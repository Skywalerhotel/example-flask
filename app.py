from flask import Flask, request, Response, render_template_string, stream_with_context, redirect
import requests
import urllib.parse
import re

app = Flask(__name__)

# Home page
HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
    <title>Simple Full Proxy</title>
</head>
<body>
    <h2>Enter a URL to Proxy:</h2>
    <form action="/fetch" method="get">
        <input type="text" name="url" placeholder="https://example.com" required style="width:400px;">
        <input type="submit" value="Go">
    </form>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/fetch')
def fetch():
    target_url = request.args.get('url')
    if not target_url:
        return "Error: No URL provided.", 400

    try:
        # Fetch the external page
        upstream_response = requests.get(target_url, stream=True, timeout=15)

        content_type = upstream_response.headers.get('Content-Type', '')

        if 'text/html' in content_type:
            # HTML page — rewrite links
            html = upstream_response.content.decode('utf-8', errors='ignore')

            parsed_url = urllib.parse.urlparse(target_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            def rewrite_link(match):
                original_url = match.group(2)
                if original_url.startswith(('http://', 'https://')):
                    if is_video(original_url):
                        new_url = '/stream?url=' + urllib.parse.quote(original_url)
                    else:
                        new_url = '/fetch?url=' + urllib.parse.quote(original_url)
                elif original_url.startswith('//'):
                    full_url = parsed_url.scheme + ':' + original_url
                    if is_video(full_url):
                        new_url = '/stream?url=' + urllib.parse.quote(full_url)
                    else:
                        new_url = '/fetch?url=' + urllib.parse.quote(full_url)
                else:
                    absolute_url = urllib.parse.urljoin(base_url, original_url)
                    if is_video(absolute_url):
                        new_url = '/stream?url=' + urllib.parse.quote(absolute_url)
                    else:
                        new_url = '/fetch?url=' + urllib.parse.quote(absolute_url)
                return f'{match.group(1)}="{new_url}"'

            html = re.sub(r'(src|href|action)\s*=\s*["\']([^"\']+)["\']', rewrite_link, html, flags=re.IGNORECASE)

            return Response(html, content_type=content_type)

        else:
            # Non-HTML (image, css, js, etc) — direct stream
            @stream_with_context
            def stream_content():
                for chunk in upstream_response.iter_content(chunk_size=16384):
                    if chunk:
                        yield chunk

            headers = {'Content-Type': content_type}
            return Response(stream_content(), status=upstream_response.status_code, headers=headers)

    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}", 502

# --- Special Route for video streaming (with Range support) ---
@app.route('/stream')
def stream_video():
    encoded_url = request.args.get('url')
    if not encoded_url:
        return "Error: Missing URL parameter.", 400

    try:
        video_url = urllib.parse.unquote(encoded_url)
    except Exception as e:
        return f"Error decoding URL: {e}", 400

    range_header = request.headers.get('Range')
    headers = {}
    if range_header:
        headers['Range'] = range_header

    try:
        upstream_response = requests.get(video_url, headers=headers, stream=True, timeout=30)
        if not upstream_response.ok and upstream_response.status_code not in [200, 206]:
            upstream_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching video URL: {e}", 502

    # Stream the video
    @stream_with_context
    def generate():
        try:
            for chunk in upstream_response.iter_content(chunk_size=16384):
                if chunk:
                    yield chunk
        finally:
            upstream_response.close()

    response_headers = {}
    for key in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range']:
        if key in upstream_response.headers:
            response_headers[key] = upstream_response.headers[key]

    if 'Accept-Ranges' not in response_headers and upstream_response.status_code == 206:
        response_headers['Accept-Ranges'] = 'bytes'

    return Response(generate(), status=upstream_response.status_code, headers=response_headers)

# --- Helper function to detect if a URL is a video ---
def is_video(url):
    return url.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m3u8', '.ts'))

if __name__ == "__main__":
    app.run()
