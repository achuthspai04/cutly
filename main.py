import os
import base64
import uvicorn
import yt_dlp
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
    print("⚠️ COOKIES_B64 environment variable not set.")


@app.get("/")
def root():
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

    ydl_opts = {
        "outtmpl": out_name,
        "download_ranges": {
            "ranges": [(start_sec, end_sec)]
        },
        "format": "bestaudio/best" if audio_only else "bestvideo+bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio" if audio_only else "FFmpegVideoConvertor",
            "preferredcodec": "mp3" if audio_only else "mp4",
        }],
        "quiet": True,
        "noplaylist": True,
        "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return out_name
    except Exception as e:
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
