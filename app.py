from flask import Flask, request, Response, url_for, render_template_string, stream_with_context
import requests
import urllib.parse
import re

app = Flask(__name__)

# --- STREAM VIDEO ROUTE ---
@app.route('/stream')
def stream_video():
    encoded_url = request.args.get('url')
    if not encoded_url:
        return "Error: Missing video URL.", 400

    try:
        video_url = urllib.parse.unquote(encoded_url)
    except Exception as e:
        return f"Error decoding URL: {e}", 400

    range_header = request.headers.get('Range')
    headers = {}
    if range_header:
        headers['Range'] = range_header

    try:
        upstream = requests.get(video_url, headers=headers, stream=True, timeout=30)
        if not upstream.ok and upstream.status_code not in (200, 206):
            upstream.raise_for_status()
    except Exception as e:
        return f"Error fetching video: {e}", 502

    @stream_with_context
    def generate():
        for chunk in upstream.iter_content(16384):
            if chunk:
                yield chunk
        upstream.close()

    response_headers = {}
    for h in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range', 'ETag', 'Last-Modified']:
        if h in upstream.headers:
            response_headers[h] = upstream.headers[h]

    return Response(generate(), headers=response_headers, status=upstream.status_code)

# --- FETCH OTHER FILES (IMAGES, CSS, JS) ---
@app.route('/fetch')
def fetch_file():
    encoded_url = request.args.get('url')
    if not encoded_url:
        return "Error: Missing file URL.", 400

    try:
        file_url = urllib.parse.unquote(encoded_url)
    except Exception as e:
        return f"Error decoding URL: {e}", 400

    try:
        upstream = requests.get(file_url, stream=True, timeout=30)
        upstream.raise_for_status()
    except Exception as e:
        return f"Error fetching file: {e}", 502

    @stream_with_context
    def generate():
        for chunk in upstream.iter_content(16384):
            if chunk:
                yield chunk
        upstream.close()

    response_headers = {}
    for h in ['Content-Type', 'Content-Length', 'Cache-Control', 'ETag']:
        if h in upstream.headers:
            response_headers[h] = upstream.headers[h]

    return Response(generate(), headers=response_headers, status=upstream.status_code)

# --- PROXY WEB PAGE ---
@app.route('/proxy')
def proxy_page():
    encoded_url = request.args.get('url')
    if not encoded_url:
        return "Error: Missing page URL.", 400

    try:
        target_url = urllib.parse.unquote(encoded_url)
    except Exception as e:
        return f"Error decoding URL: {e}", 400

    try:
        resp = requests.get(target_url, timeout=30)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return f"Error fetching page: {e}", 502

    base_url = target_url

    def replace_src_href(match):
        attr = match.group(1)
        orig = match.group(2)

        # Make absolute URL
        if orig.startswith(('http://', 'https://')):
            full = orig
        elif orig.startswith('//'):
            full = 'https:' + orig
        else:
            full = urllib.parse.urljoin(base_url, orig)

        # Video or normal file
        if full.lower().endswith(('.mp4', '.webm', '.ogg', '.m3u8')):
            proxy_link = url_for('stream_video', url=urllib.parse.quote(full))
            return f'{attr}="{proxy_link}" crossorigin="anonymous"'
        else:
            proxy_link = url_for('fetch_file', url=urllib.parse.quote(full))
            return f'{attr}="{proxy_link}"'

    # Rewrite src and href links
    html = re.sub(r'(src|href)=["\']([^"\']+)["\']', replace_src_href, html)

    return html

# --- HOME PAGE ---
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proxy Server</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f4f4f4; text-align: center; margin-top: 100px; }
            input[type=text] { width: 300px; padding: 10px; }
            button { padding: 10px 20px; background: #28a745; color: white; border: none; }
            button:hover { background: #218838; }
        </style>
    </head>
    <body>
        <h2>Enter a URL to Proxy:</h2>
        <form method="get" action="/proxy">
            <input name="url" placeholder="https://tamilvip.bike/..." required>
            <button type="submit">Go</button>
        </form>
    </body>
    </html>
    ''')

# --- START SERVER ---
if __name__ == "__main__":
    app.run()
