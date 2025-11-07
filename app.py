from flask import Flask, request, Response, render_template_string, stream_with_context, url_for
import requests, urllib.parse

app = Flask(__name__)

# --- HTML Templates ---

HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Stream Proxy</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f4; }
        h2 { color: #333; }
        form { background-color: #fff; padding: 20px; border-radius: 5px;
               box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type=text] { width: calc(100% - 100px); max-width: 500px; padding: 10px;
                           margin-right: 10px; border: 1px solid #ccc; border-radius: 3px; }
        input[type=submit] { padding: 10px 15px; background-color: #5cb85c;
                             color: white; border: none; border-radius: 3px; cursor: pointer; }
        input[type=submit]:hover { background-color: #4cae4c; }
    </style>
</head>
<body>
    <h2>Paste the Seedr Video Link:</h2>
    <form method="get" action="{{ url_for('show_player') }}">
        <input type="text" name="url" placeholder="https://www.seedr.cc/..." required>
        <input type="submit" value="Play">
    </form>
</body>
</html>
"""

VIDEO_PLAYER_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Playing Video</title>
    <style>
        body { margin: 0; background-color: #000; color: #fff;
               display: flex; flex-direction: column; align-items: center; }
        video { width: 100%; max-height: 90vh; display: block; }
        .controls { padding: 10px; background-color: #222; width: 100%;
                    text-align: center; box-sizing: border-box; }
        .controls label { margin-right: 10px; }
        .controls select { padding: 5px; border-radius: 3px; background-color: #333;
                           color: #fff; border: 1px solid #555; }
    </style>
</head>
<body>
    <video controls autoplay preload="auto" id="myVideoPlayer"
           src="{{ url_for('stream_video', url=video_url_encoded) }}">
        Your browser does not support the video tag.
    </video>

    <div class="controls">
        <label for="audioTrackSelect">Audio Track:</label>
        <select id="audioTrackSelect" title="Select Audio Track"></select>
    </div>

    <script>
    let controller = null;
    const video = document.getElementById('myVideoPlayer');

    // Abort active stream when seeking
    video.addEventListener('seeking', () => {
        if (controller) controller.abort();
        console.log("Seek detected — aborting old stream.");
    });

    // Abort when playing new range
    video.addEventListener('play', () => {
        if (controller) controller.abort();
    });

    // Audio track population (optional)
    const audioTrackSelect = document.getElementById('audioTrackSelect');
    const audioTrackLabel = document.querySelector('label[for=audioTrackSelect]');

    function populateAudioTracks() {
        audioTrackSelect.innerHTML = '';
        if (video.audioTracks && video.audioTracks.length > 0) {
            for (let i = 0; i < video.audioTracks.length; i++) {
                const track = video.audioTracks[i];
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = track.label || `Track ${i + 1}`;
                if (track.enabled) opt.selected = true;
                audioTrackSelect.appendChild(opt);
            }
            audioTrackSelect.style.display = video.audioTracks.length > 1 ? 'inline-block' : 'none';
            if (audioTrackLabel) audioTrackLabel.style.display = video.audioTracks.length > 1 ? 'inline-block' : 'none';
        } else {
            audioTrackSelect.style.display = 'none';
            if (audioTrackLabel) audioTrackLabel.style.display = 'none';
        }
    }

    video.addEventListener('loadedmetadata', populateAudioTracks);
    </script>
</body>
</html>
"""

# --- Flask Routes ---

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/player')
def show_player():
    url = request.args.get('url')
    if not url:
        return "Error: No URL provided.", 400
    encoded = urllib.parse.quote(url)
    return render_template_string(VIDEO_PLAYER_HTML, video_url_encoded=encoded)

@app.route('/stream')
def stream_video():
    encoded = request.args.get('url')
    if not encoded:
        return "Error: Missing video URL.", 400

    try:
        video_url = urllib.parse.unquote(encoded)
    except Exception as e:
        return f"Error decoding URL: {e}", 400

    range_header = request.headers.get('Range')
    headers = {
        'Connection': 'close',
        'User-Agent': 'Mozilla/5.0 (compatible; StreamProxy/1.0)',
    }
    if range_header:
        headers['Range'] = range_header

    try:
        upstream = requests.get(
            video_url,
            headers=headers,
            stream=True,
            timeout=(3, 8)
        )
    except requests.exceptions.Timeout:
        return "Upstream timeout", 504
    except requests.exceptions.RequestException as e:
        return f"Error fetching video: {e}", 502

    response_headers = {}
    for h in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range']:
        if h in upstream.headers:
            response_headers[h] = upstream.headers[h]
    if 'Accept-Ranges' not in response_headers:
        response_headers['Accept-Ranges'] = 'bytes'

    @stream_with_context
    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=32768):
                if chunk:
                    yield chunk
        except GeneratorExit:
            print("Client disconnected (seek or stop).")
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            upstream.close()
            print("Upstream connection closed.")

    return Response(generate(), status=upstream.status_code, headers=response_headers)

if __name__ == "__main__":
    # For Koyeb or Render deployment
    app.run(host="0.0.0.0", port=5000, threaded=True)
