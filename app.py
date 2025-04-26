from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL = "https://col3neg.com"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Target URL
    target_url = f"{BASE_URL}/{path}" if path else BASE_URL

    # Get the page
    try:
        resp = requests.get(target_url, timeout=10)
    except requests.RequestException:
        return "Error fetching page.", 500

    content_type = resp.headers.get('Content-Type', '')

    # If not HTML, serve directly
    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    # Parse HTML
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Replace all <a>, <link>, <script>, <img> href/src to local
    for tag in soup.find_all(['a', 'link', 'script', 'img']):
        attr = 'href' if tag.name in ['a', 'link'] else 'src'
        if tag.has_attr(attr):
            original = tag[attr]
            if original.startswith(BASE_URL):
                original = original.replace(BASE_URL, '')
            if original.startswith('/'):
                tag[attr] = original
            elif original.startswith('http'):
                # External links (ads, youtube, etc) you may want to allow or block
                pass
            else:
                tag[attr] = f"/{original}"

    # Also fix possible internal JS redirects (window.location)
    html = str(soup)
    html = re.sub(r'window\.location\s*=\s*[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'window.location="/\1"', html)
    html = re.sub(r'window\.location\.href\s*=\s*[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'window.location.href="/\1"', html)

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)
