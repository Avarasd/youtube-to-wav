from flask import Flask, request, send_file, jsonify
import yt_dlp
import os
import re
import shutil
import urllib.request
import tarfile
import uuid

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    IMPERSONATE_CHROME = ImpersonateTarget.from_str("chrome")
except ImportError:
    IMPERSONATE_CHROME = "chrome"

def ensure_node():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    node_dir = os.path.join(base_dir, "node-v20.11.1-linux-x64")
    node_bin = os.path.join(node_dir, "bin")
    
    if not os.path.exists(os.path.join(node_bin, "node")):
        print("Downloading Node.js for yt-dlp to solve YouTube signatures...", flush=True)
        url = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-linux-x64.tar.xz"
        tar_path = os.path.join(base_dir, "node.tar.xz")
        urllib.request.urlretrieve(url, tar_path)
        print("Extracting Node.js...", flush=True)
        with tarfile.open(tar_path, "r:xz") as tar:
            tar.extractall(path=base_dir)
        os.remove(tar_path)
    
    node_exe = os.path.join(node_bin, "node")
    if os.path.exists(node_exe):
        os.chmod(node_exe, 0o755)
        
    os.environ["PATH"] = node_bin + os.pathsep + os.environ.get("PATH", "")
    
    import subprocess
    try:
        res = subprocess.run([node_exe, "-v"], capture_output=True, text=True)
        print(f"NODE CHECK stdout: {res.stdout}, stderr: {res.stderr}", flush=True)
    except Exception as e:
        print(f"NODE CHECK failed: {e}", flush=True)

ensure_node()

# Add current directory to PATH so yt-dlp can find the 'ffmpeg' binary
os.environ["PATH"] += os.pathsep + os.path.dirname(os.path.abspath(__file__))

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
        "outtmpl": out_template,
        "verbose": True,
        "noplaylist": True,
        "impersonate": IMPERSONATE_CHROME,
        "extractor_args": {
            "youtube": ["player_client=android,ios,tv,web,mweb"]
        },
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

    cookie_path = None
    for cp in ["/etc/secrets/cookies.txt", "/etc/secrets/Cookies.txt", "cookies.txt", "Cookies.txt"]:
        if os.path.exists(cp):
            cookie_path = cp
            break

    if cookie_path and os.path.exists(cookie_path):
        print(f"LOADING COOKIES FROM {cookie_path} for /convert", flush=True)
        tmp_cookie_path = "/tmp/yt_cookies.txt"
        try:
            shutil.copy2(cookie_path, tmp_cookie_path)
            ydl_opts["cookiefile"] = tmp_cookie_path
        except Exception as e:
            print(f"Failed to copy cookies: {e}", flush=True)
            ydl_opts["cookiefile"] = cookie_path
    else:
        print(f"NO COOKIES FOUND (tried /etc/secrets/cookies.txt etc)", flush=True)

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
        import traceback
        err_msg = traceback.format_exc()
        print(f"DownloadError: {err_msg}", flush=True)
        return jsonify({"error": f"Download failed: {str(e)[:200]}"}), 422
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"Unexpected error: {err_msg}", flush=True)
        err_str = str(e)
        if not err_str:
            err_str = type(e).__name__
        return jsonify({"error": f"Unexpected error: {err_str[:200]}"}), 500


@app.route("/info")
def info():
    """Return video metadata without downloading."""
    url = request.args.get("url", "").strip()

    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400

    ydl_opts = {
        "quiet": False, 
        "no_warnings": False,
        "verbose": True,
        "skip_download": True,
        "noplaylist": True,
        "impersonate": IMPERSONATE_CHROME,
        "extractor_args": {
            "youtube": ["player_client=android,ios,tv,web,mweb"]
        }
    }

    cookie_path = None
    for cp in ["/etc/secrets/cookies.txt", "/etc/secrets/Cookies.txt", "cookies.txt", "Cookies.txt"]:
        if os.path.exists(cp):
            cookie_path = cp
            break

    if cookie_path and os.path.exists(cookie_path):
        print(f"LOADING COOKIES FROM {cookie_path} for /info", flush=True)
        tmp_cookie_path = "/tmp/yt_cookies.txt"
        try:
            shutil.copy2(cookie_path, tmp_cookie_path)
            ydl_opts["cookiefile"] = tmp_cookie_path
        except Exception:
            ydl_opts["cookiefile"] = cookie_path
    else:
        print(f"NO COOKIES FOUND for /info", flush=True)

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
        import traceback
        err_msg = traceback.format_exc()
        print(f"Info Unexpected error: {err_msg}", flush=True)
        err_str = str(e)
        if not err_str:
            err_str = type(e).__name__
        return jsonify({"error": err_str[:200]}), 422


if __name__ == "__main__":
    app.run(debug=True, port=5000)
