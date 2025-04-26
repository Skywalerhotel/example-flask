from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin

app = Flask(__name__)

BASE_URL_MAIN = "https://col3neg.com"
BASE_URL_TV = "https://col3negtelevision.com"

def rewrite_url(url, target_url):
    """Rewrites URLs to be relative to the proxy if they belong to the target domains."""
    absolute_url = urljoin(target_url, url)
    parsed = urlparse(absolute_url)
    
    # Check if the domain is one of our target domains
    if parsed.netloc.endswith(('col3neg.com', 'col3negtelevision.com')):
        new_url = parsed.path
        if parsed.query:
            new_url += '?' + parsed.query
        if parsed.fragment:
            new_url += '#' + parsed.fragment
        # Ensure the URL starts with a slash
        if not new_url.startswith('/'):
            new_url = '/' + new_url
        return new_url
    return absolute_url  # Return absolute URL for external links

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Determine target URL based on path
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
    else:
        target_url = f"{BASE_URL_MAIN}/{path}" if path else BASE_URL_MAIN

    # Fetch content from target URL
    headers = {"User-Agent": request.headers.get("User-Agent", "Mozilla/5.0")}
    try:
        resp = requests.get(target_url, headers=headers, timeout=10)
    except requests.RequestException:
        return "Error fetching page", 500

    content_type = resp.headers.get('Content-Type', '')

    # Bypass processing for non-HTML content
    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    # Process HTML content
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Rewrite all links and resources
    for tag in soup.find_all(['a', 'img', 'iframe', 'script', 'link']):
        if tag.name == 'a' and tag.has_attr('href'):
            tag['href'] = rewrite_url(tag['href'], target_url)
        elif tag.name in ['img', 'iframe', 'script'] and tag.has_attr('src'):
            tag['src'] = rewrite_url(tag['src'], target_url)
        elif tag.name == 'link' and tag.has_attr('href'):
            tag['href'] = rewrite_url(tag['href'], target_url)

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
        html = re.sub(pattern, r'window.location="\3"', html, flags=re.IGNORECASE)

    # Fix meta refresh redirects
    html = re.sub(
        r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=(https?:\/\/(www\.)?(col3negtelevision\.com|col3neg\.com))([^"\']*)["\']',
        lambda m: f'<meta http-equiv="refresh" content="0;url={m.group(4)}"',
        html,
        flags=re.IGNORECASE
    )

    return Response(html, content_type='text/html')

if __name__ == "__main__":
    app.run(debug=True)
