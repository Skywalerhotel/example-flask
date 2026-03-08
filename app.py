from flask import Flask, request, Response, render_template_string, url_for
import requests, urllib.parse

app = Flask(__name__)

# ===== HOME PAGE =====
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ULTRA PLAYER PRO V7</title>
<style>
body{margin:0;height:100vh;display:flex;justify-content:center;align-items:center;background:#0f172a;font-family:sans-serif;}
.card{background:#111827;padding:30px;border-radius:16px;width:90%;max-width:500px;box-shadow:0 10px 30px rgba(0,0,0,0.4);}
h2{color:white;text-align:center;margin-bottom:20px;}
input{width:100%;padding:12px;border-radius:10px;border:none;margin-bottom:15px;background:#1f2937;color:white;}
button{width:100%;padding:12px;border:none;border-radius:10px;background:#2563eb;color:white;font-weight:bold;cursor:pointer;}
button:hover{background:#1d4ed8;}
</style>
</head>
<body>
<div class="card">
<h2>Paste Video URL</h2>
<form method="get" action="{{ url_for('player') }}">
<input type="text" name="url" placeholder="https://example.com/video.mp4" required>
<button type="submit">Play Video</button>
</form>
</div>
</body>
</html>
"""

# ===== PLAYER PAGE =====
PLAYER_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ULTRA PLAYER PRO V7</title>
<style>
body{margin:0;background:black;overflow:hidden;font-family:sans-serif;}
#player{position:relative;width:100%;height:100vh;background:black;}
video{width:100%;height:100%;object-fit:contain;background:black;}
#controls{position:absolute;bottom:0;width:100%;padding:10px;background:linear-gradient(transparent,rgba(0,0,0,0.8));color:white;display:flex;flex-direction:column;transition:opacity 0.3s;}
#progress{width:100%;}
.row{display:flex;align-items:center;justify-content:space-between;}
button,select{background:none;border:none;color:white;font-size:18px;}
#time{font-size:14px;}
#settings{position:absolute;right:10px;bottom:80px;background:#111;padding:10px;border-radius:8px;display:none;color:white;}
#settings select{width:100%;margin-top:5px;color:white;background:#222;}
.seek-indicator{position:absolute;top:50%;font-size:36px;color:white;background:rgba(0,0,0,0.5);padding:20px;border-radius:50%;opacity:0;transition:0.25s ease;pointer-events:none;}
.seek-indicator.left{ left:15%; }
.seek-indicator.right{ right:15%; }
.seek-show{opacity:1;transform:translateY(-50%) scale(1.2);}
</style>
</head>
<body>

<div id="player">
<video id="video" crossorigin="anonymous" preload="auto" autoplay></video>
<div class="seek-indicator left" id="seekLeft">⏪ 10s</div>
<div class="seek-indicator right" id="seekRight">10s ⏩</div>

<div id="controls">
<input type="range" id="progress" value="0">
<div class="row">
<button id="play">▶</button>
<div id="time"><span id="current">0:00</span> / <span id="total">0:00</span></div>
<div>
<button id="pip">📺</button>
<button id="fs">⛶</button>
<button id="gear">⚙</button>
<select id="speed">
<option>0.5</option><option selected>1</option><option>1.25</option><option>1.5</option><option>2</option>
</select>
</div>
</div>
</div>

<div id="settings">
Audio Tracks
<select id="audioTracks"></select>
<br><br>
Subtitles
<input type="file" id="subload" accept=".srt,.vtt">
</div>

</div>

<script>
const video=document.getElementById("video")
const progress=document.getElementById("progress")
const play=document.getElementById("play")
const fs=document.getElementById("fs")
const pip=document.getElementById("pip")
const gear=document.getElementById("gear")
const settings=document.getElementById("settings")
const speed=document.getElementById("speed")
const subload=document.getElementById("subload")
const audioTracks=document.getElementById("audioTracks")
const current=document.getElementById("current")
const total=document.getElementById("total")
const seekLeft=document.getElementById("seekLeft")
const seekRight=document.getElementById("seekRight")

let lastTap=0
let hideTimer

// Load video
video.src="{{ url_for('stream_video', url=video_url_encoded) }}";

// Format time
function format(t){const m=Math.floor(t/60);const s=Math.floor(t%60).toString().padStart(2,'0');return m+":"+s;}

// Update time & progress
video.addEventListener('loadedmetadata',()=>{total.textContent=format(video.duration);updateAudioTracks();});
video.addEventListener('timeupdate',()=>{progress.value=(video.currentTime/video.duration)*100;current.textContent=format(video.currentTime);});

// Play/pause
play.onclick=()=>{if(video.paused){video.play();play.textContent="⏸"}else{video.pause();play.textContent="▶"}}

// Progress seek
progress.oninput=()=>{video.currentTime=(progress.value/100)*video.duration}

// Speed change
speed.onchange=()=>video.playbackRate=speed.value

// Fullscreen
fs.onclick=()=>{if(!document.fullscreenElement)document.getElementById("player").requestFullscreen();else document.exitFullscreen();}

// PiP
pip.onclick=()=>{if(document.pictureInPictureElement)document.exitPictureInPicture();else video.requestPictureInPicture()}

// Settings toggle
gear.onclick=()=>{settings.style.display=settings.style.display=="block"?"none":"block"}

// Double tap 10s seek
document.getElementById("player").addEventListener("click",(e)=>{
let now=Date.now(); if(now-lastTap<300){let x=e.clientX;if(x<window.innerWidth/2){video.currentTime=Math.max(0,video.currentTime-10);animateSeek(seekLeft);}else{video.currentTime=Math.min(video.duration,video.currentTime+10);animateSeek(seekRight);} video.play();} lastTap=now;
})
function animateSeek(el){el.classList.add("seek-show");setTimeout(()=>el.classList.remove("seek-show"),350);}

// Subtitles
subload.onchange=e=>{
let file=e.target.files[0];if(!file)return
let reader=new FileReader()
reader.onload=function(){let data=reader.result;if(file.name.endsWith(".srt")){data="WEBVTT\\n\\n"+data.replace(/,/g,'.');} let blob=new Blob([data],{type:"text/vtt"}); let url=URL.createObjectURL(blob); let track=document.createElement("track"); track.kind="subtitles"; track.src=url; track.default=true; video.appendChild(track);}
reader.readAsText(file)
}

// Embedded Audio Tracks (MKV)
function updateAudioTracks(){
audioTracks.innerHTML=""
if(video.audioTracks && video.audioTracks.length>0){
for(let i=0;i<video.audioTracks.length;i++){
let opt=document.createElement("option");opt.value=i;opt.text=video.audioTracks[i].label||"Track "+(i+1);audioTracks.appendChild(opt);}
video.audioTracks[0].enabled=true
audioTracks.onchange=()=>{for(let i=0;i<video.audioTracks.length;i++){video.audioTracks[i].enabled=(i==audioTracks.value)}}
}
}

// Auto-hide controls
function showControls(){document.getElementById("controls").style.opacity=1;clearTimeout(hideTimer);hideTimer=setTimeout(()=>document.getElementById("controls").style.opacity=0,3000);}
document.getElementById("player").onmousemove=showControls
video.onplay=showControls

// Swipe gestures
let startX,startY
video.addEventListener("touchstart",e=>{startY=e.touches[0].clientY;startX=e.touches[0].clientX;})
video.addEventListener("touchmove",e=>{let dy=startY-e.touches[0].clientY;let dx=startX-e.touches[0].clientX;if(Math.abs(dy)>Math.abs(dx)){if(startX<window.innerWidth/2){document.body.style.filter=`brightness(${1+dy/300})`}else{video.volume=Math.min(1,Math.max(0,video.volume+dy/500))}}})
</script>

</body>
</html>
"""

# ===== FLASK ROUTES =====
@app.route("/")
def home():
    return render_template_string(HOME_HTML)

@app.route("/player")
def player():
    url = request.args.get("url")
    if not url:
        return "No URL provided", 400
    encoded = urllib.parse.quote(url)
    return render_template_string(PLAYER_HTML, video_url_encoded=encoded)

@app.route("/stream")
def stream_video():
    encoded = request.args.get("url")
    if not encoded:
        return "Missing URL", 400
    video_url = urllib.parse.unquote(encoded)
    range_header = request.headers.get("Range")
    headers = {"User-Agent":"Mozilla/5.0"}
    if range_header: headers["Range"]=range_header
    r = requests.get(video_url, headers=headers, stream=True)
    def generate():
        for chunk in r.iter_content(65536):
            if chunk: yield chunk
    return Response(generate(), status=r.status_code, headers=dict(r.headers))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
