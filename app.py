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

# HTML page with the video player
VIDEO_PLAYER_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Playing Video</title>
    <style>
        body { margin: 0; background-color: #000; }
        video { width: 100%; max-height: 100vh; display: block; }
    </style>
</head>
<body>
    <video controls autoplay preload="auto" src="{{ url_for('stream_video', url=video_url_encoded) }}">
        Your browser does not support the video tag.
    </video>
</body>
</html>
"""

# --- Flask Routes ---

@app.route('/')
def home():
    """Serves the simple HTML form."""
    # Use url_for('show_player') to generate the form action URL
    return render_template_string(HOME_HTML)

@app.route('/player') # Changed route name for clarity
def show_player():
    """Renders the HTML page with the video player."""
    original_video_url = request.args.get('url')
    if not original_video_url:
        return "Error: No URL provided.", 400

    # URL-encode the original video URL before passing it as a parameter
    # to the /stream endpoint's URL. This prevents issues with special characters.
    video_url_encoded = urllib.parse.quote(original_video_url)

    # Render the player template, passing the encoded URL
    return render_template_string(VIDEO_PLAYER_HTML, video_url_encoded=video_url_encoded)

@app.route('/stream') # New route specifically for streaming video data
def stream_video():
    """Proxies the video stream, handling Range requests for seeking."""
    encoded_video_url = request.args.get('url')
    if not encoded_video_url:
        return "Error: Missing video URL parameter for streaming.", 400

    # Decode the URL back to its original form
    try:
        video_url = urllib.parse.unquote(encoded_video_url)
    except Exception as e:
         return f"Error decoding URL parameter: {e}", 400

    # Get the Range header from the client request (browser's video player)
    range_header = request.headers.get('Range', None)
    request_headers = {}
    if range_header:
        # Pass the Range header to the upstream server
        request_headers['Range'] = range_header
        print(f"Client requested Range: {range_header}") # For debugging

    try:
        # Make the streaming request to the actual video URL
        upstream_response = requests.get(
            video_url,
            headers=request_headers,
            stream=True,
            timeout=30 # Increased timeout slightly
        )
        # Only raise status for critical errors, allow 200/206 through
        if not upstream_response.ok and upstream_response.status_code not in [200, 206]:
             upstream_response.raise_for_status()

    except requests.exceptions.Timeout:
        error_message = "Error: Upstream server timed out."
        print(error_message)
        return error_message, 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching upstream URL '{video_url}': {e}"
        print(error_message)
        return error_message, 502 # Bad Gateway

    # --- Prepare the response back to the client ---
    response_headers = {}
    # Copy essential headers from the upstream response
    for header_key in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range', 'ETag', 'Last-Modified']:
        if header_key in upstream_response.headers:
            response_headers[header_key] = upstream_response.headers[header_key]

    # Ensure Accept-Ranges is correctly signaled if supported
    if 'Accept-Ranges' not in response_headers and 'bytes' in upstream_response.headers.get('Accept-Ranges', ''):
        response_headers['Accept-Ranges'] = 'bytes'
    elif upstream_response.status_code == 206 and 'Accept-Ranges' not in response_headers:
         response_headers['Accept-Ranges'] = 'bytes' # Assume bytes if partial content is served

    # Generator function to yield chunks of the video data
    @stream_with_context
    def generate_stream():
        try:
            for chunk in upstream_response.iter_content(chunk_size=16384): # Increased chunk size
                if chunk:
                    yield chunk
            print("Stream finished.") # Debugging
        except requests.exceptions.ChunkedEncodingError:
             print("Warning: Upstream connection closed unexpectedly during streaming.")
        except Exception as e:
             print(f"Error during streaming generation: {e}")
        finally:
            upstream_response.close()
            print("Upstream connection closed.") # Debugging

    # Determine the correct HTTP status code (usually 200 or 206)
    status_code = upstream_response.status_code

    print(f"Streaming to client - Status: {status_code}, Headers: {list(response_headers.keys())}") # Debugging

    # Create and return the Flask Response object for the video data
    return Response(generate_stream(), status=status_code, headers=response_headers)

if __name__ == "__main__":
    # Using threaded=True allows handling multiple requests concurrently
    # Use 0.0.0.0 to make it accessible on your network
    app.run() # Debug=True provides more error info during development
