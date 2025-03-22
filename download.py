import os
import subprocess
import logging
import urllib.parse
import glob
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='latin-1')

def convert_to_netscape(input_file, output_file):
    """
    Converts cookies from a simple tab-separated format to the Netscape format.

    Args:
        input_file (str): Path to the input file containing cookies.
        output_file (str): Path to the output file to save cookies in Netscape format.
    """
    try:
        with open(input_file, 'r', encoding='latin-1') as infile, open(output_file, 'w', encoding='latin-1') as outfile: #added encoding
            outfile.write("# Netscape HTTP Cookie File\n")
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) == 6:
                    name, domain, path, secure, expiry, value = parts
                    outfile.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        logging.info(f"Cookies converted to Netscape format: {output_file}")
    except Exception as e:
        logging.error(f"Error converting cookies: {e}")

def load_cookies(cookies_file):
    """
    Loads cookies from a Netscape-formatted file.

    Args:
        cookies_file (str): Path to the Netscape cookie file.

    Returns:
        list: A list of cookie dictionaries, or an empty list on error.
    """
    cookies = []
    if not os.path.exists(cookies_file):
        logging.warning(f"Cookie file not found: {cookies_file}")
        return []

    try:
        with open(cookies_file, 'r', encoding='latin-1') as f: #added encoding
            for line in f:
                line = line.strip()
                if not line.startswith("#"):
                    parts = line.split("\t")
                    if len(parts) == 7:
                        cookie = {}
                        cookie['domain'] = parts[0]
                        cookie['httpOnly'] = True if parts[1].upper() == "TRUE" else False
                        cookie['path'] = parts[2]
                        cookie['secure'] = True if parts[3].upper() == "TRUE" else False
                        try:
                            cookie['expires'] = int(float(parts[4])) if parts[4] else None
                        except ValueError:
                            logging.error(f"Invalid expires value: {parts[4]}")
                            cookie['expires'] = None
                        cookie['name'] = parts[5]
                        cookie['value'] = parts[6]
                        cookies.append(cookie)
                    else:
                        logging.warning(f"Skipping invalid cookie line: {line}")
        logging.info(f"Loaded {len(cookies)} cookies from {cookies_file}")
        return cookies
    except Exception as e:
        logging.error(f"Error loading cookies: {e}")
        return []

