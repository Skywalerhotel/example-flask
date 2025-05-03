from flask import Flask, request, Response, render_template_string, stream_with_context, url_for, redirect, flash
import requests
import urllib.parse # Needed for URL encoding
import os # For potentially using environment variables later

app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for flashing messages

# --- Seedr Configuration ---
# WARNING: Hardcoding credentials is insecure! Use environment variables ideally.
SEEDR_EMAIL = "pasamsung220@gmail.com"
SEEDR_PASSWORD = "Aa20031220#"
SEEDR_API_BASE = "https://www.seedr.cc/rest"

# --- HTML Templates ---

# Page to browse Seedr files
BROWSE_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Seedr Files</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f4; }
        h2 { color: #333; }
        .container { background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        ul { list-style-type: none; padding: 0; }
        li { margin-bottom: 10px; padding: 8px; border-bottom: 1px solid #eee; }
        li a { text-decoration: none; color: #0d6efd; }
        li a:hover { text-decoration: underline; }
        .file-icon { margin-right: 8px; }
        .error { color: red; font-weight: bold; margin-bottom: 1em; }
        .warning { color: orange; font-weight: bold; margin-bottom: 1em; border: 1px solid orange; padding: 10px; border-radius: 4px; background-color: #fff3cd;}

    </style>
</head>
<body>
    <div class="container">
        <h2>Seedr Video Files</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="warning">
            <strong>Security Warning:</strong> Seedr credentials are currently hardcoded in the server script. This is insecure. Do not expose this server publicly in this state.
        </div>

        {% if video_files %}
            <ul>
                {% for file in video_files %}
                <li>
                    <span class="file-icon">🎬</span> <a href="{{ url_for('show_player', file_id=file.id) }}">{{ file.name }}</a>
                    </li>
                {% endfor %}
            </ul>
        {% else %}
            <p>No video files found in the root Seedr folder, or there was an error fetching them.</p>
        {% endif %}
        </div>
</body>
</html>
"""

# HTML page with the video player (Modified to accept file_id)
VIDEO_PLAYER_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Playing Video: {{ file_name }}</title>
    <style>
        body { margin: 0; background-color: #000; }
        video { width: 100%; max-height: 100vh; display: block; }
    </style>
</head>
<body>
    <video controls autoplay preload="auto" src="{{ url_for('stream_video', file_id=file_id) }}">
        Your browser does not support the video tag.
    </video>
</body>
</html>
"""

# --- Helper Functions ---

def get_seedr_folder_contents(folder_id=None):
    """Fetches folder contents from Seedr API."""
    if folder_id:
        url = f"{SEEDR_API_BASE}/folder/{folder_id}"
    else: # Root folder
        url = f"{SEEDR_API_BASE}/folder"

    try:
        response = requests.get(
            url,
            auth=(SEEDR_EMAIL, SEEDR_PASSWORD),
            timeout=20
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Error: Timeout connecting to Seedr API at {url}")
        flash(f"Error: Timeout connecting to Seedr API.", "error")
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP Error fetching Seedr data: {e.response.status_code} - {e.response.text}")
        flash(f"Error: Failed to fetch data from Seedr (HTTP {e.response.status_code}). Check credentials or Seedr status.", "error")
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not connect to Seedr API: {e}")
        flash(f"Error: Could not connect to Seedr API: {e}", "error")
    except ValueError: # Includes JSONDecodeError
        print("Error: Could not decode JSON response from Seedr API.")
        flash("Error: Invalid response received from Seedr API.", "error")
    return None

# --- Flask Routes ---

@app.route('/')
def home():
    """Shows the list of video files from the Seedr root folder."""
    print("Fetching Seedr root folder contents...")
    data = get_seedr_folder_contents()
    video_files = []

    if data and 'files' in data:
        for item in data['files']:
            # Check if the file is likely a video
            # Seedr has 'is_video' flag, or check mime type
            is_video = item.get('is_video', False)
            mime_type = item.get('mime_type', '').lower()
            if is_video or mime_type.startswith('video/'):
                video_files.append(item)
        print(f"Found {len(video_files)} video files.")
    elif data is None:
        # Error already flashed by get_seedr_folder_contents
        pass
    else:
        print("No 'files' key found in Seedr response or data is empty.")
        flash("Received unexpected data structure from Seedr.", "error")

    # Note: We are passing the raw file dictionary now
    return render_template_string(BROWSE_HTML, video_files=video_files)

@app.route('/player')
def show_player():
    """Renders the HTML page with the video player, using file_id."""
    file_id = request.args.get('file_id')
    file_name = request.args.get('name', 'Video') # Get name if passed, otherwise default

    if not file_id:
        flash("Error: No file ID provided.", "error")
        return redirect(url_for('home'))

    # We don't need the direct URL here anymore, the player will request
    # it from the /stream endpoint using the file_id.
    # We could fetch the name here if needed, but it's simpler if passed or defaulted.

    print(f"Showing player for file_id: {file_id}")
    # Pass file_id directly to the template
    return render_template_string(VIDEO_PLAYER_HTML, file_id=file_id, file_name=file_name)

@app.route('/stream') # Stream endpoint now uses file_id
def stream_video():
    """Proxies the video stream using file_id, handling Range requests."""
    file_id = request.args.get('file_id')
    if not file_id:
        return "Error: Missing file_id parameter for streaming.", 400

    # Construct the direct download URL for the file
    # Based on Seedr API docs, this URL should initiate the download/stream
    video_url = f"{SEEDR_API_BASE}/file/{file_id}"
    print(f"Attempting to stream from URL: {video_url} (constructed from file_id: {file_id})")

    # Get the Range header from the client request (browser's video player)
    range_header = request.headers.get('Range', None)
    request_headers = {}
    if range_header:
        request_headers['Range'] = range_header
        print(f"Client requested Range: {range_header}")

    try:
        # Make the streaming request to the actual video URL using Seedr auth
        upstream_response = requests.get(
            video_url,
            auth=(SEEDR_EMAIL, SEEDR_PASSWORD), # Add authentication here!
            headers=request_headers,
            stream=True,
            timeout=30,
            allow_redirects=True # IMPORTANT: Allow redirects, Seedr might redirect to the actual content URL
        )

        # After potential redirects, check the final URL (optional debugging)
        print(f"Streaming from final upstream URL: {upstream_response.url}")

        # Check if the response is successful (200 OK or 206 Partial Content)
        if not upstream_response.ok:
            print(f"Upstream error: Status {upstream_response.status_code}, Content: {upstream_response.text[:200]}...") # Log part of the error
            upstream_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)


    except requests.exceptions.Timeout:
        error_message = f"Error: Upstream server ({video_url}) timed out."
        print(error_message)
        return error_message, 504 # Gateway Timeout
    except requests.exceptions.HTTPError as e:
         error_message = f"Error fetching upstream URL '{video_url}' (HTTP {e.response.status_code}): {e.response.text[:200]}..."
         print(error_message)
         # Return appropriate status code from upstream if available (e.g. 404 Not Found)
         return error_message, e.response.status_code if e.response is not None else 502 # Bad Gateway
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching upstream URL '{video_url}': {e}"
        print(error_message)
        return error_message, 502 # Bad Gateway

    # --- Prepare the response back to the client ---
    response_headers = {}
    # Copy essential headers from the upstream response
    # Case-insensitive header access:
    upstream_headers_lower = {k.lower(): v for k, v in upstream_response.headers.items()}

    for header_key_lower in ['content-type', 'content-length', 'accept-ranges', 'content-range', 'etag', 'last-modified']:
         if header_key_lower in upstream_headers_lower:
              # Find original case key for Flask response (optional but good practice)
              original_key = next((k for k in upstream_response.headers if k.lower() == header_key_lower), header_key_lower)
              response_headers[original_key] = upstream_headers_lower[header_key_lower]


    # Ensure Accept-Ranges is correctly signaled if supported
    accept_ranges = upstream_headers_lower.get('accept-ranges', '')
    if 'accept-ranges' not in response_headers and 'bytes' in accept_ranges:
        response_headers['Accept-Ranges'] = 'bytes'
    # If upstream sends 206 Partial Content, assume byte range support
    elif upstream_response.status_code == 206 and 'accept-ranges' not in response_headers:
         response_headers['Accept-Ranges'] = 'bytes'


    # Generator function to yield chunks of the video data
    @stream_with_context
    def generate_stream():
        try:
            # Use a slightly larger chunk size for potentially better network performance
            for chunk in upstream_response.iter_content(chunk_size=65536): # 64 KB chunks
                if chunk: # filter out keep-alive new chunks
                    yield chunk
            print(f"Stream finished for file_id: {file_id}")
        except requests.exceptions.ChunkedEncodingError:
             print(f"Warning: Upstream connection closed unexpectedly during streaming for file_id: {file_id}.")
        except Exception as e:
             # Log errors occurring during the streaming process itself
             print(f"Error during streaming generation for file_id {file_id}: {e}")
        finally:
            upstream_response.close()
            print(f"Upstream connection closed for file_id: {file_id}")

    # Determine the correct HTTP status code (usually 200 or 206)
    status_code = upstream_response.status_code

    print(f"Streaming to client for file_id {file_id} - Status: {status_code}, Headers: {list(response_headers.keys())}")

    # Create and return the Flask Response object for the video data
    return Response(generate_stream(), status=status_code, headers=response_headers)

if __name__ == "__main__":
    print("--- Starting Flask Seedr Proxy ---")
    print("WARNING: Using hardcoded Seedr credentials. This is insecure.")
    print("Access the server at http://<your-ip>:5000")
    print("------------------------------------")
    # Using threaded=True allows handling multiple requests concurrently
    # Use 0.0.0.0 to make it accessible on your network (use with caution)
    # Debug=False for production/sharing, True for development
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
