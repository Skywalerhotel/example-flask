from flask import Flask, request, Response
import requests

app = Flask(__name__)
TARGET = "https://seedr.cc"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    resp = requests.get(f"{TARGET}/{path}", params=request.args, headers=request.headers, stream=True)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response

if __name__ == "__main__":
    app.run()
