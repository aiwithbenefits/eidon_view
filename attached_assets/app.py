import os
import sys
from threading import Thread
import re
from datetime import datetime, date, timedelta
import time
import uuid # Ensure this is here for the adhoc endpoint

import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, url_for
from urllib.parse import urlparse
import datetime as dt_module # Renaming to avoid conflict with 'datetime' object from 'from datetime import datetime'
from jinja2 import BaseLoader 
from markupsafe import Markup 
from PIL import Image # Ensure this is here for the adhoc endpoint

from eidon.config import appdata_folder, screenshots_path, ARCHIVE_DIR, WEBP_QUALITY
# Corrected database import to include insert_entry and get_entry_by_timestamp
from eidon.database import (
    create_db, 
    get_all_entries, 
    get_timestamps, 
    get_entry_by_timestamp, 
    insert_entry # Make sure this is included
)
from eidon.nlp import cosine_similarity, get_embedding, tokenize_text
from eidon.screenshot import record_screenshots_thread, pause_capture, resume_capture, is_capture_active
from eidon.utils import human_readable_time, timestamp_to_human_readable, parse_prefixed_filters
from eidon.archiver import run_archiver, get_archived_image_data
from eidon.ocr import extract_text_from_image # <--- ADD THIS IMPORT

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    static_url_path='/static'
)

# Custom Jinja2 filter: nl2br
def nl2br_filter(value):
    if value is None:
        return ''
    s_value = str(value)
    return Markup(re.sub(r'\r\n|\r|\n', '<br>\n', s_value))

# Custom filter for shorter date/time for cards
def timestamp_to_short_format(timestamp_val):
    # Using dt_module.datetime to refer to the datetime class from the imported datetime module
    dt_object = dt_module.datetime.fromtimestamp(timestamp_val) 
    today = dt_module.date.today() # Using dt_module.date
    if dt_object.date() == today:
        return dt_object.strftime("Today, %I:%M %p")
    yesterday = today - dt_module.timedelta(days=1) # Using dt_module.timedelta
    if dt_object.date() == yesterday:
       return dt_object.strftime("Yesterday, %I:%M %p")
    return dt_object.strftime("%b %d, %Y, %I:%M %p")


app.jinja_env.filters["human_readable_time"] = human_readable_time
app.jinja_env.filters["timestamp_to_human_readable"] = timestamp_to_human_readable
app.jinja_env.filters["timestamp_to_short_format"] = timestamp_to_short_format
app.jinja_env.filters["nl2br"] = nl2br_filter

def get_app_icon_url(app_name, page_url=None):
    """Return Google favicon for page_url if given, else Bootstrap Icons CDN URL for app_name."""
    if page_url:
        domain = urlparse(page_url).netloc
        return f'https://www.google.com/s2/favicons?sz=64&domain={domain}'
    if not app_name:
        return ''
    slug = re.sub(r'[^a-z0-9\\-]', '', app_name.lower().strip().replace(' ', '-'))
    return f'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/icons/{slug}.svg'

@app.route("/screenshots_file/<path:filename>")
def serve_screenshot(filename):
    screenshots_file_path = os.path.join(screenshots_path, filename)
    if os.path.exists(screenshots_file_path):
        return send_from_directory(screenshots_path, filename)

    archived_data = get_archived_image_data(filename)
    if archived_data:
        return Response(archived_data, mimetype='image/webp')
    
    return "Image not found", 404

@app.route("/entry_details/<int:timestamp_val>")
def entry_details(timestamp_val):
    entry = get_entry_by_timestamp(timestamp_val)
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    entry_dict = {
        "id": entry.id,
        "app": entry.app,
        "title": entry.title,
        "text": entry.text,
        "timestamp": entry.timestamp,
        "filename": entry.filename,
        "page_url": entry.page_url,
        "app_icon_url": get_app_icon_url(entry.app, entry.page_url),
        "timestamp_hr": timestamp_to_human_readable(entry.timestamp),
        "text_preview": entry.text[:500] if entry.text else ""
    }
    return jsonify(entry_dict)


