# Eidon - Your Personal Digital History Recorder

**Eidon** is a macOS application designed to help you remember and rediscover your digital activities. It works by periodically capturing snapshots (screenshots) of your screen, extracting text content via OCR, and making this information searchable. Think of it as a personal, local, and private "rewind button" for your digital life.

## Features

*   **Automatic Snapshots:** Eidon periodically takes screenshots of your active screen(s).
*   **Intelligent Capture:**
    *   **Idle Detection:** Only captures when you're actively using your computer, pausing during idle periods.
    *   **Similarity Throttling:** Avoids excessive captures of static screens using image similarity checks (MSSIM and perceptual hashing).
    *   **Self-View Prevention:** Pauses capture when you are viewing the Eidon application itself to prevent recursive captures.
*   **OCR (Optical Character Recognition):** Extracts text from your screenshots using Apple's Vision framework, making visual content searchable.
*   **Contextual Metadata:** Records the active application name, window title, and (for supported browsers) the current page URL alongside each snapshot.
*   **Semantic Search:**
    *   Utilizes Apple's NaturalLanguage framework to generate text embeddings for OCR'd content.
    *   Allows you to search your history using natural language queries, finding relevant moments even if your keywords aren't exact text matches.
    *   Supports keyword and token-based search as a fallback.
*   **Advanced Search Filters:** Refine your search results using prefixes like `date:`, `time:`, `title:`, and `url:`.
*   **Timeline View:** Browse your captured history chronologically with an interactive timeline.
*   **Ad-hoc Capture (Quick Action):** A macOS Quick Action (with optional keyboard shortcut) allows you to manually capture the current window or a selected screen region and add it to your Eidon history.
*   **Image Archiving:** Older screenshots are compressed (using ZStandard) and organized into date-based archive folders to save space while keeping data accessible.
*   **Local & Private:** All data (screenshots, database, archives) is stored locally on your Mac, ensuring your digital history remains private.
*   **Web Interface:** Access your timeline and search functionality through a local web server.
*   **Capture Control:** Easily pause and resume screen capture via the web interface.

## How It Works

1.  **Screen Capture:** A background thread periodically takes screenshots.
2.  **Image Analysis:**
    *   Checks if the user is idle or if the screen content is too similar to the last capture.
    *   If a significant change is detected, the screenshot is processed.
3.  **OCR & Embedding:**
    *   Text is extracted from the screenshot using OCR.
    *   A semantic vector (embedding) is generated from this text.
4.  **Metadata Collection:** The active application, window title, and URL are recorded.
5.  **Database Storage:** The extracted text, embedding, metadata, timestamp, and screenshot filename are stored in a local SQLite database.
6.  **Image Saving & Archiving:**
    *   Screenshots are saved as optimized WEBP files in a "hot" storage tier.
    *   Periodically, an archiver process moves older screenshots from the "hot" tier to a "cold" tier, compressing them as `.zst` files organized by date.
7.  **Search & Retrieval:**
    *   The web interface allows you to search your history.
    *   Queries can be semantic (matching meaning) or keyword-based.
    *   Image data is served directly from the "hot" tier or decompressed on-the-fly from the "cold" archive.

## Requirements

*   **macOS:** Eidon leverages macOS-specific technologies (Apple Vision for OCR, NaturalLanguage for embeddings, Quartz for system events). It is **not** cross-platform.
*   **Python 3.9+**
*   **PyObjC Frameworks:**
    *   `pyobjc-framework-Vision`
    *   `pyobjc-framework-Quartz`
    *   `pyobjc-framework-Cocoa` (typically comes with other PyObjC installs)
*   **Other Python Packages:** (See `requirements.txt` - a typical list might include)
    *   `Flask`
    *   `numpy`
    *   `Pillow` (PIL)
    *   `zstandard`
    *   `imagehash`
    *   `psutil` (for some system utilities, though Quartz is primary on macOS)
    *   `python-dateutil`

## Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/yourusername/eidon.git # Replace with your actual repo URL
    cd eidon
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    A `requirements.txt` file should be provided. If not, you'll need to install the packages listed under "Requirements" manually.
    ```bash
    pip install -r requirements.txt
    # Or manually:
    # pip install Flask numpy Pillow zstandard imagehash psutil pyobjc-framework-Vision pyobjc-framework-Quartz python-dateutil
    ```
    *Note: PyObjC packages can sometimes be tricky. Ensure you have Xcode Command Line Tools installed (`xcode-select --install`).*

4.  **Set up Storage Path (Optional but Recommended for Production):**
    By default, Eidon might store data in a standard application support directory. You can explicitly set a storage path for screenshots, the database, and archives using the `--storage-path` command-line argument when running `app.py`.
    Example:
    ```bash
    python app.py --storage-path /Volumes/ExternalDrive/EidonData
    ```
    If not specified, check `config.py` for default locations (usually `~/Library/Application Support/eidon/` or similar).

