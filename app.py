from flask import Flask, request, Response, render_template_string, stream_with_context
import requests
import urllib.parse
from bs4 import BeautifulSoup # Need to install: pip install beautifulsoup4 lxml
import re # For basic CSS/JS checks, though not used for rewriting here

app = Flask(__name__)

# --- HTML Template for Input ---
HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Simple Web Proxy</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f4; }
        h2 { color: #333; }
        form { background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type=text] { width: calc(100% - 100px); max-width: 500px; padding: 10px; margin-right: 10px; border: 1px solid #ccc; border-radius: 3px; }
        input[type=submit] { padding: 10px 15px; background-color: #5cb85c; color: white; border: none; border-radius: 3px; cursor: pointer; }
        input[type=submit]:hover { background-color: #4cae4c; }
        .error { color: red; margin-top: 1em; }
    </style>
</head>
<body>
    <h2>Enter URL to Proxy:</h2>
    <form method="get" action="/proxy">
      <input type="text" name="url" placeholder="http://example.com" required>
      <input type="submit" value="Proxy It">
    </form>
    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}
</body>
</html>
"""

# --- Helper Function to Rewrite URLs ---
def rewrite_url(original_url, proxy_base_url):
    """Encodes the original URL to be used as a parameter for the proxy."""
    # Ensure the original URL is absolute before encoding
    if not original_url.startswith(('http://', 'https://', '//')):
         # This case shouldn't happen if urljoin worked, but as a fallback
         print(f"Warning: Skipping rewrite for non-absolute/protocol-relative URL: {original_url}")
         return original_url
    encoded_url = urllib.parse.quote(original_url, safe='') # Fully encode
    return f"{proxy_base_url}?url={encoded_url}"

# --- Flask Routes ---

@app.route('/')
def home():
    """Serves the URL input form."""
    return render_template_string(HOME_HTML)

@app.route('/proxy')
def proxy_request():
    """Handles the proxy request for a given URL."""
    target_url = request.args.get('url')

    if not target_url:
        return render_template_string(HOME_HTML, error="No URL provided.")

    # Ensure the URL has a scheme (default to http if missing)
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url

    try:
        # --- Make the request to the target server ---
        # Copy essential client headers (User-Agent is important)
        headers = { 'User-Agent': request.headers.get('User-Agent', 'FlaskProxy/1.0') }
        # Add more headers if needed (e.g., Accept, Accept-Language)

        # Use stream=True to handle potentially large non-HTML content efficiently
        upstream_response = requests.get(target_url, headers=headers, stream=True, timeout=15, allow_redirects=False) # Don't follow redirects automatically

        # --- Handle Redirects (Basic) ---
        if upstream_response.status_code in (301, 302, 303, 307, 308):
            location = upstream_response.headers.get('Location')
            if location:
                # Resolve relative redirects
                redirect_target_url = urllib.parse.urljoin(target_url, location)
                # Rewrite the redirect URL to go through the proxy
                proxy_redirect_url = rewrite_url(redirect_target_url, request.base_url)
                print(f"Redirecting to: {proxy_redirect_url}")
                # Return a redirect response pointing back to the proxy
                resp = Response(f'Redirecting to <a href="{proxy_redirect_url}">{proxy_redirect_url}</a>...', status=upstream_response.status_code)
                resp.headers['Location'] = proxy_redirect_url
                return resp
            else:
                # Redirect status without Location header - return as is? Or error?
                 return "Redirect status code received without Location header.", upstream_response.status_code

        # Raise errors for other non-OK statuses after handling redirects
        upstream_response.raise_for_status()

        content_type = upstream_response.headers.get('Content-Type', '').lower()

        # --- Process Based on Content Type ---

        if 'text/html' in content_type:
            # --- HTML Content: Parse and Rewrite Links ---
            # Read the entire content (cannot stream and parse easily with BeautifulSoup)
            html_content = upstream_response.content # Read all data
            soup = BeautifulSoup(html_content, 'lxml') # Use lxml parser

            # Base URL for resolving relative paths
            base_url = upstream_response.url # Use the final URL after potential internal requests redirects

            # Find tags with URL attributes and rewrite them
            tags_to_rewrite = {
                'a': 'href',
                'link': 'href',
                'img': 'src',
                'script': 'src',
                'iframe': 'src',
                'form': 'action',
                 # Add more tags/attributes as needed (e.g., 'source': 'src', video 'poster')
            }

            for tag_name, attr_name in tags_to_rewrite.items():
                for tag in soup.find_all(tag_name, **{attr_name: True}): # Find tags where the attribute exists
                    original_link = tag[attr_name]
                    # Resolve relative URLs to absolute URLs
                    absolute_link = urllib.parse.urljoin(base_url, original_link)
                    # Rewrite the absolute URL to point back to the proxy
                    tag[attr_name] = rewrite_url(absolute_link, request.base_url) # request.base_url is like "http://example.koyeb.app/proxy"

            # TODO: Add rewriting for srcset in img/source tags (more complex)
            # TODO: Add rewriting for inline styles with url() - very hard with BS4
            # TODO: Add basic rewriting for meta http-equiv="refresh"

            # Convert modified soup back to string
            modified_html = str(soup)

            # Create response with modified HTML
            resp = Response(modified_html, status=upstream_response.status_code)
            # Copy necessary headers (remove problematic ones if needed)
            for h in ['Content-Type', 'Cache-Control']: # Add others?
                 if h in upstream_response.headers:
                     resp.headers[h] = upstream_response.headers[h]
            # Removing security headers - BE CAREFUL, THIS IS A SECURITY RISK
            # resp.headers.pop('Content-Security-Policy', None)
            # resp.headers.pop('X-Frame-Options', None)

            return resp

        else:
            # --- Non-HTML Content: Stream Directly ---
            @stream_with_context
            def generate_stream():
                try:
                    for chunk in upstream_response.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                except Exception as e:
                    print(f"Error during streaming: {e}")
                finally:
                    upstream_response.close()

            # Copy relevant headers for streaming content
            response_headers = {}
            for header_key in ['Content-Type', 'Content-Length', 'Cache-Control', 'ETag', 'Last-Modified', 'Accept-Ranges', 'Content-Range']:
                 if header_key in upstream_response.headers:
                     response_headers[header_key] = upstream_response.headers[header_key]

            return Response(generate_stream(), status=upstream_response.status_code, headers=response_headers)

    except requests.exceptions.Timeout:
        return render_template_string(HOME_HTML, error=f"Error: Target server timed out accessing {target_url}")
    except requests.exceptions.RequestException as e:
        return render_template_string(HOME_HTML, error=f"Error accessing URL '{target_url}': {e}")
    except Exception as e:
        # Catch other potential errors (like BeautifulSoup parsing)
        return render_template_string(HOME_HTML, error=f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # Make sure to install dependencies: pip install Flask requests beautifulsoup4 lxml
    app.run()
