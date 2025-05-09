import sys
import datetime
import re
import subprocess # For platform-specific commands
import time # For potential timeouts or delays
from typing import Tuple, Optional
import os # Already implicitly there via sys, but good practice if used directly
from urllib.parse import urlparse, unquote # For URL parsing in title generation

# --- Attempt to import dateutil for flexible date/time parsing ---
try:
    from dateutil import parser as dateutil_parser
    from dateutil.tz import tzlocal # For handling local timezone if needed
except ImportError:
    dateutil_parser = None
    # print("Warning: 'python-dateutil' not found. Date/time parsing in search filters will be less flexible.", file=sys.stderr)

# --- Platform-specific imports for system interaction ---
psutil = None
win32gui = None
win32process = None
win32api = None
NSWorkspace = None
CGWindowListCopyWindowInfo = None
kCGNullWindowID = None
kCGWindowListOptionOnScreenOnly = None

if sys.platform == "win32": # Windows
    try:
        import psutil
        import win32gui
        import win32process
        # import win32api # Not used in this version for active window info
    except ImportError:
        print("Warning: 'psutil' or 'pywin32' not found. Active window/app info may be unavailable on Windows.", file=sys.stderr)
elif sys.platform == "darwin": # macOS
    try:
        from AppKit import NSWorkspace
        from Quartz import CGWindowListCopyWindowInfo, kCGNullWindowID, kCGWindowListOptionOnScreenOnly
    except ImportError:
        print("Warning: PyObjC 'AppKit' or 'Quartz' not found. Active window/app info may be unavailable on macOS.", file=sys.stderr)
# Linux uses subprocess for xprop, no special Python package imports here.


# --- Time Formatting Functions ---
def human_readable_time(timestamp: int) -> str:
    """Converts a Unix timestamp into a human-readable relative time string."""
    now_dt = datetime.datetime.now(tzlocal() if dateutil_parser else None) # Use local timezone if possible
    try:
        # Ensure timestamp is treated as UTC then converted to local for comparison if needed
        # For simplicity, assuming timestamps are "naive" or already in local system's context
        dt_object = datetime.datetime.fromtimestamp(timestamp, tzlocal() if dateutil_parser else None)
    except (TypeError, ValueError, OSError): # Handle invalid timestamp or out of range
        return "Invalid date"
        
    diff = now_dt - dt_object

    if diff.total_seconds() < 0: # Timestamp is in the future
        return "In the future" # Or format as absolute date/time

    days = diff.days
    seconds = diff.seconds # Seconds part of the timedelta (0 to 86399)

    if days >= 365:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    if days >= 30:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    if days > 0:
        return f"{days} day{'s' if days > 1 else ''} ago"
    
    # If less than a day, use seconds component of timedelta
    if seconds >= 3600: # Hours
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if seconds >= 60: # Minutes
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    if seconds >= 0: # Seconds
        # For very small differences, "just now" is better
        if seconds < 5:
            return "Just now"
        return f"{seconds} second{'s' if seconds != 1 else ''} ago"
    
    return "Just now" # Fallback for very small negative diffs if future check fails