@app.route("/")
def timeline():
    timestamps = get_timestamps() 
    initial_img_src = ""
    initial_alt_text = "No image available to display."
    initial_metadata_html = "<small>No metadata available for the initial view.</small>"
    initial_app_icon_url = ""

    if timestamps:
        first_timestamp = timestamps[0]
        first_entry = get_entry_by_timestamp(first_timestamp)
        if first_entry and first_entry.filename:
            initial_img_src = f"/screenshots_file/{first_entry.filename}"
            initial_alt_text = f"Screenshot recorded at {timestamp_to_human_readable(first_entry.timestamp)}"
            
            initial_metadata_html = ""
            if first_entry.app: initial_metadata_html += f"<div><strong>App:</strong> {first_entry.app}</div>"
            if first_entry.title: initial_metadata_html += f"<div><strong>Title:</strong> {first_entry.title}</div>"
            if first_entry.page_url: initial_metadata_html += f"<div><strong>URL:</strong> <a href='{first_entry.page_url}' target='_blank'>{first_entry.page_url}</a></div>"
            if not initial_metadata_html: initial_metadata_html = "<small>Details will load shortly.</small>"

        else:
            initial_img_src = "" 
            initial_alt_text = "Image data unavailable (no filename for initial entry)"
            initial_metadata_html = "<small class='text-danger'>Initial image or its details are unavailable.</small>"
    else:
        initial_metadata_html = "<small>No screenshots recorded yet.</small>"

    # assign dynamic app icons for timeline initial display
    if timestamps and first_entry:
        initial_app_icon_url = get_app_icon_url(first_entry.app, first_entry.page_url)

    # assign dynamic app icons for timeline initial display
    # no entries list, only initial_metadata_html; client-side fetch will use /entry_details
    return render_template(
        "timeline.html",
        timestamps=timestamps,
        initial_img_src=initial_img_src,
        initial_alt_text=initial_alt_text,
        initial_app_icon_url=initial_app_icon_url,
        initial_metadata_html=initial_metadata_html
    )

@app.route("/search")
def search():
    raw_q = request.args.get("q", "")
    filters, core_q = parse_prefixed_filters(raw_q)
    q = core_q.strip()
    if not q and not filters:
        return render_template("search_prompt.html")

    all_db_entries = get_all_entries()
    
    q_lower = q.lower()
    query_tokens = tokenize_text(q_lower)
    
    token_matched_entries = []
    if query_tokens:
        for e in all_db_entries:
            search_parts = []
            if e.text: search_parts.append(e.text.lower())
            if e.app: search_parts.append(e.app.lower())
            if e.title: search_parts.append(e.title.lower())
            if e.page_url: search_parts.append(e.page_url.lower())
            
            if not search_parts: continue

            combined_text = " ".join(search_parts)
            entry_tokens = tokenize_text(combined_text)
            
            if query_tokens.issubset(entry_tokens):
                token_matched_entries.append(e)

    if query_tokens:
        candidate_entries = token_matched_entries
    else:
        candidate_entries = all_db_entries

    filtered_entries = []
    for e in candidate_entries:
        ok = True
        # Using dt_module.datetime for consistency
        if "date" in filters and dt_module.datetime.fromtimestamp(e.timestamp).date() != filters["date"]:
            ok = False
        if ok and "time" in filters:
            etime = dt_module.datetime.fromtimestamp(e.timestamp).time()
            tfilter = filters["time"]
            if isinstance(tfilter, tuple):
                if not (tfilter[0] <= etime <= tfilter[1]):
                    ok = False
            else:
                if etime.strftime("%H:%M") != tfilter.strftime("%H:%M"):
                    ok = False
        if ok and "title" in filters and (not e.title or filters["title"] not in e.title.lower()):
            ok = False
        if "url" in filters:
            raw_url = e.page_url.lower() if e.page_url else ""
            norm_url = re.sub(r'^https?://(www\\.)?', '', raw_url)
            domain = norm_url.split('/')[0]
            if filters["url"] not in domain:
                ok = False
        if ok:
            filtered_entries.append(e)
    candidate_entries = filtered_entries if filters else candidate_entries

    if not q and filters:
        results_to_display = sorted(candidate_entries, key=lambda e: e.timestamp, reverse=True)
    else:
        has_emb = any(e.embedding is not None and e.embedding.size > 0 for e in candidate_entries)
        if q and has_emb:
            entries_with_embeddings = [e for e in candidate_entries if e.embedding is not None and e.embedding.size > 0]
            entries_without_embeddings = [e for e in candidate_entries if not (e.embedding is not None and e.embedding.size > 0)]
            entries_without_embeddings.sort(key=lambda e: e.timestamp, reverse=True)
            query_emb = get_embedding(q)
            if query_emb is None or np.all(query_emb == 0):
                results_to_display = entries_without_embeddings
            else:
                sims = [cosine_similarity(query_emb, e.embedding) for e in entries_with_embeddings]
                ranked = [pair[0] for pair in sorted(zip(entries_with_embeddings, sims), key=lambda p: p[1], reverse=True)]
                results_to_display = ranked + entries_without_embeddings
        else:
            results_to_display = sorted(candidate_entries, key=lambda e: e.timestamp, reverse=True)

    # build list of dicts with dynamic app icons for search results
    entries_with_icons = []
    for e in results_to_display:
        entry_dict = dict(e._asdict())
        entry_dict.pop('embedding', None)
        entry_dict['app_icon_url'] = get_app_icon_url(e.app, e.page_url)
        entries_with_icons.append(entry_dict)
    return render_template(
        "search_results.html",
        entries=entries_with_icons,
        query=q
    )

