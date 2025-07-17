from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import subprocess
import uuid
import base64

app = FastAPI()

# Allow all CORS (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create clips directory if not exists
os.makedirs("clips", exist_ok=True)

# Decode and write cookies from base64 env var
def write_cookies_from_env():
    b64 = os.getenv("COOKIES_B64")
    if b64:
        with open("cookies.txt", "wb") as f:
            f.write(base64.b64decode(b64))

def get_seconds(time_str):
    minutes, seconds = map(int, time_str.split(":"))
    return minutes * 60 + seconds

@app.get("/clip")
def download_clip(
    url: str = Query(...),
    start: str = Query(...),
    end: str = Query(...)
):
    try:
        write_cookies_from_env()

        start_seconds = get_seconds(start)
        end_seconds = get_seconds(end)
        duration = end_seconds - start_seconds
        uid = str(uuid.uuid4())[:8]
        clipped_path = f"clips/{uid}.mp4"

        # Get video info
        with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': 'cookies.txt'}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'clip')

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': clipped_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'cookiefile': 'cookies.txt',
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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return FileResponse(clipped_path, media_type="video/mp4", filename=f"{title}.mp4")

    except Exception as e:
        return {"error": "Internal server error", "details": str(e)}

@app.get("/voice")
def download_voice(url: str = Query(...)):
    try:
        write_cookies_from_env()

        uid = str(uuid.uuid4())[:8]
        audio_path = f"clips/{uid}.mp3"

        # Get video info
        with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': 'cookies.txt'}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'voice')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_path,
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{title}.mp3")

    except Exception as e:
        return {"error": "Internal server error", "details": str(e)}
