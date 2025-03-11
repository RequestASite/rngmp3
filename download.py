import subprocess
import os
import glob



def download_video(url, dir, format="mp3"):
    ffmpeg_location = r"ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"  # Absolute path to ffmpeg
    
    if format == "mp3":
        # Directly download audio as mp3 using yt-dlp
        command = f'yt-dlp -f bestaudio --extract-audio --audio-format mp3 -o "{os.path.join(dir, "%(title)s.%(ext)s")}" --ffmpeg-location "{ffmpeg_location}" "{url}"'
        subprocess.run(command, shell=True, check=True)
        
        # Get the downloaded mp3 files
        mp3_files = glob.glob(os.path.join(dir, "*.mp3"))
        if not mp3_files:
            return {"error": "No mp3 files were downloaded."}
        
        file_names = [os.path.basename(mp3) for mp3 in mp3_files]
        return file_names
    
    elif format == "mp4":
        # Download video and audio for each entry in the playlist
        command_video = f'yt-dlp -f bestvideo[ext=mp4] -o "{os.path.join(dir, "%(title)s.%(ext)s")}" --ffmpeg-location "{ffmpeg_location}" "{url}"'
        command_audio = f'yt-dlp -f bestaudio[ext=m4a] -o "{os.path.join(dir, "%(title)s.%(ext)s")}" --ffmpeg-location "{ffmpeg_location}" "{url}"'
        
        # Run the download commands for video and audio (playlist handling)
        subprocess.run(command_video, shell=True, check=True)
        subprocess.run(command_audio, shell=True, check=True)
        
        # Get the downloaded video and audio files for the playlist
        video_files = glob.glob(os.path.join(dir, "*.mp4"))
        audio_files = glob.glob(os.path.join(dir, "*.m4a"))
        
        if len(video_files) != len(audio_files):
            return {"error": "Mismatch between the number of video and audio files downloaded."}

        output_files = []
        
        for video_file, audio_file in zip(video_files, audio_files):
            # Ensure proper handling of spaces in filenames by quoting the paths
            video_file = f'"{video_file}"'
            audio_file = f'"{audio_file}"'
            
            # Define the output file for each video/audio pair
            output_file = os.path.splitext(video_file.strip('"'))[0] + "_final.mp4"
            output_file = f'"{output_file}"'
            
            # Merge the video and audio using ffmpeg
            merge_command = f'{ffmpeg_location} -i {video_file} -i {audio_file} -c:v copy -c:a aac -strict experimental {output_file}'
            subprocess.run(merge_command, shell=True, check=True)
            
            # Add the output file to the list
            output_files.append(os.path.basename(output_file.strip('"')))
            
            # Clean up the individual video and audio files
            os.remove(video_file.strip('"'))  # Remove the quotes
            os.remove(audio_file.strip('"'))  # Remove the quotes
        
        return output_files
    
    else:
        return {"error": "Invalid format specified. Use 'mp3' or 'mp4'."}

    try:
        # Get the downloaded final file(s)
        downloaded_files = glob.glob(os.path.join(dir, f"*.{file_extension}"))
        
        if not downloaded_files:
            return {"error": "No files were downloaded."}
        
        # Return the names of the final downloaded files
        file_names = [os.path.basename(f) for f in downloaded_files]
        return file_names

    except subprocess.CalledProcessError as e:
        return {"error": "Download failed."}
    except Exception as e:
        return {"error": "Unexpected error during download."}
