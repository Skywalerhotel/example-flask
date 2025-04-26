from flask import Flask, Response, request, jsonify, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import threading
import time
import cv2
import numpy as np

app = Flask(__name__)

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1280x720")  # 720p HD

driver = webdriver.Chrome(options=chrome_options)
lock = threading.Lock()

def get_screenshot():
    with lock:
        png = driver.get_screenshot_as_png()
    np_arr = np.frombuffer(png, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    _, jpeg = cv2.imencode('.jpg', img)
    return jpeg.tobytes()

def generate():
    while True:
        frame = get_screenshot()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.2)

@app.route('/')
def home():
    return "Remote browser server is running!"

@app.route('/open', methods=['POST'])
def open_url():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    with lock:
        try:
            driver.set_page_load_timeout(10)
            driver.get(url)
            return jsonify({'title': driver.title})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stream')
def stream():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Live Remote Browser</title>
    <style>
        body { margin: 0; background: black; overflow: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        img { max-width: 100%; max-height: 100vh; }
        button { padding: 10px 20px; font-size: 20px; margin-top: 10px; }
    </style>
</head>
<body>
    <img id="stream" src="/video_feed">
    <button onclick="goFullScreen()">Go Full Screen</button>

    <script>
        function goFullScreen() {
            var img = document.getElementById("stream");
            if (img.requestFullscreen) {
                img.requestFullscreen();
            } else if (img.webkitRequestFullscreen) {
                img.webkitRequestFullscreen();
            } else if (img.msRequestFullscreen) {
                img.msRequestFullscreen();
            }
        }
    </script>
</body>
</html>
''')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    with lock:
        driver.quit()
    return jsonify({'message': 'Browser closed'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