def timestamp_to_human_readable(timestamp: int, default_format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Converts a Unix timestamp into a human-readable absolute date/time string.
    """
    try:
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        return dt_object.strftime(default_format)
    except (TypeError, ValueError, OSError):
        return "Invalid Timestamp"

# --- Search Filter Parsing ---
def _parse_single_filter_value(key: str, value_str: str, current_datetime: datetime.datetime):
    """Helper to parse individual filter values for date and time."""
    # Ensure value_str is stripped of leading/trailing quotes for date/time parsing
    value_str_cleaned = value_str.strip("'\"")

    if key == 'date':
        if value_str_cleaned.lower() == "today":
            return current_datetime.date()
        if value_str_cleaned.lower() == "yesterday":
            return (current_datetime - datetime.timedelta(days=1)).date()

        common_date_formats = ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d-%m-%Y", "%d/%m/%Y", "%m/%d", "%m-%d")
        for fmt in common_date_formats:
            try:
                dt = datetime.datetime.strptime(value_str_cleaned, fmt)
                if fmt in ("%m/%d", "%m-%d"): 
                    dt = dt.replace(year=current_datetime.year)
                return dt.date()
            except ValueError:
                continue
        
        if dateutil_parser:
            try:
                return dateutil_parser.parse(value_str_cleaned, default=current_datetime, ignoretz=True).date()
            except (dateutil_parser.ParserError, ValueError, TypeError):
                pass
        return None

    if key == 'time':
        if '-' in value_str_cleaned and value_str_cleaned.count('-') == 1:
            start_str, end_str = value_str_cleaned.split('-', 1)
            try:
                # Recursively call for single time parsing
                start_time = _parse_single_filter_value('time', start_str.strip(), current_datetime) 
                end_time = _parse_single_filter_value('time', end_str.strip(), current_datetime)
                if start_time and end_time:
                    return (start_time, end_time)
            except ValueError:
                return None
        else: 
            common_time_formats = ("%H:%M:%S", "%H:%M", "%I:%M%p", "%I%p", "%I:%M:%S%p")
            for fmt in common_time_formats:
                try:
                    # Use .upper() for AM/PM matching consistency
                    return datetime.datetime.strptime(value_str_cleaned.upper(), fmt.upper()).time()
                except ValueError:
                    continue
            
            if dateutil_parser:
                try:
                    return dateutil_parser.parse(value_str_cleaned, default=current_datetime, ignoretz=True).time()
                except (dateutil_parser.ParserError, ValueError, TypeError):
                    pass
            return None
    return None # Should not be reached if key is 'date' or 'time'

def parse_prefixed_filters(query_string: str) -> Tuple[dict, str]:
    """
    Parses a search string for prefix filters (date:, time:, title:, url:).
    Returns a dictionary of parsed filters and the remaining core query string.
    Handles quoted values for title and url.
    """
    # Regex to find filter patterns: key:value (no space), key: "quoted value", or key value
    # This regex is complex; an alternative is iterative token processing.
    # For simplicity, let's stick to iterative token processing as it's more readable.
    
    tokens = []
    # Preserve quoted strings as single tokens
    # This regex splits by spaces, but keeps quoted sections together.
    for part in re.split(r"""("[^"]*"|'[^']*')|\s+""", query_string):
        if part is not None and part.strip():
            tokens.append(part)

    filters = {}
    core_query_parts = []
    current_dt = datetime.datetime.now()
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        potential_key_match = re.match(r"^(date|time|title|url):$", token, re.IGNORECASE)
        
        key = ""
        value_str = ""

        if potential_key_match: # e.g., "date:"
            key = potential_key_match.group(1).lower()
            if i + 1 < len(tokens):
                value_str = tokens[i+1]
                i += 2 # Consumed key and value
            else: # Key without a value, treat as core query
                core_query_parts.append(token)
                i += 1
                continue
        elif ':' in token and not (token.startswith('"') or token.startswith("'")): 
            # e.g., "date:2023-01-01" or "title:MyReport"
            parts = token.split(':', 1)
            if parts[0].lower() in ('date', 'time', 'title', 'url') and len(parts) == 2:
                key = parts[0].lower()
                value_str = parts[1]
                i += 1 # Consumed one token
            else: # Not a valid filter structure
                core_query_parts.append(token)
                i += 1
                continue
        else: # Not a filter, part of core query
            core_query_parts.append(token)
            i += 1
            continue

        # Process the extracted key and value_str
        if key:
            # Strip quotes from value_str if they are outer quotes (e.g. from regex capture)
            if (value_str.startswith('"') and value_str.endswith('"')) or \
               (value_str.startswith("'") and value_str.endswith("'")):
                value_str_cleaned = value_str[1:-1]
            else:
                value_str_cleaned = value_str

            if key in ('date', 'time'):
                parsed_value_typed = _parse_single_filter_value(key, value_str_cleaned, current_dt)
                if parsed_value_typed is not None:
                    filters[key] = parsed_value_typed
                else: # Parsing failed, add original filter part to core query
                    core_query_parts.append(f"{key}:{value_str}") # Reconstruct original form
            elif key in ('title', 'url'):
                # For title and url, value_str_cleaned is the final value
                # URL values are typically case-insensitive for matching domain/path parts
                filters[key] = value_str_cleaned.lower() if key == 'url' else value_str_cleaned
            # else: # Should not happen if key is one of the valid ones
        # else: # Should not happen
            
    core_query_str = ' '.join(core_query_parts)
    return filters, core_query_str


# --- Platform Abstraction for Active Window/App/URL ---
# (macOS, Windows, Linux specific getters are the same as in the previous response)
def _get_active_app_name_osx() -> str:
    if NSWorkspace:
        try:
            active_app_dict = NSWorkspace.sharedWorkspace().activeApplication()
            return active_app_dict.get("NSApplicationName", "")
        except Exception: return ""
    return ""

def _get_active_window_title_osx() -> str:
    if CGWindowListCopyWindowInfo and kCGNullWindowID and kCGWindowListOptionOnScreenOnly:
        try:
            window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            active_app_name = _get_active_app_name_osx()
            for window in window_list:
                if window.get("kCGWindowOwnerName") == active_app_name and window.get("kCGWindowLayer") == 0:
                    title = window.get("kCGWindowName", "")
                    if title: return title
            return ""
        except Exception: return ""
    return ""

