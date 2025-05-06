from flask import Flask, request, Response, render_template_string, stream_with_context, url_for
import requests
import urllib.parse # Needed for URL encoding

app = Flask(__name__)

# --- HTML Templates ---

# Form to enter the URL (unchanged)
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
        input[type=text] { width: calc(100% - 100px); max-width: 500px; padding: 10px; margin-right: 10px; border: 1px solid #ccc; border-radius: 3px; }
        input[type=submit] { padding: 10px 15px; background-color: #5cb85c; color: white; border: none; border-radius: 3px; cursor: pointer; }
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

# HTML page with the video player AND audio track selector
VIDEO_PLAYER_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Playing Video</title>
    <style>
        body { margin: 0; background-color: #000; color: #fff; display: flex; flex-direction: column; align-items: center;}
        video { width: 100%; max-height: 90vh; display: block; }
        .controls { padding: 10px; background-color: #222; width: 100%; text-align: center; box-sizing: border-box; }
        .controls label { margin-right: 10px; }
        .controls select { padding: 5px; border-radius: 3px; background-color: #333; color: #fff; border: 1px solid #555;}
    </style>
</head>
<body>
    <video controls autoplay preload="auto" id="myVideoPlayer" src="{{ url_for('stream_video', url=video_url_encoded) }}">
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

            // Function to populate audio track options
            function populateAudioTracks() {
                // Clear previous options
                audioTrackSelect.innerHTML = '';

                if (video.audioTracks && video.audioTracks.length > 0) {
                    console.log(`Found ${video.audioTracks.length} audio tracks.`);
                    for (let i = 0; i < video.audioTracks.length; i++) {
                        const track = video.audioTracks[i];
                        const option = document.createElement('option');
                        option.value = track.id || i; // Use id if available, otherwise index
                        option.textContent = track.label || `Track ${i + 1}` + (track.language ? ` (${track.language})` : '');
                        if (track.enabled) {
                            option.selected = true;
                        }
                        audioTrackSelect.appendChild(option);
                        console.log(`Track ${i}: Label='${track.label}', Language='${track.language}', Enabled='${track.enabled}', ID='${track.id}'`);
                    }
                    if(video.audioTracks.length <= 1){
                        audioTrackSelect.style.display = 'none';
                        if (audioTrackLabel) audioTrackLabel.style.display = 'none';
                    } else {
                        audioTrackSelect.style.display = 'inline-block';
                        if (audioTrackLabel) audioTrackLabel.style.display = 'inline-block';
                    }
                } else {
                    console.warn("audioTracks API not supported or no tracks found initially.");
                    audioTrackSelect.style.display = 'none';
                    if (audioTrackLabel) audioTrackLabel.style.display = 'none';
                }
            }

            video.addEventListener('loadedmetadata', () => {
                console.log("Video metadata loaded.");
                populateAudioTracks();
            });

            if (video.audioTracks) {
                video.audioTracks.addEventListener('change', () => {
                    console.log("Audio tracks changed.");
                    populateAudioTracks();
                });
                 video.audioTracks.addEventListener('addtrack', () => { // Also listen for addtrack
                    console.log("Audio track added.");
                    populateAudioTracks();
                });
            }


            audioTrackSelect.addEventListener('change', () => {
                const selectedValue = audioTrackSelect.value;
                console.log(`Attempting to switch to audio track value: ${selectedValue}`);
                let trackSwitched = false;
                for (let i = 0; i < video.audioTracks.length; i++) {
                    const track = video.audioTracks[i];
                    // Match by id (if string) or index (if number from parsed value)
                    if (track.id === selectedValue || i.toString() === selectedValue) {
                        track.enabled = true;
                        console.log(`Enabled track: ${track.label || 'Track ' + (i+1)} (ID: ${track.id}, Index: ${i})`);
                        trackSwitched = true;
                    } else {
                        track.enabled = false;
                    }
                }
                if (!trackSwitched) {
                    console.warn("Could not find matching track to enable for value: ", selectedValue);
                }
            });

            if (video.readyState >= 1) { // HAVE_METADATA
                 console.log("Video readyState >= HAVE_METADATA on DOMContentLoaded. Populating tracks.");
                 populateAudioTracks();
            }
        });
    </script>
</body>
</html>
"""


# --- Flask Routes ---

@app.route('/')
def home():
    """Serves the simple HTML form."""
    return render_template_string(HOME_HTML)

@app.route('/player') # Changed route name for clarity
def show_player():
    """Renders the HTML page with the video player."""
    original_video_url = request.args.get('url')
    if not original_video_url:
        return "Error: No URL provided.", 400

    video_url_encoded = urllib.parse.quote(original_video_url)
    return render_template_string(VIDEO_PLAYER_HTML, video_url_encoded=video_url_encoded)

@app.route('/stream') # New route specifically for streaming video data
def stream_video():
    """Proxies the video stream, handling Range requests for seeking."""
    encoded_video_url = request.args.get('url')
    if not encoded_video_url:
        return "Error: Missing video URL parameter for streaming.", 400

    try:
        video_url = urllib.parse.unquote(encoded_video_url)
    except Exception as e:
        return f"Error decoding URL parameter: {e}", 400

    range_header = request.headers.get('Range', None)
    request_headers = {}
    if range_header:
        request_headers['Range'] = range_header
        print(f"Client requested Range: {range_header}")

    try:
        upstream_response = requests.get(
            video_url,
            headers=request_headers,
            stream=True,
            timeout=30
        )
        if not upstream_response.ok and upstream_response.status_code not in [200, 206]:
            upstream_response.raise_for_status()

    except requests.exceptions.Timeout:
        error_message = "Error: Upstream server timed out."
        print(error_message)
        return error_message, 504
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching upstream URL '{video_url}': {e}"
        print(error_message)
        return error_message, 502

    response_headers = {}
    for header_key in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range', 'ETag', 'Last-Modified']:
        if header_key in upstream_response.headers:
            response_headers[header_key] = upstream_response.headers[header_key]

    if 'Accept-Ranges' not in response_headers and 'bytes' in upstream_response.headers.get('Accept-Ranges', ''):
        response_headers['Accept-Ranges'] = 'bytes'
    elif upstream_response.status_code == 206 and 'Accept-Ranges' not in response_headers:
        response_headers['Accept-Ranges'] = 'bytes'

    @stream_with_context
    def generate_stream():
        try:
            for chunk in upstream_response.iter_content(chunk_size=16384):
                if chunk:
                    yield chunk
            print("Stream finished.")
        except requests.exceptions.ChunkedEncodingError:
            print("Warning: Upstream connection closed unexpectedly during streaming.")
        except Exception as e:
            print(f"Error during streaming generation: {e}")
        finally:
            upstream_response.close()
            print("Upstream connection closed.")

    status_code = upstream_response.status_code
    print(f"Streaming to client - Status: {status_code}, Headers: {list(response_headers.keys())}")
    return Response(generate_stream(), status=status_code, headers=response_headers)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)
