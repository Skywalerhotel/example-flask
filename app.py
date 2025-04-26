from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import asyncio
import base64
import pyppeteer

app = Flask(__name__)
socketio = SocketIO(app)

browser = None
page = None

async def start_browser():
    global browser, page
    browser = await pyppeteer.launch(headless=False, args=['--no-sandbox'])
    page = await browser.newPage()
    await page.goto('https://google.com')

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    asyncio.run(send_screenshot())

async def send_screenshot():
    while True:
        screenshot = await page.screenshot()
        encoded = base64.b64encode(screenshot).decode('utf-8')
        socketio.emit('screenshot', {'img': f"data:image/png;base64,{encoded}"})
        await asyncio.sleep(0.5)

@socketio.on('click')
def handle_click(data):
    asyncio.run(page.mouse.click(data['x'], data['y']))

@socketio.on('keypress')
def handle_keypress(data):
    asyncio.run(page.keyboard.type(data['key']))

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_browser())
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
