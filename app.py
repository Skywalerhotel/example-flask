from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://col3neg.com"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Fetch content from the real website
    url = f"{BASE_URL}/{path}"
    resp = requests.get(url)

    # Parse HTML
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Rewrite all links to go through your Flask server
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/'):
            a_tag['href'] = href  # keep internal links same
        elif href.startswith(BASE_URL):
            new_href = href.replace(BASE_URL, '')  # remove domain
            a_tag['href'] = new_href
        elif href.startswith('http'):
            pass  # external links (leave them)
        else:
            # relative link
            a_tag['href'] = f"/{href}"

    return render_template_string(str(soup))

if __name__ == "__main__":
    app.run(debug=True)
