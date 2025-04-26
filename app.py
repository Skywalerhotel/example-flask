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

    # Fix <a href> to stay local
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('http'):
            if BASE_URL in href or 'col3negtelevision.com' in href:
                # Remove domain, keep path
                href = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)', '', href)
                if not href.startswith('/'):
                    href = '/' + href
                a_tag['href'] = href
        elif href.startswith('/'):
            a_tag['href'] = href
        else:
            a_tag['href'] = f"/{href}"

    # Fix all src links too (img, script, iframe)
    for tag in soup.find_all(['img', 'script', 'iframe', 'link']):
        attr = 'src' if tag.name in ['img', 'script', 'iframe'] else 'href'
        if tag.has_attr(attr):
            src = tag[attr]
            if src.startswith('http'):
                if BASE_URL in src or 'col3negtelevision.com' in src:
                    src = re.sub(r'^https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)', '', src)
                    if not src.startswith('/'):
                        src = '/' + src
                    tag[attr] = src
            elif src.startswith('/'):
                tag[attr] = src
            else:
                tag[attr] = f"/{src}"

    # Fix JavaScript redirects
    html = str(soup)
    html = re.sub(r'window\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^\'"]*)[\'"]', r'window.location="\3"', html)
    html = re.sub(r'window\.location\.href\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^\'"]*)[\'"]', r'window.location.href="\3"', html)
    html = re.sub(r'window\.top\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^\'"]*)[\'"]', r'window.top.location="\3"', html)
    html = re.sub(r'window\.parent\.location\s*=\s*[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^\'"]*)[\'"]', r'window.parent.location="\3"', html)

    # Fix iframe src if directly written
    html = re.sub(r'src=[\'"]https?:\/\/(www\.)?(col3neg\.com|col3negtelevision\.com)([^\'"]*)[\'"]', r'src="\3"', html)

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)