def _get_active_page_url_osx() -> str:
    browser_scripts = {
        "com.apple.Safari": 'tell application "Safari" to get URL of front document',
        "com.google.Chrome": 'tell application "Google Chrome" to get URL of active tab of front window',
        "company.thebrowser.Browser": 'tell application "Arc" to get URL of active tab of front window',
        "com.microsoft.edgemac": 'tell application "Microsoft Edge" to get URL of active tab of front window',
        "org.mozilla.firefox": 'tell application "Firefox" to get URL of active tab of front window'
    }
    if NSWorkspace:
        try:
            active_app_dict = NSWorkspace.sharedWorkspace().activeApplication()
            bundle_id = active_app_dict.get("NSApplicationBundleIdentifier")
            if bundle_id in browser_scripts:
                script = browser_scripts[bundle_id]
                process = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate(timeout=1.0) # Reduced timeout slightly
                if process.returncode == 0 and stdout:
                    return stdout.decode('utf-8').strip()
        except Exception: pass
    return ""

def _get_active_app_name_windows() -> str:
    if psutil and win32gui and win32process:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid: return ""
            return psutil.Process(pid).name()
        except Exception: return ""
    return ""

def _get_active_window_title_windows() -> str:
    if win32gui:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return ""
            return win32gui.GetWindowText(hwnd)
        except Exception: return ""
    return ""

def _get_active_page_url_windows() -> str: return "" # Placeholder

def _get_linux_xprop_details(prop_name: str) -> Optional[str]:
    try:
        xprop_root_cmd = ['xprop', '-root', '_NET_ACTIVE_WINDOW']
        active_window_proc = subprocess.run(xprop_root_cmd, capture_output=True, text=True, timeout=0.5, check=False) # Shortened timeout
        if active_window_proc.returncode != 0: return None
        match_id = re.search(r'window id # (0x[0-9a-fA-F]+)', active_window_proc.stdout)
        if not match_id: return None
        window_id = match_id.group(1)
        xprop_id_cmd = ['xprop', '-id', window_id, prop_name]
        prop_proc = subprocess.run(xprop_id_cmd, capture_output=True, text=True, timeout=0.5, check=False)
        if prop_proc.returncode != 0: return None
        if prop_name == 'WM_CLASS':
            match_class = re.search(r'WM_CLASS\(STRING\) = "([^"]+)", "([^"]+)"', prop_proc.stdout)
            return match_class.group(1) if match_class else None
        elif prop_name == '_NET_WM_NAME':
            match_name = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "([^"]*)"', prop_proc.stdout)
            return match_name.group(1) if match_name else None
    except Exception: return None
    return None

def _get_active_app_name_linux() -> str: return _get_linux_xprop_details('WM_CLASS') or ""
def _get_active_window_title_linux() -> str: return _get_linux_xprop_details('_NET_WM_NAME') or ""
def _get_active_page_url_linux() -> str: return "" # Placeholder

def generate_smart_title(app_name: str, window_title: str, url: Optional[str]) -> str:
    """
    Generates a more descriptive title based on application context.
    """
    app_name_lower = app_name.lower() if app_name else ""
    original_window_title = window_title # Keep a copy

    # 1. Web Browsers (Safari, Chrome, Arc, Edge, Firefox)
    browser_app_names = ["safari", "google chrome", "arc", "microsoft edge", "firefox"]
    is_browser = any(browser_keyword in app_name_lower for browser_keyword in browser_app_names)

    if is_browser and url:
        if window_title and window_title.lower() != url.lower() and window_title.lower() != "new tab" and window_title.strip():
            suffixes_to_remove = [
                f" - {app_name}", 
                " - Google Chrome", " - Mozilla Firefox", " - Safari",
                " - Microsoft Edge", " - Arc",
            ]
            cleaned_title = window_title
            for suffix in suffixes_to_remove:
                if cleaned_title.endswith(suffix):
                    cleaned_title = cleaned_title[:-len(suffix)].strip()
            
            if cleaned_title and cleaned_title.lower() != url.lower():
                return cleaned_title

        try:
            parsed_url = urlparse(url)
            path_parts = [part for part in parsed_url.path.split('/') if part]
            
            if path_parts and '.' in path_parts[-1]:
                filename_from_url = unquote(path_parts[-1])
                return filename_from_url
            
            title_from_url = parsed_url.netloc
            if path_parts:
                title_from_url += f"/{unquote(path_parts[0])}" 
            
            if title_from_url:
                return title_from_url
        except Exception:
            pass 

        if window_title and window_title.strip(): return window_title
        if url: return url
        return app_name if app_name else "Web Browser"

    common_file_extensions = [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.json', '.xml', '.yaml', '.yml',
        '.md', '.txt', '.rtf',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.mov', '.mp4', '.avi', '.mkv',
        '.zip', '.tar', '.gz'
    ]
    
    # Check if window_title (or its first part) looks like a filename
    # Often the filename is the first part of the window title for these apps.
    # Example: "file.py - MyProject - VS Code" -> "file.py"
    # Example: "document.pdf" (common for Preview.app if only one doc is open)
    # Example: "Finder /Users/name/Documents" -> keep as is for Finder unless specific file interaction

    # Prioritize using the part before " - " if it seems like a file name
    first_part_of_title = window_title.split(" - ")[0].strip()
    if any(first_part_of_title.lower().endswith(ext) for ext in common_file_extensions):
        return first_part_of_title

    # If the entire window_title ends with an extension (e.g. Preview.app showing just "mydoc.pdf")
    if any(window_title.lower().endswith(ext) for ext in common_file_extensions):
        return window_title
    
    if "finder" in app_name_lower and window_title and window_title.lower() != "finder":
        return window_title 

    if original_window_title and original_window_title.strip() and \
       (not app_name or original_window_title.lower() != app_name_lower):
        return original_window_title
    
    if app_name:
        return app_name
            
    return "Untitled Capture"


