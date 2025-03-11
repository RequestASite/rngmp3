import os
import shutil
import json
import uuid
import time
from flask import Flask, request, jsonify, send_from_directory, render_template, make_response
from download import download_video
from urllib.parse import unquote

BASE_DOWNLOAD_DIR = "./static/music"
if not os.path.exists(BASE_DOWNLOAD_DIR):
    os.makedirs(BASE_DOWNLOAD_DIR)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Make sure to set a secret key for session management

# Function to clean up folders that haven't been updated for a certain amount of time
def cleanup_unused_folders():
    try:
        current_time = time.time()
        EXPIRATION_TIME = 6 * 60  # Set expiration time 
        for folder in os.listdir(BASE_DOWNLOAD_DIR):
            folder_path = os.path.join(BASE_DOWNLOAD_DIR, folder)
            
            if os.path.isdir(folder_path):
                # Get the last modified time of the folder
                folder_mod_time = os.path.getmtime(folder_path)

                # Check if the folder has not been modified in the last EXPIRATION_TIME seconds
                if current_time - folder_mod_time > EXPIRATION_TIME:
                    shutil.rmtree(folder_path)
                    app.logger.info(f"Deleted folder due to inactivity: {folder_path}")
    except Exception as e:
        app.logger.error(f"Error during cleanup: {e}")


@app.before_request
def before_request():
    # Clean up unused folders every time a new request is made
    cleanup_unused_folders()

@app.route("/", methods=["GET", "POST"])
def index():
    # Generate a unique folder for each user
    user_folder = str(uuid.uuid4())  # Unique folder name for each user
    user_download_path = os.path.join(BASE_DOWNLOAD_DIR, user_folder)

    if not os.path.exists(user_download_path):
        os.makedirs(user_download_path)

    if request.method == "POST":
        url = request.form.get("url")
        format = request.form.get("format", "mp3")

        if not url:
            return jsonify({"error": "URL is required"}), 400

        try:
            # Download the video to the user-specific folder
            downloaded_files = download_video(url, user_download_path, format=format)

            if isinstance(downloaded_files, dict) and "error" in downloaded_files:
                return jsonify(downloaded_files), 500

            if not downloaded_files:
                return jsonify({"error": "No files were downloaded"}), 500

            # Store the downloaded files and the user folder info in cookies
            response = make_response(jsonify(downloaded_files))
            response.set_cookie("downloaded_files", json.dumps(downloaded_files), path="/", httponly=True)
            response.set_cookie("user_folder", user_folder, path="/", httponly=True)

            return response  

        except Exception as e:
            return jsonify({"error": f"Download failed: {e}"}), 500

    return render_template("index.html")

import logging

# Setup Flask logger
app.logger.setLevel(logging.DEBUG)  # Set the desired log level
file_handler = logging.FileHandler('app.log')  # Save logs to a file
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)

def delete_file_with_retry(file_path, retries=3, delay=1):
    """Attempt to delete a file with retries if it is locked."""
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
            decoded_filename = unquote(file_name)
            file_path = os.path.join(user_download_path, decoded_filename)
            app.logger.info(f"Attempting to delete file: {file_path}")

            success = delete_file_with_retry(file_path)
            if not success:
                app.logger.error(f"Failed to delete file: {file_path}")

        # After deletion, clear the cookies for this user
        response = make_response(jsonify({"success": True, "message": "Specified files cleared successfully"}))
        response.set_cookie("downloaded_files", "", expires=0)  # Clear the downloaded files cookie
        response.set_cookie("user_folder", "", expires=0)  # Clear the user folder cookie

        app.logger.info(f"User folder {user_folder} cleared successfully.")
        return response

    except Exception as e:
        app.logger.error(f"Error while clearing files: {e}")
        return jsonify({"error": f"Failed to clear files: {e}"}), 500

@app.route("/faq")
def faq():
    return render_template("faq.html")

import shutil

def delete_folder_with_retry(folder_path, retries=5, delay=1):
    """Attempt to delete a folder with retries if it is not empty."""
    for attempt in range(retries):
        try:
            # Check if folder is empty before trying to delete
            if not os.listdir(folder_path):  # Folder is empty
                shutil.rmtree(folder_path)
                app.logger.info(f"Deleted folder: {folder_path}")
                return True
            else:
                app.logger.info(f"Folder not empty, retrying to delete: {folder_path}")
        except Exception as e:
            app.logger.warning(f"Error deleting folder {folder_path}: {e}")
        
        # If folder is not empty, wait before retrying
        time.sleep(delay)
    
    app.logger.error(f"Failed to delete folder after {retries} attempts: {folder_path}")
    return False

@app.route("/static/music/<path:filename>")
def serve_music_file(filename):
    # Retrieve the user-specific folder from cookies
    user_folder = request.cookies.get("user_folder")

    if not user_folder:
        return "Unauthorized", 403  # If no user folder exists, deny access

    user_download_path = os.path.join(BASE_DOWNLOAD_DIR, user_folder)
    decoded_filename = unquote(filename)
    file_path = os.path.join(user_download_path, decoded_filename)

    if not os.path.exists(file_path):
        app.logger.warning(f"File not found: {file_path}")
        return "File not found", 404

    response = send_from_directory(user_download_path, decoded_filename)

    # After serving the file, delete it
    try:
        os.remove(file_path)
        app.logger.info(f"Deleted served file: {file_path}")
    except Exception as e:
        app.logger.error(f"Error deleting served file {file_path}: {e}")

    # Retry to delete the folder after serving and deleting the file
    success = delete_folder_with_retry(user_download_path)

    return response
if __name__ == "__main__":
    app.run(debug=True)
