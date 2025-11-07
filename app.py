from flask import Flask, request, Response, render_template_string, stream_with_context, url_for
import requests
import urllib.parse
import os

app = Flask(__name__)

# ------------------ HTML Templates ------------------

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
        form { background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type=text] {
            width: calc(100% - 100px);
            max-width: 500px;
            padding: 10px;
            margin-right: 10px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        input[type=submit] {
            padding: 10px 15px;
            background-color: #5cb85c;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
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
        body {
            margin: 0;
            background-color: #000;
            color: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        video {
            width: 100%;
            max-height: 90vh;
            display: block;
            background-color: #000;
        }
        .controls {
            padding: 10px;
            background-color: #222;
            width: 100%;
            text-align: center;
            box-sizing: border-box;
        }
        .controls label { margin-right: 10px; }
        .controls select {
            padding: 5px;
            border-radius: 3px;
            background-color: #333;
            color: #fff;
            border: 1px solid #555;
        }
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
        document.addEventListener('DOMContentLoaded', () => {
            const video = document.getElementById('myVideoPlayer');
            const audioTrackSelect = document.getElementById('audioTrackSelect');
            const audioTrackLabel = document.querySelector('label[for=audioTrackSelect]');

            function populateAudioTracks() {
                audioTrackSelect.innerHTML = '';
                if (video.audioTracks && video.audioTracks.length > 0) {
                    for (let i = 0; i < video.audioTracks.length; i++) {
                        const track = video.audioTracks[i];
                        const option = document.createElement('option');
                        option.value = track.id || i;
                        option.textContent = track.label || `Track ${i + 1}` + (track.language ? ` (${track.language})` : '');
                        if (track.enabled) option.selected = true;
                        audioTrackSelect.appendChild(option);
                    }
                    if (video.audioTracks.length <= 1) {
                        audioTrackSelect.style.display = 'none';
                        if (audioTrackLabel) audioTrackLabel.style.display = 'none';
                    } else {
                        audioTrackSelect.style.display = 'inline-block';
                        if (audioTrackLabel) audioTrackLabel.style.display = 'inline-block';
                    }
                } else {
                    audioTrackSelect.style.display = 'none';
                    if (audioTrackLabel) audioTrackLabel.style.display = 'none';
                }
            }

            video.addEventListener('loadedmetadata', populateAudioTracks);
            if (video.audioTracks) {
                video.audioTracks.addEventListener('change', populateAudioTracks);
                video.audioTracks.addEventListener('addtrack', populateAudioTracks);
            }

            audioTrackSelect.addEventListener('change', () => {
                const selectedValue = audioTrackSelect.value;
                for (let i = 0; i < video.audioTracks.length; i++) {
                    const track = video.audioTracks[i];
                    track.enabled = (track.id === selectedValue || i.toString() === selectedValue);
                }
            });

            if (video.readyState >= 1) populateAudioTracks();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_HTML)


@app.route('/player')
def show_player():
    original_video_url = request.args.get('url')
    if not original_video_url:
        return "Error: No URL provided.", 400
    video_url_encoded = urllib.parse.quote(original_video_url)
    return render_template_string(VIDEO_PLAYER_HTML, video_url_encoded=video_url_encoded)


@app.route('/stream')
def stream_video():
    encoded_video_url = request.args.get('url')
    if not encoded_video_url:
        return "Error: Missing video URL parameter for streaming.", 400

    try:
        video_url = urllib.parse.unquote(encoded_video_url)
    except Exception as e:
        return f"Error decoding URL parameter: {e}", 400

    range_header = request.headers.get('Range')
    headers = {'Range': range_header} if range_header else {}

    try:
        upstream_response = requests.get(video_url, headers=headers, stream=True, timeout=(5, 30))
        if upstream_response.status_code not in [200, 206]:
            upstream_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching upstream video: {e}", 502

    response_headers = {
        k: v for k, v in upstream_response.headers.items()
        if k in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range', 'ETag', 'Last-Modified']
    }
    if 'Accept-Ranges' not in response_headers and upstream_response.status_code == 206:
        response_headers['Accept-Ranges'] = 'bytes'

    @stream_with_context
    def generate_stream():
        try:
            for chunk in upstream_response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                yield chunk
        except GeneratorExit:
            print("Client disconnected — stopping stream.")
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            upstream_response.close()
            print("Upstream closed.")

    return Response(generate_stream(), status=upstream_response.status_code, headers=response_headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
