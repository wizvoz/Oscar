#
# FILENAME: app.py
# AUTHOR:   Dora (Revised)
# VERSION:  1.29 (PyInstaller compatibility)
# DESCR:    Adds a resource_path function and updates the Flask app
#           constructor to be compatible with PyInstaller packaging.
#

import sys
import os
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import subprocess
import sqlite3
from datetime import datetime
import glob
import json
from queue import Queue
import threading

# ==============================================================================
# CONFIGURATION & PATHING
# ==============================================================================
DATABASE_FILE = 'downloads.db'
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
APP_VERSION = "1.29"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==============================================================================
# FLASK APP SETUP
# ==============================================================================
app = Flask(
    __name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static')
)
CORS(app)

# --- The rest of the file (database functions, routes, etc.) is unchanged ---
def init_database():
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS downloads (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, filename TEXT NOT NULL, destination TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_download_history():
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT url, filename, destination, timestamp FROM downloads ORDER BY timestamp DESC')
    history_rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in history_rows]

def save_download_to_db(url, filename, destination):
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO downloads (url, filename, destination) VALUES (?, ?, ?)''', (url, filename, destination))
    conn.commit()
    conn.close()

def stream_yt_dlp_process(url, destination_path):
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)
        yield f"data: [INFO] Created download directory: {destination_path}\n\n"
    is_windows = sys.platform == "win32"
    yt_dlp_exe = 'yt-dlp.exe' if is_windows else 'yt-dlp'
    ffmpeg_exe = 'ffmpeg.exe' if is_windows else 'ffmpeg'
    yt_dlp_path = os.path.join(os.getcwd(), yt_dlp_exe)
    ffmpeg_path = os.path.join(os.getcwd(), ffmpeg_exe)
    if not os.path.exists(yt_dlp_path):
        yield f"data: [ERROR] Critical: {yt_dlp_exe} not found in {os.getcwd()}\n\n"
        yield f"data: ---DOWNLOAD_COMPLETE---\n\n"
        return
    command = [
        yt_dlp_path, '--no-playlist', '--output', os.path.join(destination_path, '%(title)s.%(ext)s'),
        '--merge-output-format', 'mp4', '--no-progress', '--ffmpeg-location', ffmpeg_path, url
    ]
    yield f"data: [INFO] Running command: {' '.join(command)}\n\n"
    final_filename = None
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='replace')
        for line in process.stdout:
            clean_line = line.strip()
            yield f"data: {clean_line}\n\n"
            if "[Merger] Merging formats into" in clean_line:
                try: final_filename = clean_line.split('"')[1]
                except IndexError: pass
            elif "has already been downloaded" in clean_line and "[download] " in clean_line:
                try: final_filename = clean_line.split("[download] ")[1].split(" has already been downloaded")[0].strip()
                except Exception: pass
            elif final_filename is None and "[download] Destination:" in clean_line:
                final_filename = clean_line.split('Destination:')[1].strip()
        process.wait()
        if process.returncode == 0 and final_filename:
            db_filename = os.path.basename(final_filename)
            with app.app_context(): save_download_to_db(url, db_filename, destination_path)
            yield f"data: [SUCCESS] Download completed for '{db_filename}'\n\n"
        else: yield f"data: [ERROR] Download failed for '{url}' with return code: {process.returncode}\n\n"
    except Exception as e: yield f"data: [ERROR] A server-side exception occurred: {e}\n\n"
    finally: yield f"data: ---DOWNLOAD_COMPLETE---\n\n"

@app.route('/')
def index():
    url = request.args.get('url', '')
    config_data = {'version': APP_VERSION, 'download_dir': DOWNLOAD_DIR}
    history_data = get_download_history()
    return render_template('index.html', video_url=url, config_data=json.dumps(config_data), history_data=json.dumps(history_data))

@app.route('/start-download-stream')
def start_download_stream():
    url = request.args.get('url')
    if not url:
        def error_gen():
            yield "data: [ERROR] No URL provided.\n\n"
            yield "data: ---DOWNLOAD_COMPLETE---\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    return Response(stream_yt_dlp_process(url, DOWNLOAD_DIR), mimetype='text/event-stream')

@app.route('/cleanup_partials', methods=['POST'])
def cleanup_partials():
    deleted_count = 0
    search_path = os.path.join(DOWNLOAD_DIR, '*.part')
    partial_files = glob.glob(search_path)
    for f in partial_files:
        try: os.remove(f); deleted_count += 1
        except OSError: pass
    return jsonify({"deleted_count": deleted_count})

if __name__ == '__main__':
    init_database()
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    app.run(host='0.0.0.0', debug=True, threaded=True)