from flask import Flask, request, send_file, jsonify
import yt_dlp
import os
import uuid
import re
import shutil

app = Flask(__name__, static_folder="static", template_folder="templates")

YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w\-]+"
)


def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_REGEX.match(url))


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/convert")
def convert():
    url = request.args.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL provided."}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400

    # Unique filename per request to avoid collisions
    job_id = uuid.uuid4().hex
    out_template = f"/tmp/{job_id}.%(ext)s"
    out_path = f"/tmp/{job_id}.wav"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    cookie_path = "/etc/secrets/cookies.txt"
    if not os.path.exists(cookie_path):
        cookie_path = "cookies.txt"

    if os.path.exists(cookie_path):
        tmp_cookie_path = "/tmp/yt_cookies.txt"
        try:
            shutil.copy2(cookie_path, tmp_cookie_path)
            ydl_opts["cookiefile"] = tmp_cookie_path
        except Exception:
            ydl_opts["cookiefile"] = cookie_path

    if os.path.exists("./ffmpeg"):
        ydl_opts["ffmpeg_location"] = "./ffmpeg"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio")

        if not os.path.exists(out_path):
            return jsonify({"error": "Conversion failed: output file not found."}), 500

        safe_title = re.sub(r'[^\w\s\-]', '', title).strip().replace(' ', '_')
        download_name = f"{safe_title[:80]}.wav"

        response = send_file(
            out_path,
            mimetype="audio/wav",
            as_attachment=True,
            download_name=download_name,
        )

        # Clean up after sending
        @response.call_on_close
        def cleanup():
            try:
                os.remove(out_path)
            except OSError:
                pass

        return response

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Download failed: {str(e)[:200]}"}), 422
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)[:200]}"}), 500


@app.route("/info")
def info():
    """Return video metadata without downloading."""
    url = request.args.get("url", "").strip()

    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400

    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}

    cookie_path = "/etc/secrets/cookies.txt"
    if not os.path.exists(cookie_path):
        cookie_path = "cookies.txt"

    if os.path.exists(cookie_path):
        tmp_cookie_path = "/tmp/yt_cookies.txt"
        try:
            shutil.copy2(cookie_path, tmp_cookie_path)
            ydl_opts["cookiefile"] = tmp_cookie_path
        except Exception:
            ydl_opts["cookiefile"] = cookie_path

    if os.path.exists("./ffmpeg"):
        ydl_opts["ffmpeg_location"] = "./ffmpeg"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify(
                {
                    "title": info.get("title", "Unknown"),
                    "channel": info.get("uploader", "Unknown"),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                }
            )
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 422


if __name__ == "__main__":
    app.run(debug=True, port=5000)