# --- Public API for Active Info ---
def get_active_app_name() -> str:
    if sys.platform == "darwin": return _get_active_app_name_osx()
    elif sys.platform == "win32": return _get_active_app_name_windows()
    elif sys.platform.startswith("linux"): return _get_active_app_name_linux()
    return ""

def get_active_window_title() -> str:
    if sys.platform == "darwin": return _get_active_window_title_osx()
    elif sys.platform == "win32": return _get_active_window_title_windows()
    elif sys.platform.startswith("linux"): return _get_active_window_title_linux()
    return ""

def get_active_page_url() -> str:
    if sys.platform == "darwin": return _get_active_page_url_osx()
    # Windows and Linux placeholders return ""
    return ""


# --- Example Usage (for testing if run directly) ---
if __name__ == "__main__":
    print("--- Testing Time Formatting ---")
    ts_now = int(time.time())
    ts_hour_ago = ts_now - 3600
    ts_day_ago = ts_now - 86400
    ts_month_ago = ts_now - (86400 * 35)
    ts_year_ago = ts_now - (86400 * 400)
    print(f"Now ({ts_now}): {human_readable_time(ts_now)} | {timestamp_to_human_readable(ts_now)}")
    print(f"1h ago ({ts_hour_ago}): {human_readable_time(ts_hour_ago)} | {timestamp_to_human_readable(ts_hour_ago)}")
    print(f"1d ago ({ts_day_ago}): {human_readable_time(ts_day_ago)} | {timestamp_to_human_readable(ts_day_ago)}")
    print(f"35d ago ({ts_month_ago}): {human_readable_time(ts_month_ago)} | {timestamp_to_human_readable(ts_month_ago)}")
    print(f"400d ago ({ts_year_ago}): {human_readable_time(ts_year_ago)} | {timestamp_to_human_readable(ts_year_ago)}")
    print(f"Invalid ts: {human_readable_time(-1)} | {timestamp_to_human_readable(-1)}")


    print("\n--- Testing Filter Parsing ---")
    queries_to_test = [
        "meeting notes date:2023-10-26 title:\"Project Update\"",
        "search term url:example.com time:14:30",
        "keyword date:today",
        "another one date:10/26/2023 time:2pm-4:30pm",
        "complex title:'report for Q3 - final draft' date:yesterday url:internal.site",
        "no_filters_here",
        "date: 12/25/2024 time: 10am keyword", # Space after colon
        "title:My Report text only",
        "url:https://github.com/user date:01-01-2025 time:08:00",
        "date:invalid-date some text", # Invalid date
        "time:9", # Ambiguous time, might parse with dateutil if lucky
        "date:tomorrow", # Not explicitly handled, dateutil might parse
        "time:10:30-11:30am"
    ]
    for q_str in queries_to_test:
        filters, core_q = parse_prefixed_filters(q_str)
        print(f"Query: '{q_str}'\n  Filters: {filters}\n  Core: '{core_q}'")

    print("\n--- Testing Active Window Info ---")
    print(f"Platform: {sys.platform}")
    print(f"Active App: '{get_active_app_name()}'")
    print(f"Active Title: '{get_active_window_title()}'")
    print(f"Active URL: '{get_active_page_url()}' (Note: URL retrieval is limited on some platforms/browsers)")
    
    print("\nUtils.py self-test complete.")