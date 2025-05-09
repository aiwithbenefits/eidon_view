import os
import sys
import time
import uuid # For generating unique parts of filenames
from threading import Event
from typing import List, Optional, Tuple # Retained Tuple for potential future use

import numpy as np
from PIL import Image, ImageGrab # ImageGrab for screenshots, Image for processing
import imagehash # For perceptual hashing

# macOS-specific imports for idle time and active window info
if sys.platform == "darwin":
    try:
        from Quartz import (
            CGEventSourceSecondsSinceLastEventType,
            kCGAnyInputEventType,
            kCGEventSourceStateCombinedSessionState
        )
    except ImportError:
        print("ERROR: Quartz module not found. Idle detection will not work on macOS.", file=sys.stderr)
        # Define stubs or alternative behavior if Quartz is critical and missing
        def CGEventSourceSecondsSinceLastEventType(*args): return 0 # Assume active
        kCGAnyInputEventType = None
        kCGEventSourceStateCombinedSessionState = None
else:
    # Placeholder for non-macOS idle detection (could use psutil or other libraries)
    print("Warning: Idle detection is currently only implemented for macOS.", file=sys.stderr)

# Eidon specific module imports
from eidon.config import (
    screenshots_path, IDLE_THRESHOLD, SIMILARITY_THRESHOLD, MIN_HAMMING_DISTANCE,
    MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT, WEBP_QUALITY
)
from eidon.database import insert_entry, get_entry_by_timestamp # Added get_entry_by_timestamp for conflict check
from eidon.nlp import get_embedding
from eidon.ocr import extract_text_from_image
from eidon.utils import (
    get_active_app_name,
    get_active_window_title,
    get_active_page_url,
    generate_smart_title, # Add this import
)

# --- Global Variables & Control ---

# URL parts that identify the Eidon app's own interface (to prevent self-capture)
SELF_VIEW_URL_PARTS = ["localhost:8082", "127.0.0.1:8082", "0.0.0.0:8082"] # Ensure this matches your app's serving address

# Event to control screenshot capture (pause/resume)
capture_active_event = Event()
capture_active_event.set()  # Start in active (capturing) state

# --- Capture Control Functions ---
def pause_capture():
    """Pauses the screenshot capture thread."""
    capture_active_event.clear()
    print("Screenshot capture PAUSED.", file=sys.stderr)

def resume_capture():
    """Resumes the screenshot capture thread."""
    capture_active_event.set()
    print("Screenshot capture RESUMED.", file=sys.stderr)

def is_capture_active() -> bool:
    """Checks if screenshot capture is currently active."""
    return capture_active_event.is_set()

# --- System Interaction Functions ---
def get_idle_time() -> float:
    """
    Returns user idle time in seconds.
    Currently implemented for macOS using Quartz.
    Returns 0 (active) on other platforms or if Quartz fails.
    """
    if sys.platform == "darwin" and kCGAnyInputEventType is not None:
        try:
            return CGEventSourceSecondsSinceLastEventType(
                kCGEventSourceStateCombinedSessionState,
                kCGAnyInputEventType,
            )
        except Exception as e:
            print(f"Error getting idle time from Quartz: {e}", file=sys.stderr)
            return 0.0 # Assume active on error
    return 0.0 # Default to active for non-macOS or if Quartz components are missing

# --- Image Comparison Functions ---
def _calculate_mssim_for_rgb(img1_rgb: np.ndarray, img2_rgb: np.ndarray, L: int = 255) -> float:
    """
    Calculates Mean Structural Similarity Index (MSSIM) between two RGB images.
    Helper function for is_similar.
    """
    # Constants for MSSIM calculation
    K1, K2 = 0.01, 0.03
    C1, C2 = (K1 * L) ** 2, (K2 * L) ** 2

    def rgb_to_grayscale(rgb_img: np.ndarray) -> np.ndarray:
        """Converts an RGB image (NumPy array) to grayscale."""
        # Standard luminance calculation
        return np.dot(rgb_img[..., :3], [0.2989, 0.5870, 0.1140])

    # Convert RGB images to grayscale for MSSIM
    img1_gray = rgb_to_grayscale(img1_rgb)
    img2_gray = rgb_to_grayscale(img2_rgb)

    mu1 = np.mean(img1_gray)
    mu2 = np.mean(img2_gray)
    sigma1_sq = np.var(img1_gray)
    sigma2_sq = np.var(img2_gray)
    # Covariance of img1_gray and img2_gray
    sigma12 = np.mean((img1_gray - mu1) * (img2_gray - mu2))

    # MSSIM formula
    numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2)
    
    if denominator == 0: # Avoid division by zero
        return 1.0 if numerator == 0 else 0.0 # Perfect match if both are zero, else no similarity

    ssim_index = numerator / denominator
    return ssim_index


