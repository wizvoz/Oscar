#
# FILENAME: app.py
# AUTHOR:   Dora (Revised)
# VERSION:  1.18 (Added /config endpoint for GUI)
# DESCR:    This Flask application serves a custom HTML GUI for yt-dlp.
#           It handles download requests, executes the yt-dlp process,
#           and saves download history to a local SQLite database.
#

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import subprocess
import os
import sqlite3
import threading
from queue import Queue
from datetime import datetime
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DATABASE_FILE = 'downloads.db'
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
LOG_QUEUE = Queue()
APP_VERSION = "1.18"

# ==============================================================================
# DATABASE SETUP & HELPERS
# ==============================================================================
# ... (this section is unchanged) ...
def init_database():
    """Initializes the SQLite database with the downloads table."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        filename TEXT NOT NULL,
        destination TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_download_to_db(url, filename, destination):
    """Saves a completed download's details to the database."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO downloads (url, filename, destination) VALUES (?, ?, ?)
    ''', (url, filename, destination))
    conn.commit()
    conn.close()
    
def get_download_history():
    """Fetches all download history from the database."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    cursor = conn.cursor()
    cursor.execute('SELECT url, filename, destination, timestamp FROM downloads ORDER BY timestamp DESC')
    history = cursor.fetchall()
    conn.close()
    return [dict(row) for row in history]

# ==============================================================================
# FLASK APP & HELPER FUNCTIONS
# ==============================================================================
# ... (this section is unchanged) ...
app = Flask(__name__)
CORS(app)

def run_yt_dlp(url, destination_path):
    """Executes the yt-dlp command-line process in a separate thread."""
    try:
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
            LOG_QUEUE.put(f"[INFO] Created download directory: {destination_path}")

        is_windows = sys.platform == "win32"
        yt_dlp_exe = 'yt-dlp.exe' if is_windows else 'yt-dlp'
        ffmpeg_exe = 'ffmpeg.exe' if is_windows else 'ffmpeg'

        yt_dlp_path = os.path.join(os.getcwd(), yt_dlp_exe)
        ffmpeg_path = os.path.join(os.getcwd(), ffmpeg_exe)
        
        if not os.path.exists(yt_dlp_path):
            LOG_QUEUE.put(f"[ERROR] Critical: {yt_dlp_exe} not found in {os.getcwd()}")
            LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")
            return
            
        command = [
            yt_dlp_path,
            '--output', os.path.join(destination_path, '%(title)s.%(ext)s'),
            '--merge-output-format', 'mp4',
            '--no-progress',
            '--ffmpeg-location', ffmpeg_path,
            url
        ]
        
        LOG_QUEUE.put(f"[INFO] Running command: {' '.join(command)}")
        
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True, 
            encoding='utf-8',
            errors='replace'
        )

        filename = None
        for line in process.stdout:
            clean_line = line.strip()
            LOG_QUEUE.put(clean_line)
            if "[download] Destination:" in clean_line:
                filename = os.path.basename(clean_line.split('Destination:')[1].strip())
            elif "has already been downloaded" in clean_line and "[download] " in clean_line:
                 try:
                    filename = os.path.basename(clean_line.split("[download] ")[1].split(" has already been downloaded")[0].strip())
                 except Exception:
                    pass

        process.wait()

        if process.returncode == 0 and filename:
            LOG_QUEUE.put(f"[SUCCESS] Download completed for '{url}'")
            save_download_to_db(url, filename, destination_path)
        elif process.returncode == 0 and not filename:
            LOG_QUEUE.put(f"[WARNING] Process exited successfully but no filename was captured.")
        else:
            LOG_QUEUE.put(f"[ERROR] Download failed for '{url}' with return code: {process.returncode}")
        
        LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")

    except FileNotFoundError:
        LOG_QUEUE.put(f"[ERROR] A required file was not found. Ensure yt-dlp and ffmpeg are in the root directory.")
        LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")
    except Exception as e:
        LOG_QUEUE.put(f"[ERROR] An unexpected error occurred: {e}")
        LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")


# ==============================================================================
# FLASK WEB ROUTES
# ==============================================================================
@app.route('/')
def index():
    return render_template('index.html') # Version is now loaded by JS

@app.route('/start-download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    destination_path = DOWNLOAD_DIR
    if not url:
        return jsonify({"status": "error", "message": "No URL provided"}), 400
    download_thread = threading.Thread(target=run_yt_dlp, args=(url, destination_path), daemon=True)
    download_thread.start()
    return jsonify({"status": "success", "message": "Download process initiated."})

@app.route('/stream-logs')
def stream_logs():
    def generate():
        while True:
            message = LOG_QUEUE.get()
            yield f"data: {message}\n\n"
            if "---DOWNLOAD_COMPLETE---" in message:
                break
    return Response(generate(), mimetype='text/event-stream')
    
@app.route('/get-history')
def get_history():
    history = get_download_history()
    return jsonify(history)

# --- NEW AND REVISED ROUTES ---
@app.route('/config')
def get_config():
    """Provides essential configuration to the frontend."""
    return jsonify({
        'version': APP_VERSION,
        'download_dir': DOWNLOAD_DIR
    })

# ==============================================================================
# MAIN EXECUTION BLOCK
# ==============================================================================
# ... (this section is unchanged) ...
if __name__ == '__main__':
    print(f"[DEBUG] App version {os.path.basename(__file__)} {APP_VERSION} loaded.")
    init_database()
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"[DEBUG] Created default download directory: {DOWNLOAD_DIR}")
    app.run(debug=True, threaded=True)