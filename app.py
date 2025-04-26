from flask import Flask, request, Response, render_template_string
import requests

app = Flask(__name__)

# Simple web page
HTML = """
<!doctype html>
<title>Stream Proxy</title>
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

    # Get the range from the request headers (if any)
    range_header = request.headers.get('Range', None)
    
    def generate():
        with requests.get(url, stream=True, headers={"Range": range_header}) as r:
            if range_header and r.status_code == 206:  # Partial content response
                # Stream video content chunk by chunk
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            else:
                # If no range is requested, just stream the full content
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk

    # Return the video with proper content type and range support
    return Response(generate(), content_type='video/mp4', status=206 if range_header else 200)

if __name__ == "__main__":
    app.run()
