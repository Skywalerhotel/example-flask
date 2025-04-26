from flask import Flask, render_template_string, request, Response, redirect
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://col3neg.com"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Target URL
    target_url = f"{BASE_URL}/{path}"
    if path == "":
        target_url = BASE_URL

    # Get the page
    resp = requests.get(target_url, allow_redirects=False)

    # If redirect
    if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
        location = resp.headers.get('Location', '')
        if location.startswith(BASE_URL):
            location = location.replace(BASE_URL, '')
            return redirect(location)
        else:
            return redirect(location)

    # If not HTML, like CSS/JS/Image, serve directly
    content_type = resp.headers.get('Content-Type', '')
    if not content_type.startswith('text/html'):
        return Response(resp.content, content_type=content_type)

    # Parse HTML
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Fix all <a href="">
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith(BASE_URL):
            href = href.replace(BASE_URL, '')
        if href.startswith('/'):
            a_tag['href'] = href
        elif href.startswith('http'):
            pass
        else:
            a_tag['href'] = f"/{href}"

    # Fix all <img>, <script>, <link>
    for tag in soup.find_all(['img', 'script', 'link']):
        attr = 'src' if tag.name in ['img', 'script'] else 'href'
        if tag.has_attr(attr):
            link = tag[attr]
            if link.startswith(BASE_URL):
                link = link.replace(BASE_URL, '')
            if link.startswith('/'):
                tag[attr] = link
            elif link.startswith('http'):
                pass
            else:
                tag[attr] = f"/{link}"

    # (Optional) Remove tracking scripts / ads here if you want

    return render_template_string(str(soup))

if __name__ == "__main__":
    app.run(debug=True)
