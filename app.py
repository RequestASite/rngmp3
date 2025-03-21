import os
import shutil
import json
import uuid
import time
import subprocess
from flask import Flask, request, jsonify, send_from_directory, render_template, make_response
from download import download_video
from urllib.parse import unquote
import logging  
import threading
import queue
import io

BASE_DOWNLOAD_DIR = "./static/music"
if not os.path.exists(BASE_DOWNLOAD_DIR):
    os.makedirs(BASE_DOWNLOAD_DIR)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Setup Flask logger with UTF-8 encoding
app.logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
     
def cleanup_unused_folders():
    try:
        current_time = time.time()
        EXPIRATION_TIME = 6 * 60
        for folder in os.listdir(BASE_DOWNLOAD_DIR):
            folder_path = os.path.join(BASE_DOWNLOAD_DIR, folder)
            if os.path.isdir(folder_path):
                folder_mod_time = os.path.getmtime(folder_path)
                if current_time - folder_mod_time > EXPIRATION_TIME:
                    shutil.rmtree(folder_path)
                    app.logger.info(f"Deleted folder due to inactivity: {folder_path}")
    except Exception as e:
        app.logger.error(f"Error during cleanup: {e}")

@app.before_request
def before_request():
    cleanup_unused_folders()

def is_mobile(user_agent):
    mobile_agents = ["Android", "iPhone", "iPad", "Windows Phone"]
    for agent in mobile_agents:
        if agent in user_agent:
            return True
    return False

@app.route("/", methods=["GET", "POST"])
def index():
    user_folder = str(uuid.uuid4())
    user_download_path = os.path.join(BASE_DOWNLOAD_DIR, user_folder)
    if not os.path.exists(user_download_path):
        os.makedirs(user_download_path)

    user_agent = request.headers.get("User-Agent")
    if is_mobile(user_agent):
        template = "index_mobile.html"
    else:
        template = "index.html"

    if request.method == "POST":
        url = request.form.get("url")
        format = request.form.get("format", "mp3")

        if not url:
            app.logger.warning("No URL provided by user")
            return jsonify({"error": "URL is required"}), 400

        try:
            app.logger.info(f"Attempting to download video from URL: {url}")
            result_queue = queue.Queue()

            def run_download():
                result = download_video(url, user_download_path, format)
                with app.app_context():
                    if "error" in result:
                        app.logger.error(f"Download failed: {result['error']}")
                        retry_download(url, user_download_path, format, result_queue)
                    else:
                        downloaded_files = result["success"]
                        if "files_to_rename" in result:
                            for original, sanitized in result["files_to_rename"]:
                                try:
                                    os.rename(original, sanitized)
                                except Exception as e:
                                    app.logger.error(f"Error renaming {original} to {sanitized}: {e}")
                        response = make_response(jsonify(downloaded_files))
                        response.set_cookie("downloaded_files", json.dumps(downloaded_files), path="/", httponly=True)
                        response.set_cookie("user_folder", user_folder, path="/", httponly=True)
                        app.logger.info(f"Files downloaded successfully: {downloaded_files}")
                        result_queue.put(response)
                        if "files_to_delete" in result:
                            response.set_cookie("files_to_delete", json.dumps(result["files_to_delete"]), path="/", httponly=True)

            thread = threading.Thread(target=run_download)
            thread.start()
            thread.join()
            result = result_queue.get()
            return result

        except Exception as e:
            app.logger.error(f"Download failed: {e}")
            return jsonify({"error": f"Download failed: {e}"}), 500
         
    return render_template(template)

def retry_download(url, user_download_path, format, result_queue, max_retries=80):
    retries = 0
    while retries < max_retries:
        retries += 1
        app.logger.info(f"Retrying download (attempt {retries}/{max_retries}) for URL: {url}")
        result = download_video(url, user_download_path, format)
        if "error" not in result:
            with app.app_context():
                downloaded_files = result["success"]
                if "files_to_rename" in result:
                    for original, sanitized in result["files_to_rename"]:
                        try:
                            os.rename(original, sanitized)
                        except Exception as e:
                            app.logger.error(f"Error renaming {original} to {sanitized}: {e}")
                response = make_response(jsonify(downloaded_files))
                response.set_cookie("downloaded_files", json.dumps(downloaded_files), path="/", httponly=True)
                response.set_cookie("user_folder", os.path.basename(user_download_path), path="/", httponly=True)
                app.logger.info(f"Retry download successful: {downloaded_files}")
                result_queue.put(response)
                if "files_to_delete" in result:
                    response.set_cookie("files_to_delete", json.dumps(result["files_to_delete"]), path="/", httponly=True)
                return
        else:
            app.logger.error(f"Retry download failed: {result['error']}")
              # Wait before retrying

    with app.app_context():
        result_queue.put(jsonify({"error": "Download failed after multiple retries."}), 500)