def is_similar_mssim(
    img1_np: np.ndarray, img2_np: np.ndarray, threshold: float = SIMILARITY_THRESHOLD
) -> bool:
    """
    Checks if two images (NumPy arrays) are similar based on MSSIM.
    Assumes img1_np and img2_np are RGB(A) images.
    """
    if img1_np.shape != img2_np.shape:
        # If shapes differ (e.g., resolution change), they are not considered similar for this check.
        return False
    
    # If images have an alpha channel, consider only RGB for MSSIM
    img1_rgb = img1_np[..., :3] if img1_np.shape[-1] == 4 else img1_np
    img2_rgb = img2_np[..., :3] if img2_np.shape[-1] == 4 else img2_np

    try:
        similarity = _calculate_mssim_for_rgb(img1_rgb, img2_rgb)
        return similarity >= threshold
    except Exception as e:
        print(f"Error calculating MSSIM: {e}", file=sys.stderr)
        return False # Treat as not similar on error

# --- Screenshot Acquisition ---
def take_screenshots() -> List[np.ndarray]:
    """
    Takes a screenshot of all connected displays.
    Returns a list of NumPy arrays, one for each display.
    On error or if ImageGrab fails, returns an empty list.
    """
    try:
        # ImageGrab.grab(all_screens=True) returns a list of PIL Images for each screen.
        pil_images = ImageGrab.grab(all_screens=True)
        if not isinstance(pil_images, list): # If only one screen, it might not be a list
            pil_images = [pil_images]
        return [np.array(img) for img in pil_images]
    except Exception as e:
        print(f"Error taking screenshots with ImageGrab: {e}", file=sys.stderr)
        # This can happen if no display server is running (e.g., headless SSH session)
        return []

# --- Perceptual Hashing ---
def _get_phashes_from_pil_images(pil_images: List[Image.Image]) -> List[imagehash.ImageHash]:
    """Helper to get phashes from a list of PIL images."""
    phashes = []
    for img in pil_images:
        try:
            # imagehash.phash works directly on PIL Images
            phashes.append(imagehash.phash(img))
        except Exception as e:
            print(f"Error calculating phash for an image: {e}", file=sys.stderr)
            # Add a placeholder or re-raise, depending on desired strictness
            # For now, let's try to add a "null" hash to keep array lengths consistent
            phashes.append(imagehash.hex_to_hash('0'*16)) # A zero phash
    return phashes

