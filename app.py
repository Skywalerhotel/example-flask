from flask import Flask, request, Response, render_template_string, stream_with_context
import requests

app = Flask(__name__)

# Simple web page (unchanged)
HTML = """
<!doctype html>
<title>Stream Proxy</title>
<style>
    body { font-family: sans-serif; margin: 2em; }
    input[type=text] { width: 80%; max-width: 500px; padding: 5px; }
    input[type=submit] { padding: 5px 10px; }
</style>
<h2>Paste the Seedr Video Link:</h2>
<form method="get" action="/play">
  <input type="text" name="url" placeholder="https://www.seedr.cc/..." required>
  <input type="submit" value="Play">
</form>
"""

@app.route('/')
def home():
    """Serves the simple HTML form."""
    return render_template_string(HTML)

@app.route('/play')
def play_video():
    """Proxies the video stream, handling Range requests for seeking."""
    video_url = request.args.get('url')
    if not video_url:
        return "Error: No URL provided.", 400

    # Get the Range header from the client request
    range_header = request.headers.get('Range', None)
    request_headers = {}
    if range_header:
        # Pass the Range header to the upstream server
        request_headers['Range'] = range_header
        print(f"Client requested Range: {range_header}") # For debugging

    try:
        # Make the streaming request to the actual video URL
        # Include the Range header if the client sent one
        upstream_response = requests.get(
            video_url,
            headers=request_headers,
            stream=True,
            timeout=20 # Add a reasonable timeout
        )
        # Raise an exception for bad status codes (4xx client error or 5xx server error)
        # We explicitly handle 200 and 206 later
        if not upstream_response.ok and upstream_response.status_code != 206:
             upstream_response.raise_for_status()

    except requests.exceptions.RequestException as e:
        # Handle connection errors, timeouts, invalid URLs etc.
        error_message = f"Error fetching upstream URL: {e}"
        print(error_message)
        # Return a server error status code
        return error_message, 502 # 502 Bad Gateway is appropriate here

    # --- Prepare the response back to the client ---

    response_headers = {}
    # Copy essential headers from the upstream response
    # Important for seeking: Content-Range, Accept-Ranges, Content-Length (partial)
    # Important for playback: Content-Type
    for header_key in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range']:
        if header_key in upstream_response.headers:
            response_headers[header_key] = upstream_response.headers[header_key]

    # If the upstream didn't explicitly send Accept-Ranges, but we know range requests
    # might work (e.g., status 206), we can add it. Often needed for players.
    if 'Accept-Ranges' not in response_headers and upstream_response.status_code == 206:
        response_headers['Accept-Ranges'] = 'bytes'
    elif 'Accept-Ranges' not in response_headers and 'bytes' in upstream_response.headers.get('Accept-Ranges', ''):
         response_headers['Accept-Ranges'] = 'bytes'


    # Generator function to yield chunks of the video data
    # Use stream_with_context for Flask request context handling
    @stream_with_context
    def generate_stream():
        try:
            # Iterate over chunks from the upstream response
            for chunk in upstream_response.iter_content(chunk_size=8192): # 8KB chunk size
                if chunk: # Filter out keep-alive new chunks
                    yield chunk
        except requests.exceptions.ChunkedEncodingError:
             print("Warning: Upstream connection closed unexpectedly during streaming.")
        except Exception as e:
             print(f"Error during streaming generation: {e}")
        finally:
            # Ensure the upstream connection is closed when done or if an error occurs
            upstream_response.close()
            print("Upstream connection closed.") # For debugging

    # Determine the correct HTTP status code
    # Pass through 206 Partial Content if received, otherwise use 200 OK (if successful)
    status_code = upstream_response.status_code if upstream_response.status_code in [200, 206] else 200

    print(f"Responding to client with Status: {status_code}, Headers: {response_headers}") # For debugging

    # Create and return the Flask Response object
    # Pass the generator, status code, and prepared headers
    return Response(generate_stream(), status=status_code, headers=response_headers)

if __name__ == "__main__":
    # Using threaded=True allows handling multiple requests concurrently (e.g., browser making range requests while playing)
    # Use 0.0.0.0 to make it accessible on your network, or 127.0.0.1 for local access only
    app.run() # Added host, port, debug=True for development
