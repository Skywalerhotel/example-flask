from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL = "https://tamilvip.bike"

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

    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Fix <a href> links
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('http'):
            if BASE_URL in href:
                href = re.sub(r'^https?:\/\/(www\.)?tamilyogi\.blog', '', href)
                if not href.startswith('/'):
                    href = '/' + href
                a_tag['href'] = href
        elif href.startswith('/'):
            a_tag['href'] = href
        else:
            a_tag['href'] = f"/{href}"

    # Fix images, scripts, etc
    for tag in soup.find_all(['img', 'script', 'iframe', 'link']):
        attr = 'src' if tag.name in ['img', 'script', 'iframe'] else 'href'
        if tag.has_attr(attr):
            src = tag[attr]
            if src.startswith('http'):
                if BASE_URL in src:
                    src = re.sub(r'^https?:\/\/(www\.)?tamilyogi\.blog', '', src)
                    if not src.startswith('/'):
                        src = '/' + src
                    tag[attr] = src
            elif src.startswith('/'):
                tag[attr] = src
            else:
                tag[attr] = f"/{src}"

    # Fix JavaScript redirections
    html = str(soup)
    html = re.sub(r'window\.location\s*=\s*[\'"]https?:\/\/(www\.)?tamilyogi\.blog([^\'"]*)[\'"]', r'window.location="\2"', html)
    html = re.sub(r'window\.location\.href\s*=\s*[\'"]https?:\/\/(www\.)?tamilyogi\.blog([^\'"]*)[\'"]', r'window.location.href="\2"', html)
    html = re.sub(r'window\.top\.location\s*=\s*[\'"]https?:\/\/(www\.)?tamilyogi\.blog([^\'"]*)[\'"]', r'window.top.location="\2"', html)
    html = re.sub(r'window\.parent\.location\s*=\s*[\'"]https?:\/\/(www\.)?tamilyogi\.blog([^\'"]*)[\'"]', r'window.parent.location="\2"', html)

    # Fix iframe src too
    html = re.sub(r'src=[\'"]https?:\/\/(www\.)?tamilyogi\.blog([^\'"]*)[\'"]', r'src="\2"', html)

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)
