from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import re
import requests

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/metadata", methods=["POST"])
def metadata():
    url = request.json.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Extract YouTube video ID
    match = re.search(r"(?:v=|be/)([a-zA-Z0-9_-]{11})", url)
    if not match:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    video_id = match.group(1)

    # Try fast Invidious API
    try:
        invidious = f"https://invidious.projectsegfau.lt/api/v1/videos/{video_id}"
        res = requests.get(invidious, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return jsonify({
                "title": data.get("title"),
                "thumbnail": data.get("videoThumbnails", [{}])[-1].get("url")
            })
    except:
        pass

    # Fallback to yt-dlp
    try:
        ydl_opts = {"quiet": True, "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail")
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        format_type = request.form.get("format")

        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "format": "worstaudio" if format_type == "mp3" else "worst[ext=mp4]/worst",
            "merge_output_format": "mp4",
            "keepvideo": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }] if format_type == "mp3" else [],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if format_type == "mp3":
                    filename = os.path.splitext(filename)[0] + ".mp3"
        except Exception as e:
            return f"Download failed: {str(e)}", 500

        return send_file(filename, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