5.  **Set up the Ad-hoc Capture Quick Action (Optional):**
    *   Open Automator.
    *   Create a new "Quick Action".
    *   Set "Workflow receives current" to **no input** in **any application**.
    *   Add a "Run AppleScript" action.
    *   Paste the AppleScript code (provided separately in the project, often in a file like `eidon_quick_action.applescript`).
    *   Save the Quick Action (e.g., "Eidon Adhoc Capture").
    *   Optionally, assign a keyboard shortcut to this Quick Action via System Settings > Keyboard > Keyboard Shortcuts > Services.

## Usage

1.  **Run the Application:**
    Navigate to the Eidon project directory in your terminal (ensure your virtual environment is active).
    ```bash
    python app.py [arguments]
    ```
    **Command-line arguments (see `config.py` or run `python app.py --help`):**
    *   `--storage-path <PATH>`: Specify the root directory for Eidon's data.
    *   `--idle-time-threshold <SECONDS>`: Seconds of inactivity before capture pauses (default: 10).

2.  **Access the Web Interface:**
    Once running, Eidon will print the URL for the web interface (usually `http://localhost:8082` or `http://0.0.0.0:8082`). Open this in your web browser.

3.  **Using Eidon:**
    *   **Timeline:** Scroll through your captured history. Click on cards to view details.
    *   **Search:** Use the search bar.
        *   Enter keywords or natural language questions.
        *   Use filters:
            *   `date:YYYY-MM-DD` or `date:today` or `date:yesterday` or `date:mm/dd`
            *   `time:HH:MM` or `time:HH:MM-HH:MM` (e.g., `time:14:00-16:30`)
            *   `title:your window title query`
            *   `url:domain.com` or `url:keyword_in_url`
            *   Example: `meeting notes date:yesterday title:project alpha`
    *   **Pause/Resume Capture:** Use the toggle button in the web interface header.
    *   **Ad-hoc Capture:** Trigger your Quick Action (via Services menu or keyboard shortcut) to manually capture a window or selection.
Okay, here's a guide to the best search methods to use in the Eidon app, based on its functionality:

**Eidon: Your Personal Digital Rewind Button**

Eidon is a macOS application designed to help you remember and rediscover your digital activities. It works by periodically capturing snapshots (screenshots) of your screen, extracting text content via OCR, and making this information searchable. Think of it as a personal, local, and private "rewind button" for your digital life.

**How to Search Effectively in Eidon**

Eidon offers a flexible search system that combines keyword matching, powerful filters, and smart semantic understanding. Here’s how to make the most of it:

**1. Basic Keyword Search:**

*   **How it works:** Simply type words or phrases into the search bar. Eidon will look for these terms in:
    *   Text content extracted from your screen (OCR)
    *   Application names (e.g., "Safari", "VS Code")
    *   Window titles (e.g., "Project Proposal - Google Docs")
    *   Recorded URLs (if applicable, e.g., from browser activity)
*   **Example:** `meeting notes`, `python documentation`, `invoice template design`
*   **Ranking of Results:**
    *   **Smart Ranking (Semantic Search):** Eidon intelligently tries to understand the *meaning* of your query. If possible, it will prioritize entries that are semantically similar to your search terms, even if they don't contain the exact keywords. These highly relevant results typically appear first.
    *   **Time-based Ranking:** Results that match your keywords but aren't part of the primary semantic ranking (e.g., entries with less text content or when semantic analysis of your query isn't possible) are generally sorted by time, with the most recent entries appearing first.

**2. Using Prefixed Filters for Precision:**

Prefixed filters allow you to significantly narrow down your search. You can use them alone or combine them with keywords.

*   **`date:` Filter:** Finds entries from a specific day.
    *   **Format:** `date:YYYY-MM-DD`
    *   **Example:** To see all activity from October 26, 2023: `date:2023-10-26`
    *   **With Keywords:** `quarterly results date:2023-10-26`

*   **`time:` Filter:** Pinpoints entries to a specific time or a time range. This is most effective when combined with a `date:` filter or when searching for activity from "today" or "yesterday."
    *   **Specific Time Format:** `time:HH:MM` (uses 24-hour format)
    *   **Example:** `project update date:2023-10-26 time:14:30` (finds "project update" around 2:30 PM on that date)
    *   **Time Range Format:** `time:HH:MM-HH:MM`
    *   **Example:** `research paper time:09:00-11:30` (looks for "research paper" activity between 9:00 AM and 11:30 AM)

*   **`title:` Filter:** Searches specifically within window titles.
    *   **Format:** `title:your_text`
    *   **Example:** `title:presentation` (finds entries where "presentation" appears in the window title)
    *   **Note:** This is a case-insensitive, partial match. `title:report` would match "Final Report" and "report_draft".

*   **`url:` Filter:** Searches by website domain or parts of a URL.
    *   **Format:** `url:your_text`
    *   **Example:** `url:github` (finds activity related to any github.com pages)
    *   **Example:** `url:developer.apple.com`
    *   **Note:** It primarily searches the domain part of the URL (e.g., for `https://www.example.com/path/page`, it considers `example.com`). `url:google` would match `docs.google.com`, `mail.google.com`, etc.

