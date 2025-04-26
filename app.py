from flask import Flask, request, Response, render_template_string
import requests

app = Flask(__name__)

# Simple web page with form to input video URL
HTML = """
<!doctype html>
<title>Advanced Video Proxy</title>
<h2>Paste the Seedr Video Link:</h2>
<form method="get" action="/play">
  <input type="text" name="url" style="width:500px">
  <input type="submit" value="Play">
</form>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/play')
def play_video():
    url = request.args.get('url')
    if not url:
        return "No URL provided.", 400

    range_header = request.headers.get('Range', None)
    if range_header:
        range_type, range_value = range_header.split('=')
        byte_start, byte_end = range_value.split('-')
        byte_start = int(byte_start)
        byte_end = int(byte_end) if byte_end else None
    else:
        byte_start = 0
        byte_end = None

    def generate():
        with requests.get(url, stream=True, headers={'Range': f'bytes={byte_start}-{byte_end}'}) as r:
            if r.status_code == 206:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            else:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk

    # Optionally, add subtitles (e.g., .srt or .vtt)
    subtitle_url = "https://example.com/subtitles.srt"  # Change to actual subtitle URL

    return render_template_string("""
    <html>
        <body>
            <video id="videoPlayer" width="640" height="360" controls>
                <source src="{{ url }}" type="video/mp4">
                <track src="{{ subtitle_url }}" kind="subtitles" srclang="en" label="English">
            </video>
        </body>
    </html>
    """, url=request.url, subtitle_url=subtitle_url)

if __name__ == "__main__":
    app.run()
