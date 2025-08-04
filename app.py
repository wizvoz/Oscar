#
# FILENAME: app.py
# AUTHOR:   Dora (Revised)
# VERSION:  1.9 (Final fix for quoting issues with subprocess)
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

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DATABASE_FILE = 'downloads.db'
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
LOG_QUEUE = Queue()

# ==============================================================================
# DATABASE SETUP & HELPERS
# ==============================================================================
def init_database():
    """Initializes the SQLite database with the downloads table."""
    conn = sqlite3.connect(DATABASE_FILE)
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
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO downloads (url, filename, destination) VALUES (?, ?, ?)
    ''', (url, filename, destination))
    conn.commit()
    conn.close()
    
def get_download_history():
    """Fetches all download history from the database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT url, filename, destination, timestamp FROM downloads ORDER BY timestamp DESC')
    history = cursor.fetchall()
    conn.close()
    
    # Convert list of tuples to list of dictionaries for easier JSON handling
    history_dicts = []
    for row in history:
        history_dicts.append({
            "url": row[0],
            "filename": row[1],
            "destination": row[2],
            "timestamp": row[3]
        })
    return history_dicts

# ==============================================================================
# FLASK APP & HELPER FUNCTIONS
# ==============================================================================
app = Flask(__name__)
CORS(app)  # Enable CORS for the entire application

def run_yt_dlp(url, destination_path):
    """Executes the yt-dlp command-line process in a separate thread."""
    try:
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
            LOG_QUEUE.put(f"[INFO] Created download directory: {destination_path}")
        
        yt_dlp_path = os.path.join(os.getcwd(), 'yt-dlp.exe')
        ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg.exe')

        # Build the command as a list of arguments for robust subprocess handling
        # This is the correct way to handle paths with spaces and quoting
        command = [
            yt_dlp_path,
            '--output', os.path.join(destination_path, '%(title)s.%(ext)s'),
            '--merge-output-format', 'mp4',
            '--no-progress',
            '--ffmpeg-location', ffmpeg_path,
            url
        ]
        
        LOG_QUEUE.put(f"[INFO] Running command: {' '.join(command)}")
        
        # Use shell=False for security and to avoid quoting issues
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        filename = None
        for line in process.stdout:
            LOG_QUEUE.put(line.strip())
            if "[download] Destination:" in line:
                filename = os.path.basename(line.split('Destination:')[1].strip())
            
        process.wait()

        if process.returncode == 0 and filename:
            LOG_QUEUE.put(f"[SUCCESS] Download completed for '{url}'")
            save_download_to_db(url, filename, destination_path)
            LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")
        else:
            LOG_QUEUE.put(f"[ERROR] Download failed for '{url}'")
            LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")

    except Exception as e:
        LOG_QUEUE.put(f"[ERROR] An unexpected error occurred: {e}")
        LOG_QUEUE.put("---DOWNLOAD_COMPLETE---")

# ==============================================================================
# FLASK WEB ROUTES
# ==============================================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    
    destination_path = DOWNLOAD_DIR
    
    if not url:
        return jsonify({"status": "error", "message": "No URL provided"}), 400

    download_thread = threading.Thread(target=run_yt_dlp, args=(url, destination_path))
    download_thread.start()

    return jsonify({"status": "success", "message": "Download started."})

@app.route('/stream-logs')
def stream_logs():
    def generate():
        while True:
            message = LOG_QUEUE.get()
            yield f"data: {message}\n\n"
            if message == "---DOWNLOAD_COMPLETE---":
                break
    return Response(generate(), mimetype='text/event-stream')

@app.route('/get-history')
def get_history():
    history = get_download_history()
    return jsonify(history)

# ==============================================================================
# MAIN EXECUTION BLOCK
# ==============================================================================
if __name__ == '__main__':
    if not os.path.exists(DATABASE_FILE):
        init_database()
    
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"Created default download directory: {DOWNLOAD_DIR}")
        
    app.run(debug=True)
