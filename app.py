from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL_MAIN = "https://col3neg.com"
BASE_URL_TV = "https://col3negtelevision.com"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Smart URL detection
    if path.startswith("watch"):
        target_url = f"{BASE_URL_TV}/{path}"
    elif path.startswith("video"):
        try:
            parts = path.split('/')
            series_slug = parts[1] if len(parts) > 1 else ''
            video_id = parts[2] if len(parts) > 2 else ''
            watch_slug = f"watch-{series_slug}-{video_id}.html"
            target_url = f"{BASE_URL_TV}/{watch_slug}"
        except Exception:
            return "Error parsing video URL", 400
    elif path.startswith("embed"):
        target_url = f"{BASE_URL_TV}/{path}"
        if request.query_string:
            target_url += '?' + request.query_string.decode('utf-8')
    else:
        target_url = f"{BASE_URL_MAIN}/{path}" if path else BASE_URL_MAIN

    headers = {
        "User-Agent": request.headers.get("User-Agent", "Mozilla/5.0")
    }

    try:
        resp = requests.get(target_url, headers=headers, timeout=10)
    except requests.RequestException:
        return "Error fetching page.", 500

    content_type = resp.headers.get('Content-Type', '')

    # For non-HTML (images, css, js, fonts)
    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Fix all <a> href
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('http'):
            if 'col3neg.com' in href or 'col3negtelevision.com' in href:
                href = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)', '', href)
                if not href.startswith('/'):
                    href = '/' + href
        elif not href.startswith('/'):
            href = '/' + href
        a_tag['href'] = href

    # Fix src for img, iframe, script, link
    for tag in soup.find_all(['img', 'iframe', 'script', 'link']):
        attr = 'src' if tag.name in ['img', 'iframe', 'script'] else 'href'
        if tag.has_attr(attr):
            src = tag[attr]
            if src.startswith('http'):
                if 'col3neg.com' in src or 'col3negtelevision.com' in src:
                    src = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)', '', src)
                    if not src.startswith('/'):
                        src = '/' + src
            elif not src.startswith('/'):
                src = '/' + src
            tag[attr] = src

    # Remove ad iframes
    for iframe in soup.find_all('iframe', src=True):
        if any(ad_domain in iframe['src'] for ad_domain in ['ads.com', 'adsterra', 'popads', 'propellerads']):
            iframe.decompose()

    html = str(soup)

    # Fix JavaScript redirects
    js_patterns = [
        r'window\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3negtelevision\.com|col3neg\.com)([^\'"]*)[\'"]',
        r'window\.location\.href\s*=\s*[\'"]https?:\/\/(www\.)?(col3negtelevision\.com|col3neg\.com)([^\'"]*)[\'"]',
        r'window\.top\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3negtelevision\.com|col3neg\.com)([^\'"]*)[\'"]',
        r'window\.parent\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3negtelevision\.com|col3neg\.com)([^\'"]*)[\'"]',
    ]
    for pattern in js_patterns:
        html = re.sub(pattern, r'window.location="\3"', html)

    # Fix meta refresh redirects
    html = re.sub(
        r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=(https?:\/\/(www\.)?(col3negtelevision\.com|col3neg\.com))([^"\']*)["\']',
        lambda m: f'<meta http-equiv="refresh" content="0;url={m.group(4)}"',
        html,
        flags=re.IGNORECASE
    )

    return Response(html, content_type='text/html')

# Special route for embeds (videos)
@app.route('/embed/<video_id>')
def embed(video_id):
    query = request.query_string.decode('utf-8')
    target_url = f"{BASE_URL_TV}/embed/{video_id}"
    if query:
        target_url += '?' + query

    headers = {
        "User-Agent": request.headers.get("User-Agent", "Mozilla/5.0")
    }

    try:
        resp = requests.get(target_url, headers=headers, timeout=10)
    except requests.RequestException:
        return "Error fetching embed page.", 500

    content_type = resp.headers.get('Content-Type', '')

    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    soup = BeautifulSoup(resp.text, 'html.parser')

    for iframe in soup.find_all('iframe', src=True):
        src = iframe['src']
        if src.startswith('http'):
            if 'col3neg.com' in src or 'col3negtelevision.com' in src:
                src = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)', '', src)
                if not src.startswith('/'):
                    src = '/' + src
        iframe['src'] = src

    html = str(soup)
    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)

