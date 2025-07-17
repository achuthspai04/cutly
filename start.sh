#!/bin/bash
# Install system dependencies if needed
# (Render should handle this via Dockerfile, but backup)

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port $PORT