def delete_file_with_retry(file_path, retries=20, delay=1):
    for attempt in range(retries):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                app.logger.info(f"Deleted file: {file_path}")
                return True
            else:
                app.logger.warning(f"File not found: {file_path}")
                return False
        except PermissionError as e:
            app.logger.warning(f"PermissionError while deleting {file_path}: {e}")
            if attempt < retries - 1:
                app.logger.info(f"Retrying to delete {file_path} in {delay} seconds...")
                time.sleep(delay)
            else:
                app.logger.error(f"Failed to delete file after {retries} attempts: {file_path}")
                return False
        except Exception as e:
            app.logger.error(f"Error deleting file {file_path}: {e}")
            return False
    return False

@app.route("/clear_files", methods=["POST"])
def clear_files():
    user_folder = request.cookies.get("user_folder")
    if not user_folder:
        return jsonify({"error": "No user-specific folder found"}), 400
    user_download_path = os.path.join(BASE_DOWNLOAD_DIR, user_folder)
    downloaded_files_cookie = request.cookies.get("downloaded_files")
    downloaded_files = json.loads(downloaded_files_cookie) if downloaded_files_cookie else []
    app.logger.info(f"Files to clear from {user_folder}: {downloaded_files}")
    if not downloaded_files:
        app.logger.warning("No files found to clear")
        return jsonify({"error": "No files found to clear"}), 400
    try:
        for file_name in downloaded_files:
            decoded_filename = unquote(file_name)  # Corrected line
            file_path = os.path.join(user_download_path, decoded_filename) #Added line
            app.logger.info(f"Attempting to delete file: {file_path}")
            success = delete_file_with_retry(file_path)
            if not success:
                app.logger.error(f"Failed to delete file: {file_path}")
        response = make_response(jsonify({"success": True, "message": "Specified files cleared successfully"}))
        response.set_cookie("downloaded_files", "", expires=0)
        response.set_cookie("user_folder", "", expires=0)
        app.logger.info(f"User folder {user_folder} cleared successfully.")
        return response
    except Exception as e:
        app.logger.error(f"Error while clearing files: {e}")
        return jsonify({"error": f"Failed to clear files: {e}"}), 500

@app.route("/faq")
def faq():
    user_agent = request.headers.get("User-Agent")
    if is_mobile(user_agent):
        template = "faq_mobile.html" 
    else:
        template = "faq.html"
    return render_template(template)

def delete_folder_with_retry(folder_path, retries=5, delay=1):
    for attempt in range(retries):
        try:
            if not os.listdir(folder_path):
                shutil.rmtree(folder_path)
                app.logger.info(f"Deleted folder: {folder_path}")
                return True
            else:
                app.logger.info(f"Folder not empty, retrying to delete: {folder_path}")
        except Exception as e:
            app.logger.warning(f"Error deleting folder {folder_path}: {e}")
        time.sleep(delay)
    app.logger.error(f"Failed to delete folder after {retries} attempts: {folder_path}")
    return False

@app.route("/static/music/<path:filename>")
def serve_music_file(filename):
    user_folder = request.cookies.get("user_folder")
    if not user_folder:
        return "Unauthorized", 403
    user_download_path = os.path.join(BASE_DOWNLOAD_DIR, user_folder)
    decoded_filename = unquote(filename)
    file_path = os.path.join(user_download_path, decoded_filename)
    if not os.path.exists(file_path):
        app.logger.warning(f"File not found: {file_path}")
        return "File not found", 404
    response = send_from_directory(user_download_path, decoded_filename)

    files_to_delete_cookie = request.cookies.get("files_to_delete")
    files_to_delete = json.loads(files_to_delete_cookie) if files_to_delete_cookie else []
    for filepath in files_to_delete:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                app.logger.info(f"Deleted file after serving: {filepath}")
        except Exception as e:
            app.logger.error(f"Error deleting file after serving {filepath}: {e}")

    # Attempt to delete the served file after sending
    try:
        os.remove(file_path)
        app.logger.info(f"Deleted served file: {file_path}")
    except Exception as e:
        app.logger.error(f"Error deleting served file {file_path}: {e}")

    # Attempt to delete the folder after serving
    success = delete_folder_with_retry(user_download_path)
    return response

def run_command(command):
    app.logger.info(f"Running command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        app.logger.info(f"Command output: {result.stdout}")
        if result.stderr:
            app.logger.error(f"Command error: {result.stderr}")
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Command failed with error: {e.stderr}")
        return e.stdout, e.stderr

if __name__ == "__main__":
    app.run(host='10.0.0.4', port=5000, debug=True)