**3. Combining Keywords and Filters (The Power Combo):**

This is often the most efficient way to find exactly what you're looking for.

*   **Syntax:** `keyword1 keyword2 filter1:value filter2:value`
*   **Examples:**
    *   Find a budget spreadsheet you worked on in Google Docs around January 20th, 2024:
        `budget spreadsheet url:docs.google date:2024-01-20`
    *   Locate the final version of a client presentation from the afternoon of February 10th, 2024:
        `client presentation title:final date:2024-02-10 time:15:00-17:00`
    *   Search for an error message you saw on Stack Overflow yesterday (assuming yesterday was March 14th, 2024):
        `error message date:2024-03-14 url:stackoverflow`

**4. Searching by Filters Only:**

If you omit keywords and only use filters, Eidon will list all entries that match those filter criteria, sorted by time (most recent first).

*   **Example:** To see all your activity on Wikipedia on New Year's Day 2023:
    `date:2023-01-01 url:wikipedia.org`

**Tips for Best Search Results:**

*   **Start Broad, Then Narrow:** Begin with a few general keywords. If you get too many results, add more specific terms or apply filters.
*   **Leverage Semantic Search:** Don't worry if you can't recall the exact words. Eidon's semantic understanding can often find relevant entries based on meaning. For instance, searching for `vacation planning` might surface an email titled "Trip Itinerary."
*   **Filters Are Your Friends:** `date:`, `time:`, `url:`, and `title:` are excellent tools for quickly reducing the search pool.
*   **Iterate Your Search:** If your first attempt doesn't yield the desired result, try slightly different keywords, synonyms, or adjust your filters.
*   **Mind Your Syntax:** While semantic search is forgiving, ensure filter prefixes and their values (like dates) are correctly formatted.
*   **Visibility Matters:** The more text visible on your screen during a snapshot, the richer the data Eidon can capture, leading to more comprehensive search results later.
## Configuration

Key configuration options are managed in `config.py` or via command-line arguments:

*   `IDLE_THRESHOLD`: Time in seconds before capture is considered idle.
*   `SIMILARITY_THRESHOLD`: MSSIM value above which images are considered too similar to recapture.
*   `MIN_HAMMING_DISTANCE`: Minimum perceptual hash distance for images to be considered different.
*   `MAX_IMAGE_WIDTH`, `MAX_IMAGE_HEIGHT`: Dimensions for thumbnailing screenshots before saving (affects file size and OCR input quality if OCR is done on thumbnails).
*   `WEBP_QUALITY`: Compression quality for WEBP images.
*   `HOT_DAYS`, `COLD_DAYS`: Thresholds for moving screenshots to the compressed archive.
*   `ARCHIVE_DIR`, `screenshots_path`, `db_path`: Paths for data storage, often derived from `appdata_folder` or the `--storage-path` argument.

## Troubleshooting

*   **`NameError` or `ModuleNotFoundError`:** Ensure all dependencies are installed correctly in your active Python environment.
*   **OCR/Embedding Failures on macOS:**
    *   Make sure you have the necessary PyObjC frameworks installed (`Vision`, `Quartz`, `Cocoa`).
    *   The NaturalLanguage framework requires macOS to have downloaded language models. This usually happens automatically.
*   **`curl command failed` (from Quick Action):**
    *   Verify the Eidon Flask app (`app.py`) is running.
    *   Check the Flask app's console output for errors related to the `/api/add_adhoc_capture` endpoint.
    *   Ensure the URL in the AppleScript (`http://localhost:8082/api/add_adhoc_capture`) matches where your Flask app is being served.
*   **Permissions:** Eidon needs permission to take screenshots. The first time it tries, macOS should prompt you. If not, go to System Settings > Privacy & Security > Screen Recording and ensure your terminal application (or Python itself, if run directly) is allowed. Similar permissions might be needed for Accessibility (to get window titles/app names reliably).
*   **Storage Space:** Eidon can consume significant disk space over time, even with WEBP compression and archiving. Monitor the size of your storage path.

## Contributing

Contributions are welcome! If you'd like to contribute, please:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Write tests for your changes if applicable.
5.  Ensure your code lints and follows existing style.
6.  Submit a pull request with a clear description of your changes.

## Future Ideas / Potential Enhancements

*   More sophisticated activity detection (e.g., differentiating between active typing vs. just moving a mouse over a video).
*   Audio recording and transcription (with appropriate privacy considerations).
*   Integration with other services (e.g., calendar to tag events).
*   Encrypted database and archives.
*   Summarization of daily/weekly activity.
*   Cross-platform support (major undertaking, would require replacing macOS-specific components).
*   Dedicated desktop application GUI instead of/in addition to the web interface.

## License

This project is licensed under the [MIT License](LICENSE.md) (or specify your chosen license).

---
