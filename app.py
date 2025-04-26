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
    if path.startswith("watch") or path.startswith("tvseries") or path.startswith("teledrama"):
        target_url = f"{BASE_URL_TV}/{path}"
    else:
        target_url = f"{BASE_URL_MAIN}/{path}" if path else BASE_URL_MAIN

    try:
        resp = requests.get(target_url, timeout=10)
    except requests.RequestException:
        return "Error fetching page.", 500

    content_type = resp.headers.get('Content-Type', '')

    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    soup = BeautifulSoup(resp.text, 'html.parser')

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

    for tag in soup.find_all(['img', 'script', 'iframe', 'link']):
        attr = 'src' if tag.name in ['img', 'script', 'iframe'] else 'href'
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

    html = str(soup)

    patterns = [
        r'window\.location\s*=\s*['"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^'"]*)['"]',
        r'window\.location\.href\s*=\s*['"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^'"]*)['"]',
        r'window\.top\.location\s*=\s*['"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^'"]*)['"]',
        r'window\.parent\.location\s*=\s*['"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^'"]*)['"]',
    ]

    for pattern in patterns:
        html = re.sub(pattern, r'window.location="\3"', html)

    html = re.sub(
        r'<meta\s+http-equiv=["']refresh["']\s+content=["']\d+;\s*url=(https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com))([^"']*)["']',
        lambda m: f'<meta http-equiv="refresh" content="0;url={m.group(4)}"',
        html,
    )

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