@app.route("/api/capture_status")
def api_capture_status():
    status = "active" if is_capture_active() else "paused"
    return jsonify({"status": status})

@app.route("/api/toggle_capture", methods=["POST"])
def api_toggle_capture():
    if is_capture_active():
        pause_capture()
        new_status = "paused"
    else:
        resume_capture()
        new_status = "active"
    return jsonify({"status": new_status})

# Adhoc capture endpoint starts here
@app.route("/api/add_adhoc_capture", methods=["POST"])
def api_add_adhoc_capture():
    if 'screenshot_file' not in request.files:
        return jsonify({"status": "error", "message": "No screenshot_file part in request"}), 400
    
    file = request.files['screenshot_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected in request"}), 400

    app_name = request.form.get('app_name', "Unknown App (Adhoc)")
    if not app_name or app_name.strip() == "":
        app_name = "Unknown App (Adhoc)"
        
    window_title = request.form.get('window_title', "Unknown Title (Adhoc)")
    if not window_title or window_title.strip() == "":
        window_title = "Unknown Title (Adhoc)"

    page_url = request.form.get('page_url')
    if page_url and page_url.strip() == "":
        page_url = None

    timestamp = int(time.time())
    filename_base = f"{timestamp}_adhoc_{uuid.uuid4().hex}"
    filename_webp = filename_base + ".webp"
    filepath = os.path.join(screenshots_path, filename_webp)

    try:
        img = Image.open(file.stream)
        img.save(filepath, format="WEBP", quality=WEBP_QUALITY)
    except Exception as e:
        app.logger.error(f"Error saving adhoc screenshot {filename_webp}: {e}")
        return jsonify({"status": "error", "message": f"Could not process or save image: {str(e)}"}), 500

    text_content = ""
    embedding_vector = np.array([]) 

    try:
        text_content = extract_text_from_image(img) # Needs extract_text_from_image
    except Exception as e:
        app.logger.error(f"OCR error for adhoc capture {filename_webp}: {e}")
        # Continue with empty text

    if text_content and text_content.strip():
        try:
            embedding_vector = get_embedding(text_content)
        except Exception as e:
            app.logger.error(f"Embedding error for adhoc capture {filename_webp}: {e}")
            # Continue with empty embedding

    try:
        db_id = insert_entry( # Needs insert_entry
            text=text_content,
            timestamp=timestamp,
            embedding=embedding_vector,
            app=app_name,
            title=window_title,
            filename=filename_webp,
            page_url=page_url
        )
        # Check if insertion was skipped due to duplicate timestamp or genuinely failed
        if db_id is None:
            # To distinguish a "skipped duplicate" from a "failed insert", we can check if an entry with that timestamp now exists.
            # This assumes get_entry_by_timestamp is available and works.
            if get_entry_by_timestamp(timestamp):
                 app.logger.warning(f"Adhoc capture for timestamp {timestamp} (file: {filename_webp}) was likely skipped due to duplicate timestamp.")
            else:
                app.logger.error(f"Adhoc capture for {filename_webp} failed to insert into DB (not a duplicate).")
                # return jsonify({"status": "error", "message": "Database insertion failed."}), 500 # Optional: make it a hard fail
    except Exception as e:
        app.logger.error(f"Database insertion error for adhoc capture {filename_webp}: {e}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500

    app.logger.info(f"Successfully processed adhoc capture: {filename_webp}")
    return jsonify({"status": "success", "message": "Adhoc capture processed.", "filename": filename_webp})


if __name__ == "__main__":
    create_db()
    try:
        run_archiver()
    except Exception as e:
        print(f"Archiver error on startup: {e}", file=sys.stderr)

    print(f"Appdata folder: {appdata_folder}")
    print(f"Screenshots folder: {screenshots_path}")
    print(f"Archive folder: {ARCHIVE_DIR}")

    t = Thread(target=record_screenshots_thread)
    t.daemon = True
    t.start()

    app.run(host='0.0.0.0', port=8082, debug=True)
