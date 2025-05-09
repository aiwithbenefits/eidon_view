import sqlite3
from collections import namedtuple
import numpy as np
from typing import Any, List, Optional, Tuple

from eidon.config import db_path

# Define the structure of a database entry using namedtuple
Entry = namedtuple("Entry", ["id", "app", "title", "text", "timestamp", "embedding", "filename", "page_url"])


def create_db() -> None:
    """
    Creates the SQLite database and the 'entries' table if they don't exist.

    The table schema includes columns for an auto-incrementing ID, application name,
    window title, extracted text, timestamp, and text embedding.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Create table with all columns, including filename and page_url from the start.
            # UNIQUE constraint on timestamp ensures no duplicate entries for the same second.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app TEXT,
                    title TEXT,
                    text TEXT,
                    timestamp INTEGER UNIQUE,
                    embedding BLOB,
                    filename TEXT,
                    page_url TEXT
                )
            """)
            # Add index on timestamp for faster lookups (idempotent, won't error if exists)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON entries (timestamp)"
            )

            # --- Column Alteration Logic (for upgrading older schemas) ---
            # This part is for users who might have an older version of the database.
            # For new setups, these will be skipped.
            
            # Check and add filename column if not present
            cursor.execute("PRAGMA table_info(entries)")
            columns = [column[1] for column in cursor.fetchall()]
            if "filename" not in columns:
                try:
                    cursor.execute("ALTER TABLE entries ADD COLUMN filename TEXT")
                    print("INFO: Added 'filename' column to database.")
                except sqlite3.OperationalError as e:
                    # This might happen if another process added it, or a rare race condition.
                    print(f"Warning: Tried to add 'filename' column but failed (might already exist): {e}")

            # Check and add page_url column if not present
            # Re-fetch column info in case 'filename' was just added
            cursor.execute("PRAGMA table_info(entries)")
            columns = [column[1] for column in cursor.fetchall()]
            if "page_url" not in columns:
                try:
                    cursor.execute("ALTER TABLE entries ADD COLUMN page_url TEXT")
                    print("INFO: Added 'page_url' column to database.")
                except sqlite3.OperationalError as e:
                    print(f"Warning: Tried to add 'page_url' column but failed (might already exist): {e}")
            
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during table creation or alteration: {e}")


def get_all_entries() -> List[Entry]:
    """
    Retrieves all entries from the database.

    Returns:
        List[Entry]: A list of all entries as Entry namedtuples.
                     Returns an empty list if the table is empty or an error occurs.
    """
    entries: List[Entry] = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
            cursor = conn.cursor()
            cursor.execute("SELECT id, app, title, text, timestamp, embedding, filename, page_url FROM entries ORDER BY timestamp DESC")
            results = cursor.fetchall()
            for row in results:
                embedding_val = row["embedding"]
                # Handle NULL or empty embeddings gracefully
                if embedding_val and len(embedding_val) > 0:
                    embedding = np.frombuffer(embedding_val, dtype=np.float32)
                else:
                    embedding = np.array([], dtype=np.float32) # Ensure consistent empty array type
                
                entries.append(
                    Entry(
                        id=row["id"],
                        app=row["app"],
                        title=row["title"],
                        text=row["text"],
                        timestamp=row["timestamp"],
                        embedding=embedding,
                        filename=row["filename"],
                        page_url=row["page_url"],
                    )
                )
    except sqlite3.Error as e:
        print(f"Database error while fetching all entries: {e}")
    return entries


def get_timestamps() -> List[int]:
    """
    Retrieves all timestamps from the database, ordered descending.

    Returns:
        List[int]: A list of all timestamps.
                   Returns an empty list if the table is empty or an error occurs.
    """
    timestamps: List[int] = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Use the index for potentially faster retrieval
            cursor.execute("SELECT timestamp FROM entries ORDER BY timestamp DESC")
            results = cursor.fetchall()
            timestamps = [result[0] for result in results]
    except sqlite3.Error as e:
        print(f"Database error while fetching timestamps: {e}")
    return timestamps


def insert_entry(
    text: str, 
    timestamp: int, 
    embedding: np.ndarray, 
    app: str, 
    title: str, 
    filename: str, 
    page_url: Optional[str]
) -> Optional[int]:
    """
    Inserts a new entry into the database. Skips insertion if an entry with the
    same timestamp already exists due to the UNIQUE constraint on the timestamp column.

    Args:
        text (str): The extracted text content.
        timestamp (int): The Unix timestamp of the screenshot.
        embedding (np.ndarray): The embedding vector for the text.
        app (str): The name of the active application.
        title (str): The title of the active window.
        filename (str): The filename of the associated screenshot.
        page_url (Optional[str]): The URL of the page if available.

    Returns:
        Optional[int]: The ID of the newly inserted row if successful.
                       Returns None if the insertion was skipped due to a duplicate timestamp
                       or if an error occurred.
    """
    # Ensure embedding is bytes; handle empty array case
    if embedding.size > 0:
        embedding_bytes: bytes = embedding.astype(np.float32).tobytes()
    else:
        embedding_bytes = b'' # Store empty byte string for empty embeddings

    last_row_id: Optional[int] = None
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # ON CONFLICT(timestamp) DO NOTHING: If a row with this timestamp exists, skip insertion.
            cursor.execute(
                """
                INSERT INTO entries (text, timestamp, embedding, app, title, filename, page_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(timestamp) DO NOTHING
                """,
                (text, timestamp, embedding_bytes, app, title, filename, page_url)
            )
            conn.commit()
            if cursor.rowcount > 0:  # Check if a row was actually inserted
                last_row_id = cursor.lastrowid
            # else:
                # Optionally log that a duplicate timestamp was encountered and insertion skipped
                # print(f"INFO: Skipped inserting entry with duplicate timestamp: {timestamp}")

    except sqlite3.Error as e:
        print(f"Database error during insertion for timestamp {timestamp}: {e}")
    return last_row_id

def get_entry_by_timestamp(timestamp_val: int) -> Optional[Entry]:
    """Retrieves a single entry by its timestamp."""
    entry: Optional[Entry] = None
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, app, title, text, timestamp, embedding, filename, page_url FROM entries WHERE timestamp = ?", (timestamp_val,))
            row = cursor.fetchone()
            if row:
                embedding_val = row["embedding"]
                if embedding_val and len(embedding_val) > 0:
                    embedding = np.frombuffer(embedding_val, dtype=np.float32)
                else:
                    embedding = np.array([], dtype=np.float32)
                
                entry = Entry(
                    id=row["id"],
                    app=row["app"],
                    title=row["title"],
                    text=row["text"],
                    timestamp=row["timestamp"],
                    embedding=embedding,
                    filename=row["filename"],
                    page_url=row["page_url"]
                )
    except sqlite3.Error as e:
        print(f"Database error while fetching entry by timestamp {timestamp_val}: {e}")
    return entry