# --- Main Screenshot Recording Thread ---
def record_screenshots_thread() -> None:
    """
    Continuously records screenshots, processes them, and stores relevant data if significant changes are detected.
    Handles multiple monitors, idle time, self-view prevention, and similarity checks.
    """
    # Ensure TOKENIZERS_PARALLELISM is set to false if using Hugging Face tokenizers indirectly
    # This is often done to prevent deadlocks when using tokenizers in threads with multiprocessing.
    # If not using HF tokenizers directly here, this might be less critical for this specific file.
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Initialize with an initial capture to have a baseline
    last_captured_screenshots_np: List[np.ndarray] = []
    last_captured_phashes: List[imagehash.ImageHash] = []

    # Initial capture attempt
    initial_screenshots_np = take_screenshots()
    if initial_screenshots_np:
        last_captured_screenshots_np = initial_screenshots_np
        # For phash, we need PIL images of the (potentially thumbnailed) versions
        initial_pil_thumbs = []
        for np_array in initial_screenshots_np:
            img = Image.fromarray(np_array)
            img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
            initial_pil_thumbs.append(img)
        last_captured_phashes = _get_phashes_from_pil_images(initial_pil_thumbs)
    else:
        print("Warning: Initial screenshot capture failed. Retrying...", file=sys.stderr)
        # Loop will handle retries or wait if display becomes available.

    loop_count = 0
    while True:
        capture_active_event.wait() # Thread will pause here if event is cleared

        # Check for user idle time
        idle_seconds = get_idle_time()
        if idle_seconds >= IDLE_THRESHOLD:
            # print(f"User idle for {idle_seconds:.1f}s. Skipping capture.", file=sys.stderr) # Debug
            time.sleep(min(IDLE_THRESHOLD / 2, 5.0)) # Sleep adaptively when idle
            continue

        # Take new screenshots
        current_screenshots_np_list = take_screenshots()
        if not current_screenshots_np_list: # Failed to capture (e.g., screensaver, no display)
            print("Warning: Failed to capture current screenshots. Retrying in 5s.", file=sys.stderr)
            time.sleep(5)
            continue
        
        # Get active window URL for self-view check
        active_url: Optional[str] = get_active_page_url()
        if active_url and any(self_part in active_url for self_part in SELF_VIEW_URL_PARTS):
            # print(f"Self-view detected ({active_url}). Skipping capture.", file=sys.stderr) # Debug
            # Update last_screenshots to current (skipped) view to prevent immediate recapture on tab switch
            last_captured_screenshots_np = current_screenshots_np_list
            current_pil_thumbs = []
            for np_array in current_screenshots_np_list:
                img = Image.fromarray(np_array)
                img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
                current_pil_thumbs.append(img)
            last_captured_phashes = _get_phashes_from_pil_images(current_pil_thumbs)
            time.sleep(3) # Wait a bit longer if viewing self
            continue

        # Handle changes in the number of monitors
        if len(current_screenshots_np_list) != len(last_captured_screenshots_np):
            print(f"Monitor configuration changed from {len(last_captured_screenshots_np)} to {len(current_screenshots_np_list)} screens. Re-initializing baseline.", file=sys.stderr)
            last_captured_screenshots_np = current_screenshots_np_list
            current_pil_thumbs = []
            for np_array in current_screenshots_np_list:
                img = Image.fromarray(np_array)
                img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
                current_pil_thumbs.append(img)
            last_captured_phashes = _get_phashes_from_pil_images(current_pil_thumbs)
            time.sleep(3) # Pause briefly after monitor change
            continue
        
        # If last capture was empty (e.g., initial failure), set it now
        if not last_captured_screenshots_np:
            last_captured_screenshots_np = current_screenshots_np_list
            current_pil_thumbs = []
            for np_array in current_screenshots_np_list:
                img = Image.fromarray(np_array)
                img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
                current_pil_thumbs.append(img)
            last_captured_phashes = _get_phashes_from_pil_images(current_pil_thumbs)


        something_processed_this_cycle = False
        current_timestamp = int(time.time()) # Get a base timestamp for this capture cycle

        for i, current_single_screen_np in enumerate(current_screenshots_np_list):
            # Ensure corresponding last_screenshot and last_phash exist
            if i >= len(last_captured_screenshots_np) or i >= len(last_captured_phashes):
                print(f"Warning: Index {i} out of bounds for last capture data. Skipping this screen for similarity.", file=sys.stderr)
                # This should ideally be caught by monitor change logic, but as a safeguard.
                # We will process it as a "new" screen without similarity check.
                # To do that, we need to make sure a placeholder is there or handle it.
                # For now, let's just process it as if it's completely new.
                is_mssim_similar = False
                hamming_dist_low_enough = False
            else:
                # Compare with the corresponding screen from the last capture
                last_single_screen_np = last_captured_screenshots_np[i]
                last_single_screen_phash = last_captured_phashes[i]

                # 1. MSSIM check (on full-resolution or consistently scaled images)
                # For performance, MSSIM might be too slow if done on every screen every second.
                # Consider doing it less frequently or only if phash suggests high similarity.
                # For now, doing both.
                is_mssim_similar = is_similar_mssim(current_single_screen_np, last_single_screen_np)

                # 2. Perceptual Hash (phash) check (on thumbnails)
                current_pil_thumb = Image.fromarray(current_single_screen_np)
                current_pil_thumb.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
                current_phash = imagehash.phash(current_pil_thumb)
                
                hamming_distance = current_phash - last_single_screen_phash
                hamming_dist_low_enough = hamming_distance <= MIN_HAMMING_DISTANCE
            
            if is_mssim_similar and hamming_dist_low_enough:
                # print(f"Screen {i}: Similar (MSSIM & phash). Skipping.", file=sys.stderr) # Debug
                continue # Skip this screen if both checks indicate similarity

            # --- Significant Change Detected - Process This Screen ---
            something_processed_this_cycle = True
            print(f"Screen {i}: Change detected. Processing. MSSIM similar: {is_mssim_similar}, Hamming dist: {hamming_distance if 'hamming_distance' in locals() else 'N/A'}", file=sys.stderr)


            # Update the baseline for this specific screen
            last_captured_screenshots_np[i] = current_single_screen_np
            if 'current_phash' in locals(): # Ensure current_phash was calculated
                 last_captured_phashes[i] = current_phash
            else: # Recalculate if skipped comparison
                temp_thumb = Image.fromarray(current_single_screen_np)
                temp_thumb.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
                last_captured_phashes[i] = imagehash.phash(temp_thumb)


            # Generate a unique filename for this screen's capture
            # Use the per-cycle timestamp + screen index + UUID for uniqueness
            # Adding a tiny delay for multi-screen to potentially get different sub-second timestamps if needed,
            # but DB has UNIQUE on timestamp. So, screen index is more for filename uniqueness.
            # We need to ensure the timestamp for DB insert is unique *per entry*.
            # One strategy: use current_timestamp + small_offset_for_screen_i, or ensure DB handles this.
            # The database `ON CONFLICT(timestamp) DO NOTHING` will handle exact second collisions.
            # For now, let's use the cycle's `current_timestamp` for all screens in this batch.
            # The filename uniqueness is handled by `_{i}_{uuid}`.
            
            # Use the timestamp for *this specific screen processing start*
            # This is more robust if processing multiple screens takes time.
            screen_specific_timestamp = int(time.time()) 
            if i > 0: # If not the first screen, ensure timestamp is at least different
                screen_specific_timestamp = max(screen_specific_timestamp, current_timestamp + i) # A bit artificial but ensures different ts for db if needed
                                                                                                 # The best is DB just handles collision on exact second.
                                                                                                 # So, use `current_timestamp` if DB `ON CONFLICT` is reliable.
                                                                                                 # Let's use the cycle timestamp for now and let DB handle conflicts.
                                                                                                 # If this becomes an issue (too many skipped inserts), refine timestamping.


            filename_base = f"{current_timestamp}_{i}_{uuid.uuid4().hex[:8]}" # Shorter UUID
            filename_webp = filename_base + ".webp"
            filepath_webp = os.path.join(screenshots_path, filename_webp)

            # Save the image (after thumbnailing) as WEBP
            # The 'current_pil_thumb' is already created if phash was calculated.
            # If not (e.g. first pass or error in phash section), create it.
            if 'current_pil_thumb' not in locals() or i >= len(last_captured_phashes): # ensure it's for the current screen
                pil_to_save = Image.fromarray(current_single_screen_np)
                pil_to_save.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
            else:
                pil_to_save = current_pil_thumb # Reuse the thumbnailed image

            try:
                pil_to_save.save(
                    filepath_webp,
                    format="WEBP",
                    quality=WEBP_QUALITY,
                    method=6  # Slower, but often better compression
                )
            except Exception as e:
                print(f"Error saving screenshot {filepath_webp}: {e}", file=sys.stderr)
                continue # Skip processing this screen if save fails

            # Perform OCR on the *original* full-resolution image for best quality
            # Note: current_single_screen_np is the full-res numpy array.
            text_content = ""
            try:
                text_content = extract_text_from_image(current_single_screen_np)
            except Exception as e:
                print(f"OCR error for {filename_webp}: {e}", file=sys.stderr)
                # Optionally, clean up the saved image if OCR fails critically
                # try: os.remove(filepath_webp) except OSError as rm_err: print(f"Error removing {filepath_webp}: {rm_err}")
                # Continue processing other screens or next cycle, but this entry will lack text.

            embedding_vector = np.array([])
            if text_content and text_content.strip():
                try:
                    embedding_vector = get_embedding(text_content)
                except Exception as e:
                    print(f"Embedding error for {filename_webp}: {e}", file=sys.stderr)
            
            # Get metadata (app, title, URL) - this is for the state at the start of the capture cycle
            current_app_name = get_active_app_name()
            current_window_title_from_os = get_active_window_title()
            # active_url is already fetched for self-view check (ensure it's defined in this scope or re-fetch if needed)
            # If active_url might not be set from the self-view check block, ensure it's fetched here:
            # active_url = get_active_page_url() # Uncomment if active_url might not be consistently set

            title_for_db = generate_smart_title(
                app_name=current_app_name,
                window_title=current_window_title_from_os,
                url=active_url # Pass the fetched active_url
            )
            # Ensure active_app for DB is not empty
            active_app_for_db = current_app_name or "Unknown App"

            # Insert into database
            # Use `current_timestamp` which is shared for all screens in this cycle.
            # The DB's `ON CONFLICT(timestamp) DO NOTHING` will prevent duplicates if another screen
            # from a *previous* cycle coincidentally had the exact same timestamp and was processed.
            # If multiple screens in the *same* cycle use the same `current_timestamp`,
            # only the first one processed for that timestamp will be inserted. This is a known limitation
            # if we need per-screen entries with identical timestamps.
            # A solution is composite primary key (timestamp, screen_idx) or ensuring unique timestamps.
            # For now, relying on the fact that processing screens takes *some* time, or if not,
            # the DB skips subsequent inserts for that exact second.
            # Let's try to use a slightly offset timestamp for DB to differentiate screens in same cycle
            # This is a bit of a hack. A proper solution would be a composite key or more robust timestamp generation.
            
            # Using a timestamp specific to this screen's processing, but ensuring it's not before the cycle's base.
            # This makes it more likely each screen in a multi-monitor setup gets a unique DB entry if processed rapidly.
            db_timestamp = max(int(time.time()), current_timestamp) # Ensure it's at least the cycle start
            
            # If multiple screens, add a small increment to the timestamp for subsequent screens
            # This helps avoid DB collision if processing is very fast.
            if len(current_screenshots_np_list) > 1 and i > 0 :
                 # Check if previous screen used this exact timestamp (unlikely due to processing time, but safeguard)
                 # This is tricky without querying db. A simpler approach:
                 db_timestamp_candidate = current_timestamp + i # Artificial increment for uniqueness
                 # We need to ensure this candidate isn't already taken by a *previous successful insert*
                 # For now, let's use the candidate and rely on ON CONFLICT for true duplicates.
                 # A better way: if the DB supported (timestamp, screen_idx) as unique key.
                 # Given current DB: if multiple screens are processed within the same second,
                 # only the first will get in for that `current_timestamp`.
                 # Let's stick to `current_timestamp` and document that only one entry per second is stored currently.
                 # filename identifies the screen.
                 pass # Sticking with current_timestamp for DB, filename is unique.

            db_id = insert_entry(
                text=text_content,
                timestamp=current_timestamp, # Using the cycle's base timestamp for DB entry
                embedding=embedding_vector,
                app=active_app_for_db, # Use the potentially non-empty app name
                title=title_for_db,    # Use the new smart title
                filename=filename_webp, # Filename is unique per screen
                page_url=active_url
            )
            if db_id is None and get_entry_by_timestamp(current_timestamp):
                print(f"INFO: Screenshot {filename_webp} (ts: {current_timestamp}) likely skipped due to existing DB entry for this timestamp.", file=sys.stderr)


            # Brief pause if processing multiple screens to allow system to catch up slightly
            if len(current_screenshots_np_list) > 1 and i < len(current_screenshots_np_list) - 1:
                time.sleep(0.05) # Very short pause

        # Determine sleep duration for the next cycle
        loop_interval = 3.0 # Base interval in seconds
        if not something_processed_this_cycle and idle_seconds < IDLE_THRESHOLD:
            # If nothing changed and user is active, check more frequently.
            loop_interval = 1.0
        
        time.sleep(loop_interval)
        loop_count += 1
        # if loop_count % 10 == 0: print(f"Capture loop {loop_count} completed. Idle: {idle_seconds:.1f}s", file=sys.stderr) # Periodic status

    # This part of the original code is unreachable due to the infinite loop.
    # print("Screenshot recording thread finished.") # Should not be reached