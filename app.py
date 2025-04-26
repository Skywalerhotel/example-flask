from flask import Flask, request, Response, render_template_string, stream_with_context, redirect
import requests
import urllib.parse
import re

app = Flask(__name__)

# Home page with input form
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
            # If it's HTML, we need to rewrite links
            html = upstream_response.content.decode('utf-8', errors='ignore')

            # Base URL for relative links
            parsed_url = urllib.parse.urlparse(target_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Replacing src, href, action inside HTML to point through our proxy
            def replace_link(match):
                original_url = match.group(2)
                if original_url.startswith(('http://', 'https://')):
                    new_url = '/fetch?url=' + urllib.parse.quote(original_url)
                elif original_url.startswith('//'):
                    new_url = '/fetch?url=' + urllib.parse.quote(parsed_url.scheme + ':' + original_url)
                else:
                    # Handle relative paths
                    absolute_url = urllib.parse.urljoin(base_url, original_url)
                    new_url = '/fetch?url=' + urllib.parse.quote(absolute_url)
                return f'{match.group(1)}="{new_url}"'

            # Rewrite links
            html = re.sub(r'(src|href|action)\s*=\s*["\']([^"\']+)["\']', replace_link, html, flags=re.IGNORECASE)

            return Response(html, content_type=content_type)

        else:
            # For non-HTML (images, videos, css, js...), stream directly
            @stream_with_context
            def stream_content():
                for chunk in upstream_response.iter_content(chunk_size=16384):
                    if chunk:
                        yield chunk

            headers = {'Content-Type': content_type}
            return Response(stream_content(), status=upstream_response.status_code, headers=headers)

    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}", 502

if __name__ == "__main__":
    app.run()
