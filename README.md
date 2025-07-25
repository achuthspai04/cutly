# Cutly - YouTube Video Clipper API

A FastAPI-based service for extracting video and audio clips from YouTube videos.

## Features

- 🎥 **Video Clipping**: Extract MP4 video clips with original quality
- 🎵 **Audio Extraction**: Extract MP3 audio clips at 192kbps
- 🏷️ **Smart Naming**: Uses actual YouTube video titles as filenames
- 📅 **Current Dates**: Sets file dates to download time
- 🧹 **Auto Cleanup**: Automatically removes old files every 30 minutes
- 🌐 **CORS Enabled**: Ready for web frontend integration

## API Endpoints

### `GET /`
Returns API documentation and usage examples.

### `GET /clip`
Download a video clip from YouTube.

**Parameters:**
- `url`: YouTube video URL
- `start`: Start time in HH:MM:SS format
- `end`: End time in HH:MM:SS format

**Example:**
```
/clip?url=https://www.youtube.com/watch?v=VIDEO_ID&start=00:01:30&end=00:02:45
```

### `GET /voice`
Download an audio clip from YouTube.

**Parameters:**
- `url`: YouTube video URL  
- `start`: Start time in HH:MM:SS format
- `end`: End time in HH:MM:SS format

**Example:**
```
/voice?url=https://www.youtube.com/watch?v=VIDEO_ID&start=00:01:30&end=00:02:45
```

### `GET /cleanup`
Manually trigger cleanup of temporary files.

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn main:app --reload --port 8080
```

3. Access the API at `http://localhost:8080`

## Deployment

might need too workaround ways so that yt doesnt flag this as a bot.

## File Management

- Temporary files are stored in the `temp/` directory
- Files older than 1 hour are automatically cleaned up every 30 minutes
- Manual cleanup available via `/cleanup` endpoint
