import os
import time
import glob
import zstandard as zstd # Ensure this is imported
from datetime import datetime
from typing import Optional, Tuple # Added Tuple for potential future use
import re
import logging # For better logging practices
import sys # For sys.stderr

# Assuming your config.py is in a directory named 'eidon' at the same level or in PYTHONPATH
# If Eidon is the root package: from eidon.config import ...
# If archiver.py is inside 'eidon' package: from .config import ...
# Given "from Eidon.config", this implies Eidon is a directory in PYTHONPATH
# For consistency with other files, let's assume:
from eidon.config import screenshots_path, HOT_DAYS, COLD_DAYS, ARCHIVE_DIR, WEBP_QUALITY # WEBP_QUALITY isn't used here but good to be aware of config structure

# --- Logging Setup ---
# It's good practice to use the logging module instead of just print() for application messages.
logger = logging.getLogger(__name__)
if not logger.handlers: # Avoid adding multiple handlers if imported multiple times or in testing
    handler = logging.StreamHandler(sys.stderr) # Log to stderr
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Set default logging level (INFO, DEBUG, WARNING, ERROR)


# --- Archiver Function ---
def run_archiver(compression_level: int = 19, chunk_size: int = 16384) -> None:
    """
    Compresses old .webp snapshots from screenshots_path into individual .zst files
    within date-based subdirectories in ARCHIVE_DIR.

    Args:
        compression_level (int): Zstandard compression level (1-22, higher is more compression but slower).
        chunk_size (int): Size of chunks (in bytes) to read/write during compression.
    """
    now_ts = time.time()
    # cutoff_hot is not used in the current logic but kept for reference from original
    # cutoff_hot = now_ts - (HOT_DAYS * 86400) 
    cutoff_cold = now_ts - (COLD_DAYS * 86400)

    logger.info(f"Starting archiver run. Archiving files older than {COLD_DAYS} days.")
    logger.info(f"Screenshots path: {screenshots_path}")
    logger.info(f"Archive destination: {ARCHIVE_DIR}")

    try:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create archive base directory {ARCHIVE_DIR}: {e}")
        return # Cannot proceed if archive directory cannot be created

    # Find all .webp files in the screenshots directory
    webp_pattern = os.path.join(screenshots_path, "*.webp")
    archived_count = 0
    already_exists_cleaned_count = 0
    error_count = 0

    for original_filepath in glob.glob(webp_pattern):
        try:
            # Get the modification time of the file
            file_mtime = os.path.getmtime(original_filepath)

            if file_mtime < cutoff_cold:
                # File is old enough to be archived
                mtime_datetime = datetime.fromtimestamp(file_mtime)
                date_str = mtime_datetime.strftime("%Y-%m-%d")
                
                day_archive_subdir = os.path.join(ARCHIVE_DIR, date_str)
                try:
                    os.makedirs(day_archive_subdir, exist_ok=True)
                except OSError as e:
                    logger.error(f"Failed to create day archive directory {day_archive_subdir} for {original_filepath}: {e}")
                    error_count += 1
                    continue # Skip to next file

                base_filename = os.path.basename(original_filepath)
                archived_file_path_zst = os.path.join(day_archive_subdir, base_filename + ".zst")

                # Check if the archived file already exists
                if os.path.exists(archived_file_path_zst):
                    logger.debug(f"Archived file {archived_file_path_zst} already exists.")
                    # If original still exists, remove it (it's a duplicate or leftover)
                    if os.path.exists(original_filepath):
                        try:
                            os.remove(original_filepath)
                            logger.info(f"Removed original file {original_filepath} as its archive already exists.")
                            already_exists_cleaned_count +=1
                        except OSError as e:
                            logger.error(f"Error removing already archived original file {original_filepath}: {e}")
                            error_count += 1
                    continue # Move to the next file

                # Archive the file
                logger.info(f"Archiving {original_filepath} to {archived_file_path_zst}...")
                try:
                    # Initialize Zstd compressor
                    compressor_context = zstd.ZstdCompressor(level=compression_level)
                    
                    with open(original_filepath, 'rb') as f_in, \
                         open(archived_file_path_zst, 'wb') as f_out:
                        # Use stream_writer for efficient chunk-by-chunk compression
                        with compressor_context.stream_writer(f_out, size=os.path.getsize(original_filepath)) as compressor:
                            while True:
                                chunk = f_in.read(chunk_size)
                                if not chunk:
                                    break
                                compressor.write(chunk)
                    
                    # If compression is successful, remove the original file
                    os.remove(original_filepath)
                    logger.info(f"Successfully archived and removed original: {original_filepath}")
                    archived_count += 1

                except Exception as e: # Catch any error during compression or file removal
                    logger.error(f"Error during archiving process for {original_filepath} to {archived_file_path_zst}: {e}")
                    error_count += 1
                    # Important: If compression failed, do NOT remove original_filepath.
                    # If archive file was partially created, it might be good to clean it up.
                    if os.path.exists(archived_file_path_zst):
                        try:
                            # Check if the file is empty or very small, indicating partial write
                            if os.path.getsize(archived_file_path_zst) < chunk_size / 2 : # Heuristic
                                os.remove(archived_file_path_zst)
                                logger.warning(f"Removed potentially corrupt/partial archive file: {archived_file_path_zst}")
                        except OSError as rm_err:
                             logger.error(f"Failed to remove partial archive {archived_file_path_zst} after error: {rm_err}")
            # else:
                # logger.debug(f"File {original_filepath} is not old enough for archiving (mtime: {file_mtime:.0f} vs cutoff: {cutoff_cold:.0f}).")

        except FileNotFoundError:
            # This can happen if a file is deleted between glob listing and processing
            logger.warning(f"File not found during archival (possibly deleted concurrently): {original_filepath}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing file {original_filepath} for archiving: {e}")
            error_count += 1
    
    logger.info(f"Archiver run finished. Archived: {archived_count} files. Cleaned pre-existing: {already_exists_cleaned_count}. Errors: {error_count}.")


