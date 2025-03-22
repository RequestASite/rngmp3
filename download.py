import os
import subprocess
from playwright.sync_api import sync_playwright
import logging
import time
import urllib.parse
import glob
import re  # Import the regular expression module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

cookies_file = "cookies.txt"
youtube_url = "https://www.youtube.com"  # URL to check if cookies are valid

def convert_to_netscape(input_file, output_file):
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            outfile.write("# Netscape HTTP Cookie File\n")
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) == 6:
                    name, domain, path, secure, expiry, value = parts
                    outfile.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        logging.info(f"Cookies converted to Netscape format: {output_file}")
    except Exception as e:
        logging.error(f"Error converting cookies: {e}")

def load_cookies(context, cookies_file):
    if os.path.exists(cookies_file):
        with open(cookies_file, 'r') as f:
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
                        context.add_cookies([cookie])

def save_cookies(page, cookies_file):
    cookies = page.context.cookies()
    with open(cookies_file, 'w') as f:
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

def refresh_youtube_cookies():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            load_cookies(page.context, cookies_file)
            page.goto(youtube_url)
            time.sleep(5)  # Allow time for cookies to take effect
            save_cookies(page, cookies_file)
            browser.close()
            logging.info("YouTube cookies refreshed.")
    except Exception as e:
        logging.error(f"Error refreshing cookies: {e}")

def decode_utf8_with_replace(byte_string):
    try:
        decoded_string = byte_string.decode('utf-8')
        return urllib.parse.unquote(decoded_string)
    except UnicodeDecodeError:
        decoded_string = byte_string.decode('utf-8', errors='replace')
        return urllib.parse.unquote(decoded_string)

def sanitize_filename(filename):
    """Sanitizes a filename by removing or replacing problematic characters."""
    allowed_chars = r"[^a-zA-Z0-9_\-\.\(\) ]"  # Allow letters, numbers, underscores, hyphens, periods, parentheses, and spaces
    sanitized_name = re.sub(allowed_chars, "_", filename)
    return sanitized_name

def download_video(url, dir, format, ffmpeg_location=r"ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"):
    refresh_youtube_cookies()  # Refresh cookies before each download
    netscape_cookies = "netscape_cookies.txt"
    convert_to_netscape(cookies_file, netscape_cookies)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                logging.info(f"Downloading {url} to {dir} in {format} format.")
                page.goto(url)
                time.sleep(3)
                final_url_bytes = page.url.encode('utf-8')
                final_url = decode_utf8_with_replace(final_url_bytes)
            except Exception as e:
                logging.error(f"Playwright error: {e}")
                browser.close()
                return {"error": f"Playwright error: {e}"}
            browser.close()

        if format == "mp3":
            command = (
                f'yt-dlp -f bestaudio --extract-audio --audio-format mp3 '
                f'--cookies "{netscape_cookies}" '
                f'-o "{os.path.join(dir, "%(title)s.%(ext)s")}" '
                f'--ffmpeg-location "{ffmpeg_location}" "{final_url}"'
            )
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"yt-dlp error: {result.stderr}")
                return {"error": f"yt-dlp error: {result.stderr}"}
            mp3_files = glob.glob(os.path.join(dir, "*.mp3"))
            if not mp3_files:
                return {"error": "No mp3 files were downloaded."}
            file_names = [os.path.basename(file) for file in mp3_files]
            sanitized_file_names = [sanitize_filename(name) for name in file_names]
            files_to_rename = [] #store the files that need to be renamed.
            for original, sanitized in zip(file_names, sanitized_file_names):
                if original != sanitized:
                    files_to_rename.append((os.path.join(dir,original),os.path.join(dir,sanitized)))
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
            result_video = subprocess.run(command_video, shell=True, capture_output=True, text=True)
            result_audio = subprocess.run(command_audio, shell=True, capture_output=True, text=True)
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
                    subprocess.run(merge_command, shell=True, check=True)
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
            for original, sanitized in zip(output_files, sanitized_output_files):
                if original != sanitized:
                    os.rename(os.path.join(dir, original), os.path.join(dir, sanitized))

            return {"success": sanitized_output_files, "files_to_delete": files_to_delete} #return the files to be deleted

    except Exception as overall_e:
        logging.error(f"Overall download error: {overall_e}")
        return {"error": f"Overall download error: {overall_e}"}