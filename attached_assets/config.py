import os
import sys
import argparse

parser = argparse.ArgumentParser(
    description="Eidon - Personal Digital History Recorder",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows default values in help
)

# --- Storage Configuration ---
# Determine a sensible default storage path based on OS.
# This will be used if --storage-path is not provided.
def get_default_appdata_folder(app_name="eidon"):
    if sys.platform == "darwin": # macOS
        home = os.path.expanduser("~")
        default_path = os.path.join(home, "Library", "Application Support", app_name)
    elif sys.platform == "win32": # Windows
        appdata = os.getenv("APPDATA")
        if not appdata: # Fallback if APPDATA is not set (rare)
            home = os.path.expanduser("~")
            default_path = os.path.join(home, ".eidon_data") # Hidden folder in user's home
        else:
            default_path = os.path.join(appdata, app_name)
    else: # Linux and other Unix-like
        xdg_data_home = os.getenv("XDG_DATA_HOME")
        if xdg_data_home:
            default_path = os.path.join(xdg_data_home, app_name)
        else: # Fallback based on XDG Base Directory Specification
            home = os.path.expanduser("~")
            default_path = os.path.join(home, ".local", "share", app_name)
    return default_path

DEFAULT_STORAGE_PATH = get_default_appdata_folder()

parser.add_argument(
    "--storage-path",
    default=DEFAULT_STORAGE_PATH,
    help="Root path to store screenshots, database, and archives.",
)

# --- Capture Behavior Configuration ---
parser.add_argument(
    "--idle-time-threshold",
    type=float,
    default=10.0, # Default to 10 seconds
    help="Seconds of user inactivity before screenshot capture pauses.",
)
parser.add_argument(
    "--primary-monitor-only", # This argument was in the original but not used by screenshot.py
    action="store_true",      # If you intend to use it, screenshot.py needs modification.
    default=False, # Defaulting to False as current screenshot.py captures all screens.
    help="Only record the primary monitor (currently captures all monitors).",
)

# --- Image Processing and Similarity ---
# These are not exposed as command-line args but are configurable constants.
# If you want them as args, you can add them to the parser.

# Similarity thresholds for skipping captures
SIMILARITY_THRESHOLD = 0.70  # For MSSIM, range 0-1. Higher means more similar.
MIN_HAMMING_DISTANCE = 10     # For perceptual hash (phash). Lower means more similar.
                             # A value of 0 means identical. Small values (e.g., <5) are very similar.

# Resize and compression settings for screenshots
MAX_IMAGE_WIDTH = 960      # Max width for saved screenshots (aspect ratio preserved)
MAX_IMAGE_HEIGHT = 600       # Max height for saved screenshots
WEBP_QUALITY = 75            # Quality 0-100 for WebP compression (lower is smaller/lower quality)

# --- Archiving Configuration ---
HOT_DAYS = 1         # Files newer than this remain in the primary 'screenshots' dir.
COLD_DAYS = 0        # Files older than this are candidates for moving to the archive.
                      # Note: Archiving currently considers files older than COLD_DAYS based on mtime.

# --- Parse Arguments ---
# Only parse if the script is run directly, not when imported.
# This allows other modules to import config values without triggering argparse errors
# if they are imported by a script that doesn't expect these args (e.g., a test script).
if __name__ == "__main__" or "pytest" not in sys.modules: # Crudely check if not run by pytest
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # This can happen if --help is passed or an error occurs in parsing.
        # Allow the program to exit cleanly.
        if e.code != 0: # If it's an error code, print message
             print(f"Argument parsing error: {e}", file=sys.stderr)
        sys.exit(e.code)
else:
    # If imported, provide default values or handle as needed.
    # For simplicity, creating a Namespace with defaults.
    # This ensures that config values are available even if app.py (or another main) isn't the entry point.
    class ArgsDefault:
        def __init__(self):
            self.storage_path = DEFAULT_STORAGE_PATH
            self.idle_time_threshold = 10.0
            self.primary_monitor_only = True
    args = ArgsDefault()


# --- Set Global Configuration Variables ---
IDLE_THRESHOLD = args.idle_time_threshold
PRIMARY_MONITOR_ONLY = args.primary_monitor_only # Uncomment if used

# Define paths based on the (potentially user-provided) storage_path
appdata_folder = os.path.abspath(args.storage_path) # Ensure path is absolute
db_path = os.path.join(appdata_folder, "eidon.db")
screenshots_path = os.path.join(appdata_folder, "screenshots")
ARCHIVE_DIR = os.path.join(appdata_folder, "archive")

# --- Create Directories if they don't exist ---
# This should ideally be done once when the application starts,
# for example, in app.py before starting threads.
# However, having it here ensures paths are valid if config.py is imported early.
def ensure_dirs_exist():
    paths_to_create = [appdata_folder, screenshots_path, ARCHIVE_DIR]
    for path_to_create in paths_to_create:
        if not os.path.exists(path_to_create):
            try:
                os.makedirs(path_to_create, exist_ok=True)
                # print(f"INFO: Created directory: {path_to_create}")
            except OSError as e:
                print(f"ERROR: Could not create directory {path_to_create}: {e}", file=sys.stderr)
                # Depending on severity, you might want to sys.exit() here
ensure_dirs_exist()


# --- Sanity Check Print (optional, for debugging) ---
# if __name__ == "__main__":
#     print("--- Eidon Configuration ---")
#     print(f"Storage Path: {appdata_folder}")
#     print(f"Database Path: {db_path}")
#     print(f"Screenshots Path: {screenshots_path}")
#     print(f"Archive Path: {ARCHIVE_DIR}")
#     print(f"Idle Threshold: {IDLE_THRESHOLD}s")
#     print(f"Similarity Threshold (MSSIM): {SIMILARITY_THRESHOLD}")
#     print(f"Min Hamming Distance (phash): {MIN_HAMMING_DISTANCE}")
#     print(f"Max Image Width/Height: {MAX_IMAGE_WIDTH}/{MAX_IMAGE_HEIGHT}")
#     print(f"WebP Quality: {WEBP_QUALITY}")
#     print(f"Hot/Cold Days for Archive: {HOT_DAYS}/{COLD_DAYS}")
#     print("---------------------------")