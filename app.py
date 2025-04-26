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

    # Get the Range header from the request
    range_header = request.headers.get('Range', None)
    
    # Start the request to Seedr
    with requests.get(url, stream=True, headers={"Range": range_header}) as r:
        # If Seedr supports range requests, we expect status 206 (Partial Content)
        if range_header and r.status_code == 206:
            # Setting the content range for partial content
            content_range = r.headers.get('Content-Range')
            content_length = r.headers.get('Content-Length')
            if content_range:
                start, end, total = content_range.split(' ')[1].split('/')
                # Fix: We will include Content-Range and Content-Length for the streaming
                headers = {
                    'Content-Range': content_range,
                    'Content-Length': content_length,
                    'Accept-Ranges': 'bytes'
                }
            else:
                headers = {}
        else:
            headers = {}

        # Stream the video content
        def generate():
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        return Response(generate(), content_type='video/mp4', headers=headers, status=206 if range_header else 200)

if __name__ == "__main__":
    app.run()
