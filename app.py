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

    try:
        resp = requests.get(target_url, timeout=10)
    except requests.RequestException:
        return "Error fetching page.", 500

    content_type = resp.headers.get('Content-Type', '')

    # If not HTML, serve directly
    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Fix all internal links
    for tag in soup.find_all(['a', 'link', 'script', 'img', 'iframe']):
        attr = 'href' if tag.name in ['a', 'link'] else 'src'
        if tag.has_attr(attr):
            original = tag[attr]
            if original.startswith(BASE_URL):
                original = original.replace(BASE_URL, '')
            if original.startswith('/'):
                tag[attr] = original
            elif original.startswith('http'):
                # External links (ad/youtube): allow or block
                pass
            else:
                tag[attr] = f"/{original}"

    # String hacks for javascript redirects
    html = str(soup)

    # Fix various JavaScript redirects
    html = re.sub(r'window\.location\s*=\s*[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'window.location="/\1"', html)
    html = re.sub(r'window\.location\.href\s*=\s*[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'window.location.href="/\1"', html)
    html = re.sub(r'window\.top\.location\s*=\s*[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'window.top.location="/\1"', html)
    html = re.sub(r'window\.parent\.location\s*=\s*[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'window.parent.location="/\1"', html)

    # Also fix iframe src if directly written
    html = re.sub(r'src=[\'"]https:\/\/col3neg\.com([^\'"]*)[\'"]', r'src="/\1"', html)

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)
