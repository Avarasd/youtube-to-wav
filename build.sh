#!/usr/bin/env bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Download and extract static ffmpeg if not present
if [ ! -f "ffmpeg" ]; then
    echo "Downloading static FFmpeg..."
    curl -L -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar -xJvf ffmpeg.tar.xz
    # Move ffmpeg and ffprobe binaries to the root directory
    mv ffmpeg-*-static/ffmpeg .
    mv ffmpeg-*-static/ffprobe .
    # Clean up
    rm -rf ffmpeg-*-static ffmpeg.tar.xz
    echo "FFmpeg installed successfully."
fi
