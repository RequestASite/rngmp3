import subprocess
import os
import glob

def download_video(url, dir, format="mp3"):
    """
    Downloads a video from the given URL and saves it as either MP3 or MP4.

    :param url: The URL of the video to download.
    :param dir: The directory where the downloaded file(s) should be saved.
    :param format: The desired format ("mp3" for audio, "mp4" for video).
    :return: A list of downloaded file names or an error message.
    """


    # Specify the location of ffmpeg
    ffmpeg_location = r"./ffmpeg-master-latest-win64-gpl-shared/bin/ffmpeg.exe"

    # Construct yt-dlp command based on the format
    if format == "mp3":
        command = f'yt-dlp -f bestaudio --extract-audio --audio-format mp3 -o "{os.path.join(dir, "%(title)s.%(ext)s")}" --ffmpeg-location "{ffmpeg_location}" "{url}"'
        file_extension = "mp3"
    elif format == "mp4":
        command = f'yt-dlp -f bestvideo+bestaudio --merge-output-format mp4 -o "{os.path.join(dir, "%(title)s.%(ext)s")}" --ffmpeg-location "{ffmpeg_location}" "{url}"'
        file_extension = "mp4"
    else:
        return {"error": "Invalid format specified. Use 'mp3' or 'mp4'."}

    try:
        # Run the command to download
        subprocess.run(command, shell=True, check=True)
        print(f"Download successful for: {url}")

        # Get a list of all downloaded files with the correct extension
        downloaded_files = glob.glob(os.path.join(dir, f"*.{file_extension}"))
        file_names = [os.path.basename(f) for f in downloaded_files]

        return file_names  # Return list of downloaded filenames

    except subprocess.CalledProcessError as e:
        print(f"Error during download: {e}")
        return {"error": f"Download failed."}
    except Exception as e:
        print(f"Unexpected error: Download Failed")
        return {"error": f"Unexpected error: Download Failed"}
