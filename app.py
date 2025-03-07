import os
import uuid
import shutil  # Import shutil for removing directories
from flask import Flask, request, jsonify, send_from_directory, render_template, session
from download import download_video  # Ensure this function is working as expected
from flask import make_response  # Import to manage response and cookies
from datetime import datetime, timedelta
from flask import make_response, jsonify
import stat

BASE_DOWNLOAD_DIR = "./static/music"
if not os.path.exists(BASE_DOWNLOAD_DIR):
    os.makedirs(BASE_DOWNLOAD_DIR)

search_strings = ["mp3", "mp4"]

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Make sure to set a strong secret key for session management


def force_delete_folder(folder_path):
    """ Forcefully deletes a folder, even if files are locked or read-only. """
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.chmod(file_path, stat.S_IWRITE)  # Make file writable
                os.remove(file_path)  # Delete file
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")

        for dir in dirs:
            try:
                os.rmdir(os.path.join(root, dir))  # Delete subdirectory
            except Exception as e:
                print(f"Failed to delete directory {dir}: {e}")

    try:
        os.rmdir(folder_path)  # Delete main directory
        print(f"Successfully deleted {folder_path}")
    except Exception as e:
        print(f"Failed to delete folder {folder_path}: {e}")


@app.route("/", methods=["GET", "POST"])
def index():
    # Generate session token if it doesn't exist
    if 'session_token' not in session:
        session['session_token'] = str(uuid.uuid4())  # Generate a new UUID for the session
        print(f"Generated new session token: {session['session_token']}")  # Debugging log

    session_token = session.get('session_token')
    print(f"Session token retrieved: {session_token}")  # Debugging log

    if request.method == "POST":
        url = request.form.get("url")
        format = request.form.get("format", "mp3")

        if not url:
            return jsonify({"error": "URL is required"}), 400

        if format not in search_strings:
            return jsonify({"error": f"Invalid format: {format}. Valid formats are: {', '.join(search_strings)}"}), 400

        try:
            user_download_dir = os.path.join(BASE_DOWNLOAD_DIR, session_token)
            if not os.path.exists(user_download_dir):
                os.makedirs(user_download_dir)

            downloaded_files = download_video(url, user_download_dir, format=format)
            print("DUUUURRR")
            print(user_download_dir)

            if isinstance(downloaded_files, dict) and "error" in downloaded_files:
                return jsonify(downloaded_files), 500

            if not downloaded_files:
                return jsonify({"error": "No files were downloaded"}), 500

            return jsonify(downloaded_files)  # Return the downloaded files as JSON

        except Exception as e:
            print(f"Error during download: {e}")
            return jsonify({"error": f"Download failed: {e}"}), 500

    return render_template("index.html")



@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/clear_files", methods=["POST"])
def clear_files():
    try:
        session_token = session.get('session_token')
        if not session_token:
            return jsonify({"error": "No session token found"}), 400

        user_download_dir = os.path.join(BASE_DOWNLOAD_DIR, session_token)
        if not os.path.exists(user_download_dir):
            return jsonify({"error": "User's download folder does not exist"}), 400

        shutil.rmtree(user_download_dir, ignore_errors=True)
        
        session.pop('session_token', None)  # Only delete session after cleanup

        return jsonify({"success": True, "deleted_directory": user_download_dir})

    except Exception as e:
        return jsonify({"error": f"Failed to clear files: {e}"}), 500

@app.route("/static/music/<path:filename>")
def serve_music(filename):
    """Serve files from the static/music directory."""
    return send_from_directory(BASE_DOWNLOAD_DIR, filename)


if __name__ == "__main__": 
    app.run(debug=True)
