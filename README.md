# YouTube → WAV

A minimal, clean web app that converts any YouTube video to a WAV audio file.

Built with Flask + yt-dlp + FFmpeg on the backend, and a pure HTML/CSS/JS frontend.

## Setup

```bash
pip3 install -r requirements.txt
python3 app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Requirements

- Python 3.9+
- FFmpeg installed on your system (`brew install ffmpeg`)
- `flask` and `yt-dlp` (see `requirements.txt`)
