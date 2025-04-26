from flask import Flask, request, Response, redirect
import requests

app = Flask(__name__)
TARGET = "https://www.seedr.cc"

# Copy all request headers except 'host'
def get_headers():
    headers = {}
    for h in request.headers:
        if h[0].lower() != 'host':
            headers[h[0]] = h[1]
    return headers

@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    url = f"{TARGET}/{path}"
    
    # Forward request to seedr
    resp = requests.request(
        method=request.method,
        url=url,
        headers=get_headers(),
        params=request.args,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
        stream=True,
    )

    # Handle redirects manually (important for login)
    if resp.status_code in (301, 302, 303, 307, 308):
        redirect_location = resp.headers.get('Location')
        if redirect_location.startswith(TARGET):
            redirect_location = redirect_location[len(TARGET):]
        return redirect(redirect_location, code=resp.status_code)

    # Exclude problematic headers
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    
    # Send back the response
    response = Response(resp.content, resp.status_code, headers)
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
