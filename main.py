from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import subprocess
import time
import threading
import glob

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File cleanup function
def cleanup_old_files():
    """Remove files older than 1 hour from temp directory"""
    try:
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            return
            
        current_time = time.time()
        for file_path in glob.glob(os.path.join(temp_dir, "*")):
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                # Remove files older than 1 hour (3600 seconds)
                if file_age > 3600:
                    try:
                        os.remove(file_path)
                        print(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        print(f"Error removing file {file_path}: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Schedule cleanup to run every 30 minutes
def schedule_cleanup():
    cleanup_old_files()
    # Schedule next cleanup
    threading.Timer(1800, schedule_cleanup).start()  # 1800 seconds = 30 minutes

# Start cleanup scheduler
schedule_cleanup()

@app.get("/clip")
def clip_video_direct(
    url: str = Query(...),
    start: str = Query(...),  # format: HH:MM:SS
    end: str = Query(...)
):
    """Alternative endpoint that downloads only the clipped portion directly"""
    os.makedirs("temp", exist_ok=True) 

    video_id = uuid.uuid4().hex
    clipped_path = os.path.join("temp", f"{video_id}_clip.mp4")

    # Convert time format to seconds for yt-dlp
    def time_to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        else:
            return int(parts[0])

    start_seconds = time_to_seconds(start)
    end_seconds = time_to_seconds(end)
    duration = end_seconds - start_seconds

    # yt-dlp options with direct trimming
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': clipped_path,
        'merge_output_format': 'mp4',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'postprocessor_args': [
            '-ss', str(start_seconds),
            '-t', str(duration),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k'
        ]
    }

    try:
        # Get video info first to extract title
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')
            # Clean filename - remove invalid characters
            clean_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_title = clean_title[:50]  # Limit length
            
        # Now download with the original options
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(clipped_path):
            return JSONResponse(content={"error": "Direct clip download failed."}, status_code=500)

        # Update file dates to current time - use both access and modify time
        try:
            current_time = time.time()
            os.utime(clipped_path, (current_time, current_time))
            # Also try to set creation time on Windows
            if os.name == 'nt':
                import stat
                os.chmod(clipped_path, stat.S_IWRITE)
        except Exception as date_error:
            print(f"Warning: Could not update file dates: {date_error}")

        return FileResponse(clipped_path, media_type="video/mp4", filename=f"{clean_title}_clip.mp4")

    except Exception as e:
        # Clean up in case of error
        try:
            if os.path.exists(clipped_path):
                os.remove(clipped_path)
        except:
            pass
        
        return JSONResponse(content={"error": "Internal server error", "details": str(e)}, status_code=500)

@app.get("/voice")
def extract_voice(
    url: str = Query(...),
    start: str = Query(...),  # format: HH:MM:SS
    end: str = Query(...)
):
    """Downloads only the audio portion of the selected time range"""
    os.makedirs("temp", exist_ok=True) 

    video_id = uuid.uuid4().hex
    audio_path = os.path.join("temp", f"{video_id}_audio")  # Remove .mp3 extension

    # Convert time format to seconds for yt-dlp
    def time_to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        else:
            return int(parts[0])

    start_seconds = time_to_seconds(start)
    end_seconds = time_to_seconds(end)
    duration = end_seconds - start_seconds

    # yt-dlp options for audio-only extraction with trimming
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': audio_path,
        'merge_output_format': 'mp3',
        'quiet': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ],
        'postprocessor_args': [
            '-ss', str(start_seconds),
            '-t', str(duration)
        ]
    }

    try:
        # Get video info first to extract title
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'audio')
            # Clean filename - remove invalid characters
            clean_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_title = clean_title[:50]  # Limit length
            
        # Now download with the original options
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # The actual file will have .mp3 extension added by yt-dlp
        final_audio_path = audio_path + ".mp3"
        
        if not os.path.exists(final_audio_path):
            return JSONResponse(content={"error": "Audio extraction failed."}, status_code=500)

        # Update file dates to current time - use both access and modify time
        try:
            current_time = time.time()
            os.utime(final_audio_path, (current_time, current_time))
            # Also try to set creation time on Windows
            if os.name == 'nt':
                import stat
                os.chmod(final_audio_path, stat.S_IWRITE)
        except Exception as date_error:
            print(f"Warning: Could not update file dates: {date_error}")

        return FileResponse(final_audio_path, media_type="audio/mpeg", filename=f"{clean_title}_voice.mp3")

    except Exception as e:
        # Clean up in case of error
        try:
            if os.path.exists(final_audio_path):
                os.remove(final_audio_path)
            # Also try to clean up the base path without extension
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except:
            pass
        
        return JSONResponse(content={"error": "Internal server error", "details": str(e)}, status_code=500)

@app.get("/")
def root():
    """API Documentation"""
    return {
        "message": "Klippd - YouTube Video Clipper API",
        "endpoints": {
            "/clip": "Download video clip (MP4) from YouTube",
            "/voice": "Download audio clip (MP3) from YouTube",
            "/cleanup": "Manual cleanup of temp files"
        },
        "usage": {
            "clip": "/clip?url=YOUTUBE_URL&start=HH:MM:SS&end=HH:MM:SS",
            "voice": "/voice?url=YOUTUBE_URL&start=HH:MM:SS&end=HH:MM:SS"
        },
        "example": {
            "url": "https://www.youtube.com/watch?v=VIDEO_ID",
            "start": "00:01:30",
            "end": "00:02:45"
        }
    }

@app.get("/cleanup")
def manual_cleanup():
    """Manually trigger cleanup of temp files"""
    try:
        cleanup_old_files()
        return {"message": "Cleanup completed successfully"}
    except Exception as e:
        return {"error": f"Cleanup failed: {str(e)}"}
