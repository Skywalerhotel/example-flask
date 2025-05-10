from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    # Display client details
    client_details = {
        "client_ip": request.remote_addr,
        "client_headers": dict(request.headers),
        "method": request.method,
        "path": request.full_path,
        "body": request.get_data().decode('utf-8'),
    }

    # Print client details to console (optional)
    print("Client Details: ", client_details)

    # Forward the request to the target URL
    target_url = request.args.get('url')  # Pass the target URL as a query parameter
    if not target_url:
        return jsonify({"error": "Target URL not specified. Use ?url=<target_url>"}), 400

    try:
        # Forward the request to the target and capture the response
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for key, value in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

        # Return the response to the client
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = app.response_class(resp.content, resp.status_code, headers)
        return response

    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    from waitress import serve
    import os

    # Use HTTPS for the proxy server
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)
