#!/usr/bin/env bash
# Exit on error
set -e

# Install Python dependencies and FORCE upgrade yt-dlp to bypass Render cache
pip install -r requirements.txt
pip install --upgrade yt-dlp

# Download and extract static ffmpeg if not present
if [ ! -f "ffmpeg" ]; then
    echo "Downloading ffmpeg..."
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar -xf ffmpeg-release-amd64-static.tar.xz
    mv ffmpeg-*-static/ffmpeg .
    mv ffmpeg-*-static/ffprobe .
    rm -rf ffmpeg-*-static* ffmpeg-release-amd64-static.tar.xz
    echo "FFmpeg installed successfully."
fi

# Download Node.js to solve YouTube's JS challenges (signatures)
if [ ! -f "node" ]; then
    echo "Downloading Node.js..."
    curl -sL https://nodejs.org/dist/v20.11.1/node-v20.11.1-linux-x64.tar.xz | tar -xJ
    mv node-v20.11.1-linux-x64/bin/node .
    rm -rf node-v20.11.1-linux-x64
fi
