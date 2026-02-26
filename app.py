from flask import Flask, request, Response, render_template_string, stream_with_context, url_for
import requests, urllib.parse

app = Flask(__name__)

# --- HTML Templates ---

HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Stream Proxy</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f4; }
        h2 { color: #333; }
        form { background-color: #fff; padding: 20px; border-radius: 5px;
               box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type=text] { width: calc(100% - 100px); max-width: 500px; padding: 10px;
                           margin-right: 10px; border: 1px solid #ccc; border-radius: 3px; }
        input[type=submit] { padding: 10px 15px; background-color: #5cb85c;
                             color: white; border: none; border-radius: 3px; cursor: pointer; }
        input[type=submit]:hover { background-color: #4cae4c; }
    </style>
</head>
<body>
    <h2>Paste the Seedr Video Link:</h2>
    <form method="get" action="{{ url_for('show_player') }}">
        <input type="text" name="url" placeholder="https://www.seedr.cc/..." required>
        <input type="submit" value="Play">
    </form>
</body>
</html>
"""

VIDEO_PLAYER_HTML = """ 
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pro Video Player</title>
<style>
body{margin:0;background:#0f172a;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial}
.player{width:95%;max-width:900px;background:#000;position:relative;border-radius:12px;overflow:hidden;cursor:pointer}
video{width:100%;display:block}
.loader{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:60px;height:60px;border:6px solid rgba(255,255,255,0.2);border-top:6px solid #fff;border-radius:50%;animation:spin 1s linear infinite;display:none}
@keyframes spin{100%{transform:translate(-50%,-50%) rotate(360deg)}}
.seek-indicator{position:absolute;top:50%;transform:translateY(-50%);font-size:40px;color:white;opacity:0;transition:0.3s}
.seek-left{left:20%}.seek-right{right:20%}.show{opacity:1;transform:translateY(-50%) scale(1.2)}
.controls{position:absolute;bottom:0;width:100%;background:linear-gradient(to top,rgba(0,0,0,0.9),transparent);padding:10px;box-sizing:border-box;transition:0.3s}
.hide-controls{opacity:0}
.progress{width:100%;height:6px;background:#333;border-radius:5px;cursor:pointer;position:relative;margin-bottom:8px}
.buffered{position:absolute;height:100%;background:#666;width:0%;border-radius:5px}
.progress-filled{position:absolute;height:100%;width:0%;background:#ff0000;border-radius:5px}
.control-row{display:flex;justify-content:space-between;align-items:center}
.left,.right{display:flex;align-items:center;gap:10px}
button,select{background:none;border:none;color:white;font-size:16px;cursor:pointer}
input[type=range]{cursor:pointer}
.time{font-size:14px}
</style>
</head>
<body>

<div class="player" id="player">
<video id="video" src="{{ url_for('stream_video', url=video_url_encoded) }}" autoplay preload="auto"></video>
<div class="loader" id="loader"></div>
<div class="seek-indicator seek-left" id="seekLeft">⏪ <span id="leftCount">10</span>s</div>
<div class="seek-indicator seek-right" id="seekRight"><span id="rightCount">10</span>s ⏩</div>

<div class="controls" id="controls">
<div class="progress" id="progress"><div class="buffered" id="buffered"></div><div class="progress-filled" id="progressFilled"></div></div>
<div class="control-row">
<div class="left">
<button id="playPause">▶</button>
<button id="mute">🔊</button>
<input type="range" id="volume" min="0" max="1" step="0.05" value="1">
<span class="time" id="currentTime">0:00</span> /
<span class="time" id="duration">0:00</span>
</div>
<div class="right">
<select id="speed"><option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="1.5">1.5x</option><option value="2">2x</option></select>
<button id="pip">📺</button>
<button id="fullscreen">⛶</button>
</div>
</div>
</div>
</div>

<script>
const video=document.getElementById("video");const player=document.getElementById("player");const controls=document.getElementById("controls");
const loader=document.getElementById("loader");const progress=document.getElementById("progress");const progressFilled=document.getElementById("progressFilled");
const bufferedBar=document.getElementById("buffered");const playPause=document.getElementById("playPause");const mute=document.getElementById("mute");
const volume=document.getElementById("volume");const speed=document.getElementById("speed");const fullscreen=document.getElementById("fullscreen");
const pip=document.getElementById("pip");const currentTime=document.getElementById("currentTime");const duration=document.getElementById("duration");

let lastTap=0,tapCount=10,hideTimeout;

playPause.onclick=()=>{if(video.paused){video.play();playPause.textContent="❚❚";}else{video.pause();playPause.textContent="▶";}};
video.onwaiting=()=>loader.style.display="block";video.onplaying=()=>loader.style.display="none";
video.ontimeupdate=()=>{const percent=(video.currentTime/video.duration)*100;progressFilled.style.width=percent+"%";currentTime.textContent=format(video.currentTime)};
video.onloadedmetadata=()=>duration.textContent=format(video.duration);
function format(t){const m=Math.floor(t/60);const s=Math.floor(t%60).toString().padStart(2,"0");return m+":"+s;}
video.onprogress=()=>{if(video.buffered.length>0){const bufferedEnd=video.buffered.end(video.buffered.length-1);bufferedBar.style.width=(bufferedEnd/video.duration*100)+"%"}}; 
progress.onclick=(e)=>{const rect=progress.getBoundingClientRect();const x=e.clientX-rect.left;video.currentTime=(x/rect.width)*video.duration};
player.onclick=(e)=>{let now=Date.now();if(now-lastTap<300){tapCount+=10;const rect=player.getBoundingClientRect();const x=e.clientX-rect.left;if(x<rect.width/2){video.currentTime=Math.max(0,video.currentTime-10);document.getElementById("leftCount").textContent=tapCount;show("seekLeft")}else{video.currentTime=Math.min(video.duration,video.currentTime+10);document.getElementById("rightCount").textContent=tapCount;show("seekRight")}video.play();}else tapCount=10;lastTap=now};
function show(id){const el=document.getElementById(id);el.classList.add("show");setTimeout(()=>el.classList.remove("show"),400);}
volume.oninput=()=>video.volume=volume.value;
mute.onclick=()=>{video.muted=!video.muted;mute.textContent=video.muted?"🔇":"🔊";};
speed.onchange=()=>video.playbackRate=speed.value;
fullscreen.onclick=()=>{if(!document.fullscreenElement)player.requestFullscreen();else document.exitFullscreen();};
pip.onclick=async()=>{if(document.pictureInPictureElement)document.exitPictureInPicture();else await video.requestPictureInPicture();};
document.onkeydown=(e)=>{if(e.code==="Space"){e.preventDefault();playPause.click();}if(e.code==="ArrowRight")video.currentTime+=10;if(e.code==="ArrowLeft")video.currentTime-=10;};
function resetHide(){controls.classList.remove("hide-controls");clearTimeout(hideTimeout);hideTimeout=setTimeout(()=>controls.classList.add("hide-controls"),3000);}
player.onmousemove=resetHide;video.onplay=resetHide;
</script>

</body>
</html>
"""

# --- Flask Routes ---

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/player')
def show_player():
    url = request.args.get('url')
    if not url:
        return "Error: No URL provided.", 400
    encoded = urllib.parse.quote(url)
    return render_template_string(VIDEO_PLAYER_HTML, video_url_encoded=encoded)

@app.route('/stream')
def stream_video():
    encoded = request.args.get('url')
    if not encoded:
        return "Error: Missing video URL.", 400
    try:
        video_url = urllib.parse.unquote(encoded)
    except:
        return "Error decoding URL.", 400

    range_header = request.headers.get('Range')
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; StreamProxy/1.0)'}
    if range_header: headers['Range'] = range_header

    try:
        upstream = requests.get(video_url, headers=headers, stream=True, timeout=(3,8))
    except requests.exceptions.Timeout:
        return "Upstream timeout", 504
    except Exception as e:
        return f"Error fetching video: {e}", 502

    response_headers = {}
    for h in ['Content-Type','Content-Length','Accept-Ranges','Content-Range']:
        if h in upstream.headers: response_headers[h] = upstream.headers[h]
    if 'Accept-Ranges' not in response_headers: response_headers['Accept-Ranges'] = 'bytes'

    @stream_with_context
    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=32768):
                if chunk: yield chunk
        finally:
            upstream.close()

    return Response(generate(), status=upstream.status_code, headers=response_headers)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
