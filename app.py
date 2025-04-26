from flask import Flask, request, Response, render_template_string
import requests

app = Flask(__name__)

# Simple web page for user to paste the Seedr link
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

    # Get the Range header to support video seeking
    range_header = request.headers.get('Range', None)

    # Start the request to Seedr
    with requests.get(url, stream=True, headers={"Range": range_header}) as r:
        if r.status_code == 206:  # Partial Content (supports Range request)
            content_range = r.headers.get('Content-Range')
            content_length = r.headers.get('Content-Length')
            headers = {
                'Content-Range': content_range,
                'Content-Length': content_length,
                'Accept-Ranges': 'bytes'
            }
        else:
            headers = {}

        # Streaming video in chunks
        def generate():
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        # Respond with the video content
        return Response(generate(), content_type='video/mp4', headers=headers, status=206 if range_header else 200)

if __name__ == "__main__":
    app.run()
