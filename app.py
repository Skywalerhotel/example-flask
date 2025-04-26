from flask import Flask, Response
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL_MAIN = "https://col3neg.com"
BASE_URL_TV = "https://col3negtelevision.com"
BASE_URL_SEEDR = "https://www.seedr.cc"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Smart URL detection
    if path.startswith("watch"):
        target_url = f"{BASE_URL_TV}/{path}"
    elif path.startswith("video"):
        try:
            # Convert /video/xxx/yyy to /watch-xxx-yyy.html
            parts = path.split('/')
            series_slug = parts[1] if len(parts) > 1 else ''
            video_id = parts[2] if len(parts) > 2 else ''
            watch_slug = f"watch-{series_slug}-{video_id}.html"
            target_url = f"{BASE_URL_TV}/{watch_slug}"
        except Exception:
            return "Error parsing video URL", 400
    elif path.startswith("seedr"):
        seedr_path = path[len("seedr/"):]  # remove 'seedr/' part
        target_url = f"{BASE_URL_SEEDR}/{seedr_path}"
    else:
        target_url = f"{BASE_URL_MAIN}/{path}" if path else BASE_URL_MAIN

    try:
        resp = requests.get(target_url, timeout=10)
    except requests.RequestException:
        return "Error fetching page.", 500

    content_type = resp.headers.get('Content-Type', '')

    # Not HTML (images, js, css, etc)
    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    # Process HTML
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Fix <a href>
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('http'):
            if any(domain in href for domain in ['col3neg.com', 'col3negtelevision.com', 'seedr.cc']):
                href = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc)', '', href)
                if not href.startswith('/'):
                    href = '/' + href
        elif not href.startswith('/'):
            href = '/' + href
        a_tag['href'] = href

    # Fix src in img, script, iframe, link
    for tag in soup.find_all(['img', 'script', 'iframe', 'link']):
        attr = 'src' if tag.name in ['img', 'script', 'iframe'] else 'href'
        if tag.has_attr(attr):
            src = tag[attr]
            if src.startswith('http'):
                if any(domain in src for domain in ['col3neg.com', 'col3negtelevision.com', 'seedr.cc']):
                    src = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc)', '', src)
                    if not src.startswith('/'):
                        src = '/' + src
            elif not src.startswith('/'):
                src = '/' + src
            tag[attr] = src

    html = str(soup)

    # Fix JS redirects
    patterns = [
        r'window\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc)([^\'"]*)[\'"]',
        r'window\.location\.href\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc)([^\'"]*)[\'"]',
        r'window\.top\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc)([^\'"]*)[\'"]',
        r'window\.parent\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc)([^\'"]*)[\'"]',
    ]
    for pattern in patterns:
        html = re.sub(pattern, r'window.location="\3"', html)

    # Fix meta refresh redirects
    html = re.sub(
        r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=(https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com|seedr\.cc))([^"\']*)["\']',
        lambda m: f'<meta http-equiv="refresh" content="0;url={m.group(4)}"',
        html,
        flags=re.IGNORECASE
    )

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)
