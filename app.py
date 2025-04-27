from flask import Flask, request, Response, render_template_string, url_for
import requests
import urllib.parse
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# --- HTML Templates ---
HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Universal Proxy</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f4; }
        h2 { color: #333; margin-top: 2em; }
        form { background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2em; }
        input[type=text] { width: calc(100% - 100px); max-width: 500px; padding: 10px; margin-right: 10px; border: 1px solid #ccc; border-radius: 3px; }
        input[type=submit] { padding: 10px 15px; background-color: #5cb85c; color: white; border: none; border-radius: 3px; cursor: pointer; }
        input[type=submit]:hover { background-color: #4cae4c; }
        .notice { color: #666; font-size: 0.9em; margin-top: 0.5em; }
    </style>
</head>
<body>
    <h2>Stream Video:</h2>
    <form method="get" action="{{ url_for('show_player') }}">
      <input type="text" name="url" placeholder="https://example.com/video.mp4" required>
      <input type="submit" value="Play">
    </form>
    <div class="notice">Supports MP4, WebM, and other video formats with range requests</div>

    <h2>Browse Website:</h2>
    <form method="get" action="{{ url_for('proxy_website') }}">
      <input type="text" name="url" placeholder="https://example.com/" required>
      <input type="submit" value="Browse">
    </form>
    <div class="notice">All website resources will be proxied through this server</div>
</body>
</html>
"""

VIDEO_PLAYER_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Video Player</title>
    <style>
        body { margin: 0; background: #000; }
        video { width: 100%; height: 100vh; }
    </style>
</head>
<body>
    <video controls autoplay playsinline>
        <source src="{{ video_url }}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/player')
def show_player():
    video_url = request.args.get('url')
    if not video_url:
        return "Missing video URL", 400
    
    proxied_url = url_for('proxy_resource', url=video_url)
    return render_template_string(VIDEO_PLAYER_HTML, video_url=proxied_url)

@app.route('/proxy-website')
def proxy_website():
    base_url = request.args.get('url')
    if not base_url:
        return "Missing website URL", 400

    if not base_url.startswith(('http://', 'https://')):
        base_url = 'http://' + base_url

    try:
        response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except Exception as e:
        return f"Error fetching website: {str(e)}", 502

    content_type = response.headers.get('Content-Type', '')
    if 'text/html' not in content_type:
        return Response(response.content, content_type=content_type)

    soup = BeautifulSoup(response.text, 'html.parser')
    tags_attrs = {
        'a': 'href',
        'link': 'href',
        'img': 'src',
        'script': 'src',
        'iframe': 'src',
        'form': 'action',
        'source': 'src',
        'video': 'poster',
        'audio': 'src',
    }

    for tag_name, attr in tags_attrs.items():
        for tag in soup.find_all(tag_name):
            if tag.get(attr):
                absolute_url = urllib.parse.urljoin(base_url, tag[attr])
                tag[attr] = url_for('proxy_resource', url=absolute_url)

    # Handle srcset attributes
    for img in soup.find_all('img', srcset=True):
        new_srcset = []
        for source in img['srcset'].split(','):
            url_part = source.strip().split()[0]
            absolute_url = urllib.parse.urljoin(base_url, url_part)
            new_srcset.append(source.replace(url_part, url_for('proxy_resource', url=absolute_url)))
        img['srcset'] = ','.join(new_srcset)

    # Handle CSS url() references
    for style in soup.find_all('style'):
        if style.string:
            style.string = re.sub(
                r'url\((["\']?)(.*?)\1\)',
                lambda m: f'url({m.group(1)}{url_for("proxy_resource", url=urllib.parse.urljoin(base_url, m.group(2)))}{m.group(1)})',
                style.string
            )

    return Response(str(soup), content_type='text/html')

@app.route('/proxy/<path:url>')
def proxy_resource(url):
    headers = {}
    range_header = request.headers.get('Range')
    if range_header:
        headers['Range'] = range_header

    try:
        resp = requests.get(url, headers=headers, stream=True)
        if resp.status_code not in (200, 206):
            resp.raise_for_status()
    except Exception as e:
        return f"Error fetching resource: {str(e)}", 502

    excluded_headers = ['content-encoding', 'transfer-encoding', 'connection']
    response_headers = [
        (k, v) for k, v in resp.raw.headers.items()
        if k.lower() not in excluded_headers
    ]

    return Response(
        resp.iter_content(chunk_size=16384),
        status=resp.status_code,
        headers=response_headers
    )

if __name__ == '__main__':
    app.run(threaded=True, port=5000)