def save_cookies(cookies, cookies_file):
    """
    Saves cookies to a file in Netscape format.

    Args:
        cookies (list): A list of cookie dictionaries.
        cookies_file (str): Path to the output file to save cookies.
    """
    try:
        with open(cookies_file, 'w', encoding='latin-1') as f: #added encoding
            f.write("# Netscape HTTP Cookie File\n")
            for cookie in cookies:
                domain = cookie["domain"]
                http_only = "TRUE" if cookie.get("httpOnly") else "FALSE"
                path = cookie["path"]
                secure = "TRUE" if cookie["secure"] else "FALSE"
                expiry = cookie.get("expires", "")
                name = cookie["name"]
                value = cookie["value"]
                f.write(f"{domain}\t{http_only}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        logging.info(f"Saved {len(cookies)} cookies to {cookies_file}")
    except Exception as e:
        logging.error(f"Error saving cookies: {e}")

def decode_utf8_with_replace(byte_string):
    try:
        decoded_string = byte_string.decode('latin-1') #changed from utf-8
        return urllib.parse.unquote(decoded_string)
    except UnicodeDecodeError:
        decoded_string = byte_string.decode('latin-1', errors='replace') #changed from utf-8
        return urllib.parse.unquote(decoded_string)

def sanitize_filename(filename):
    """Sanitizes a filename by removing or replacing problematic characters."""
    allowed_chars = r"[^a-zA-Z0-9_\-\.\(\) ]"  # Allow letters, numbers, underscores, hyphens, periods, parentheses, and spaces
    sanitized_name = re.sub(allowed_chars, "_", filename)
    return sanitized_name


def download_video(url, dir, format, cookies_file="cookies.txt", ffmpeg_location=r"ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"):
    """
    Downloads a video or audio from a given URL, with cookie support, and handles file renaming.

    Args:
        url (str): The URL of the video to download.
        dir (str): The directory to save the downloaded file(s) to.
        format (str):  "mp3" for audio-only, "mp4" for video.
        cookies_file (str, optional): Path to the Netscape-formatted cookie file. Defaults to "cookies.txt".
        ffmpeg_location (str, optional): Path to the ffmpeg executable. Defaults to a relative path.

    Returns:
        dict:  A dictionary with either an "error" key and its message, or a "success" key
                and a list of downloaded file names, and "files_to_rename"
                which contains tuples of (original_path, sanitized_path)
    """
    netscape_cookies = "netscape_cookies.txt"
    convert_to_netscape(cookies_file, netscape_cookies) #convert the cookies

    try:
        logging.info(f"Downloading {url} to {dir} in {format} format.")
        final_url = url #in the previous version, the code was using playwright to get the final URL.
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": f"Error: {e}"}

    try:
        if format == "mp3":
            command = (
                f'yt-dlp -f bestaudio --extract-audio --audio-format mp3 '
                f'--cookies "{netscape_cookies}" '
                f'-o "{os.path.join(dir, "%(title)s.%(ext)s")}" '
                f'--ffmpeg-location "{ffmpeg_location}" "{final_url}"'
            )
            result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='latin-1') #added encoding
            if result.returncode != 0:
                logging.error(f"yt-dlp error: {result.stderr}")
                return {"error": f"yt-dlp error: {result.stderr}"}
            mp3_files = glob.glob(os.path.join(dir, "*.mp3"))
            if not mp3_files:
                return {"error": "No mp3 files were downloaded."}
            file_names = [os.path.basename(file) for file in mp3_files]
            sanitized_file_names = [sanitize_filename(name) for name in file_names]
            files_to_rename = []  # store the files that need to be renamed.
            for original, sanitized in zip(file_names, sanitized_file_names):
                if original != sanitized:
                    files_to_rename.append((os.path.join(dir, original), os.path.join(dir, sanitized)))
            return {"success": sanitized_file_names, "files_to_rename": files_to_rename}
        elif format == "mp4":
            command_video = (
                f'yt-dlp -f bestvideo[ext=mp4] --cookies "{netscape_cookies}" '
                f'-o "{os.path.join(dir, "%(title)s.%(ext)s")}" '
                f'--ffmpeg-location "{ffmpeg_location}" "{final_url}"'
            )
            command_audio = (
                f'yt-dlp -f bestaudio[ext=m4a] --cookies "{netscape_cookies}" '
                f'-o "{os.path.join(dir, "%(title)s.%(ext)s")}" '
                f'--ffmpeg-location "{ffmpeg_location}" "{final_url}"'
            )
            result_video = subprocess.run(command_video, shell=True, capture_output=True, text=True, encoding='latin-1') #added encoding
            result_audio = subprocess.run(command_audio, shell=True, capture_output=True, text=True, encoding='latin-1') #added encoding
            if result_video.returncode != 0:
                logging.error(f"yt-dlp video error: {result_video.stderr}")
                return {"error": f"yt-dlp video error: {result_video.stderr}"}
            if result_audio.returncode != 0:
                logging.error(f"yt-dlp audio error: {result_audio.stderr}")
                return {"error": f"yt-dlp audio error: {result_audio.stderr}"}
            video_files = glob.glob(os.path.join(dir, "*.mp4"))
            audio_files = glob.glob(os.path.join(dir, "*.m4a"))
            if len(video_files) != len(audio_files):
                return {"error": "Mismatch between video and audio files."}
            output_files = []
            files_to_delete = []  # Store paths of files to delete later

            for video_file, audio_file in zip(video_files, audio_files):
                output_file = os.path.splitext(video_file)[0] + "_final.mp4"
                merge_command = (
                    f'"{ffmpeg_location}" -i "{video_file}" -i "{audio_file}" '
                    f'-c:v copy -c:a aac -strict experimental "{output_file}"'
                )
                try:
                    subprocess.run(merge_command, shell=True, check=True, encoding='latin-1') #added encoding
                    output_files.append(os.path.basename(output_file))
                    files_to_delete.append(video_file)  # Store for later deletion
                    files_to_delete.append(audio_file)  # Store for later deletion

                except subprocess.CalledProcessError as e:
                    logging.error(f"FFmpeg merge error: {e.stderr}")
                    return {"error": f"FFmpeg merge error: {e.stderr}"}
                except Exception as e:
                    logging.error(f"Error merging files: {e}")
                    return {"error": f"Error merging files: {e}"}

            sanitized_output_files = [sanitize_filename(name) for name in output_files]
            files_to_rename = []
            for original, sanitized in zip(output_files, sanitized_output_files):
                if original != sanitized:
                    files_to_rename.append((os.path.join(dir,original),os.path.join(dir,sanitized)))

            return {"success": sanitized_output_files, "files_to_delete": files_to_delete, "files_to_rename": files_to_rename}  # return the files to be deleted
        else:
            return {"error": f"Invalid format: {format}"}
    except Exception as overall_e:
        logging.error(f"Overall download error: {overall_e}")
        return {"error": f"Overall download error: {overall_e}"}
