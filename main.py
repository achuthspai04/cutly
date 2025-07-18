import os
import base64
import uvicorn
import yt_dlp
import shutil
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Check if FFmpeg is available
if not shutil.which("ffmpeg"):
    print("⚠️ FFmpeg not found! Some features may not work.")
else:
    print("✅ FFmpeg found.")

# Enable CORS for testing/demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Decode and save cookies.txt from base64 env
COOKIES_B64 = os.getenv("COOKIES_B64")
if COOKIES_B64:
    try:
        decoded = base64.b64decode(COOKIES_B64).decode("utf-8")
        with open("cookies.txt", "w", encoding="utf-8") as f:
            f.write(decoded)
        print("✅ cookies.txt created successfully.")
    except Exception as e:
        print(f"❌ Error decoding cookies: {e}")
else:
    print("⚠️ COOKIES_B64 environment variable not set. App will work without cookies but may have limitations.")


@app.get("/")
def root():
    return {
        "message": "Cutly - YouTube Video Clipper API",
        "endpoints": {
            "/clip": "Download video clip (MP4) from YouTube",
            "/voice": "Download audio clip (MP3) from YouTube",
            "/cleanup": "Manual cleanup of temp files",
            "/status": "Check API health and capabilities"
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


def format_timestamp(ts: str) -> int:
    """Converts HH:MM:SS to seconds."""
    h, m, s = map(int, ts.split(":"))
    return h * 3600 + m * 60 + s


def download_clip(url: str, start: str, end: str, audio_only=False):
    start_sec = format_timestamp(start)
    end_sec = format_timestamp(end)
    duration = end_sec - start_sec

    ext = "mp3" if audio_only else "mp4"
    out_name = f"output.{ext}"

    # Base options that work without cookies
    ydl_opts = {
        "outtmpl": out_name,
        "format": "bestaudio/best" if audio_only else "bestvideo+bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "ignoreerrors": True,  # Continue on non-fatal errors
        # Use external_downloader with ffmpeg for better clipping
        "external_downloader": "ffmpeg",
        "external_downloader_args": {
            "ffmpeg_i": ["-ss", str(start_sec), "-t", str(duration)]
        }
    }
    
    # Only add cookies if file exists and is valid
    cookies_file = "cookies.txt"
    if os.path.exists(cookies_file) and os.path.getsize(cookies_file) > 0:
        ydl_opts["cookiefile"] = cookies_file
        print("📄 Using cookies file for authentication")
    else:
        print("⚠️ No valid cookies found, proceeding without authentication")
    
    # Add postprocessor only for audio extraction
    if audio_only:
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Check if file was created successfully
        if not os.path.exists(out_name):
            raise RuntimeError("Download completed but output file not found")
            
        return out_name
    except Exception as e:
        # Try again without cookies if cookies were the issue
        if "cookies" in str(e).lower() and "cookiefile" in ydl_opts:
            print("🔄 Retrying without cookies due to authentication error...")
            ydl_opts.pop("cookiefile", None)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                if os.path.exists(out_name):
                    return out_name
            except Exception as retry_error:
                raise RuntimeError(f"Download failed even without cookies: {retry_error}")
        
        raise RuntimeError(str(e))


@app.get("/clip")
def clip(url: str = Query(...), start: str = Query(...), end: str = Query(...)):
    try:
        path = download_clip(url, start, end, audio_only=False)
        return FileResponse(path, media_type="video/mp4", filename="clip.mp4")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Internal server error", "details": str(e)})


@app.get("/voice")
def voice(url: str = Query(...), start: str = Query(...), end: str = Query(...)):
    try:
        path = download_clip(url, start, end, audio_only=True)
        return FileResponse(path, media_type="audio/mpeg", filename="clip.mp3")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Internal server error", "details": str(e)})


@app.get("/cleanup")
def cleanup():
    removed = []
    for f in ["output.mp4", "output.mp3"]:
        if os.path.exists(f):
            os.remove(f)
            removed.append(f)
    return {"status": "done", "removed": removed}


@app.get("/status")
def status():
    """Check API status and capabilities"""
    status_info = {
        "status": "online",
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "cookies_available": os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0,
        "yt_dlp_version": yt_dlp.__version__
    }
    
    if status_info["cookies_available"]:
        status_info["cookies_status"] = "valid cookies loaded"
    else:
        status_info["cookies_status"] = "no cookies (may limit some videos)"
    
    return status_info


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Use Render's PORT env var
    uvicorn.run(app, host="0.0.0.0", port=port)
