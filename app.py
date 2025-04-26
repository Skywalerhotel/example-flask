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

    def generate():
        with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

    return Response(generate(), content_type='video/mp4')

if __name__ == "__main__":
    app.run()