# --- Archived Image Retrieval ---
def get_archived_image_data(filename_webp: str) -> Optional[bytes]:
    """
    Retrieves and decompresses an image from the archive, given its original .webp filename.
    Example filename_webp: "1746552743_0_uuid.webp"

    Args:
        filename_webp (str): The original .webp filename of the image.

    Returns:
        Optional[bytes]: The decompressed image data as bytes if found and successfully decompressed,
                         otherwise None.
    """
    if not filename_webp or not filename_webp.endswith(".webp"):
        logger.warning(f"Invalid .webp filename provided for archive retrieval: '{filename_webp}'")
        return None

    # Extract timestamp from filename like "1746552743_0_....webp" using regex
    # This regex assumes the timestamp is the first numeric part before an underscore.
    match = re.match(r"^(\d+)_", filename_webp)
    if not match:
        logger.warning(f"Could not extract timestamp from filename: {filename_webp}. Archive lookup may fail or be incorrect.")
        # Fallback: try to use current date if timestamp extraction fails? Or just fail?
        # For now, let's try to proceed, but the date_str might be wrong if filename format changes.
        # A more robust way would be to search all date folders if timestamp is unparseable, but that's slow.
        # Or, if the db entry has the mtime, use that.
        # For now, require timestamp in filename for correct date folder lookup.
        # If no timestamp, we cannot reliably determine the date_str for the archive path.
        # Alternative: if filename format is strictly timestamp_index_uuid.webp, use that.
        # The original used mtime of the file to create date_str. Here, we use timestamp from filename.
        # This is generally good if filenames *always* start with the correct capture timestamp.
        return None # Cannot reliably find it without a timestamp to form the date path.
        
    timestamp = int(match.group(1))
    try:
        date_from_timestamp = datetime.fromtimestamp(timestamp)
        date_str = date_from_timestamp.strftime("%Y-%m-%d")
    except ValueError: # Timestamp might be out of range for datetime
        logger.error(f"Invalid timestamp {timestamp} extracted from filename {filename_webp} for date conversion.")
        return None

    archived_file_name_zst = filename_webp + ".zst"
    # Path construction: ARCHIVE_DIR / YYYY-MM-DD / filename.webp.zst
    potential_archived_filepath = os.path.join(ARCHIVE_DIR, date_str, archived_file_name_zst)

    logger.debug(f"Attempting to retrieve archived image: {potential_archived_filepath}")

    if os.path.exists(potential_archived_filepath):
        try:
            decompressor_context = zstd.ZstdDecompressor()
            with open(potential_archived_filepath, 'rb') as f_in:
                # Use stream_reader for efficient decompression
                with decompressor_context.stream_reader(f_in) as reader:
                    decompressed_data = reader.read()
            logger.info(f"Successfully decompressed: {potential_archived_filepath}")
            return decompressed_data
        except zstd.ZstdError as e: # More specific Zstd errors
            logger.error(f"Zstandard decompression error for {potential_archived_filepath}: {e}")
            return None
        except Exception as e: # Other errors (IOError, etc.)
            logger.error(f"Error during decompression of {potential_archived_filepath}: {e}")
            return None
    else:
        logger.debug(f"Archived file not found at expected path: {potential_archived_filepath}")
        # Optional: Implement a fallback search if the date derived from filename timestamp is wrong.
        # This would involve globbing ARCHIVE_DIR/*/*.zst, which could be slow.
        # For now, strict path based on filename's timestamp is used.
        return None

# --- Example Usage (for testing if run directly) ---
if __name__ == "__main__":
    logger.info("Running archiver.py directly for testing...")
    
    # --- Setup a mock environment for testing ---
    # This is more involved than just calling the functions.
    # You'd need to:
    # 1. Create mock screenshots_path, ARCHIVE_DIR.
    # 2. Populate screenshots_path with some dummy .webp files with various mtimes.
    # 3. Run run_archiver().
    # 4. Verify that correct files were archived and originals removed.
    # 5. Test get_archived_image_data() on one of the archived files.
    # This setup is non-trivial for a simple __main__ block.

    # For a quick manual test, you could:
    # print(f"Config - Screenshots Path: {screenshots_path}")
    # print(f"Config - Archive Dir: {ARCHIVE_DIR}")
    # print(f"Config - Cold Days: {COLD_DAYS}")
    
    # print("\nSimulating run_archiver():")
    # run_archiver(compression_level=3) # Use a low compression level for faster testing

    # print("\nAttempting to retrieve a known archived file (replace with actual filename):")
    # test_filename = "1700000000_0_test.webp" # Ensure this file would have been archived
    # data = get_archived_image_data(test_filename)
    # if data:
    #     print(f"Retrieved {len(data)} bytes for {test_filename}.")
    #     # Optionally save it to verify content:
    #     # with open("retrieved_test_image.webp", "wb") as f_out_test:
    #     #     f_out_test.write(data)
    #     # print("Saved retrieved image to retrieved_test_image.webp for verification.")
    # else:
    #     print(f"Could not retrieve data for {test_filename}.")

    logger.warning("Archiver self-test in __main__ is basic. For full testing, set up a mock file structure.")
    logger.info("To run archiver: ensure config paths are correct and run `python -m eidon.archiver` or call run_archiver() from your main app.")