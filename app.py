from flask import Flask, request, Response, render_template_string
import requests, urllib.parse

app = Flask(__name__)

# ================= HOME PAGE =================
HOME_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pasan Ultra Player</title>
<style>
body{
margin:0;
height:100vh;
display:flex;
justify-content:center;
align-items:center;
background:linear-gradient(135deg,#0f172a,#1e293b);
font-family:Arial;
}
/* Liquid Glass Card */
.card{
background: rgba(255,255,255,0.05);
backdrop-filter: blur(12px) saturate(180%);
-webkit-backdrop-filter: blur(12px) saturate(180%);
padding:30px;
border-radius:16px;
width:90%;
max-width:500px;
box-shadow:0 10px 30px rgba(0,0,0,0.4);
color:white;
}
h2{
color:white;
text-align:center;
margin-bottom:20px;
}
input{
width:100%;
padding:12px;
border:none;
border-radius:10px;
background: rgba(255,255,255,0.05);
backdrop-filter: blur(8px);
-webkit-backdrop-filter: blur(8px);
border:1px solid rgba(255,255,255,0.2);
color:white;
margin-bottom:15px;
}
button{
width:100%;
padding:12px;
border:none;
border-radius:10px;
background: rgba(255,255,255,0.1);
backdrop-filter: blur(8px);
-webkit-backdrop-filter: blur(8px);
border:1px solid rgba(255,255,255,0.2);
color:white;
font-weight:bold;
cursor:pointer;
transition:0.3s;
}
button:hover{
background: rgba(255,255,255,0.2);
transform:scale(1.05);
}
</style>
</head>
<body>
<div class="card">
<h2>Pasan Ultra Player</h2>
<form action="/player">
<input name="url" placeholder="Paste video URL" required>
<button>Play Video</button>
</form>
</div>
</body>
</html>
"""

# ================= PLAYER PAGE =================
VIDEO_PLAYER_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pasan Ultra Player MAX</title>

<style>
body{
margin:0;
background:#0f172a;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
font-family:Arial;
}
.player{
width:95%;
max-width:1100px;
background:black;
border-radius:18px;
overflow:hidden;
position:relative;
display:flex;
justify-content:center;
align-items:center;
}
video{
width:100%;
display:block;
background:black;
object-fit:contain;
}

/* loader */
.loader{
position:absolute;
top:50%;
left:50%;
transform:translate(-50%,-50%);
width:55px;
height:55px;
border:5px solid rgba(255,255,255,0.2);
border-top:5px solid white;
border-radius:50%;
animation:spin 1s linear infinite;
display:none;
}
@keyframes spin{
100%{transform:translate(-50%,-50%) rotate(360deg)}
}

/* controls - Liquid Glass */
.controls{
position:absolute;
bottom:15px;
left:50%;
transform:translateX(-50%);
width:95%;
max-width:1100px;
background: rgba(255,255,255,0.05);
backdrop-filter: blur(12px) saturate(180%);
-webkit-backdrop-filter: blur(12px) saturate(180%);
border-radius:20px;
padding:15px;
box-shadow:0 8px 32px rgba(0,0,0,0.4);
transition:0.3s ease;
}
.progress{
height:6px;
background: rgba(255,255,255,0.1);
border-radius:5px;
cursor:pointer;
position:relative;
margin-bottom:12px;
}
.buffered{
position:absolute;
height:100%;
background: rgba(255,255,255,0.2);
width:0%;
border-radius:5px;
}
.played{
position:absolute;
height:100%;
background:linear-gradient(90deg,#ef4444,#f97316);
width:0%;
border-radius:5px;
}
.row{
display:flex;
justify-content:space-between;
align-items:center;
}
button,select{
background: rgba(255,255,255,0.1);
border-radius:12px;
padding:8px 12px;
backdrop-filter: blur(8px);
-webkit-backdrop-filter: blur(8px);
border:1px solid rgba(255,255,255,0.2);
color:white;
font-weight:bold;
cursor:pointer;
transition:0.3s;
margin-right:8px;
}
button:hover{
background: rgba(255,255,255,0.2);
transform:scale(1.05);
}
input[type=range]{
accent-color:#ef4444;
}
.time{
color:white;
font-size:14px;
}
/* Pasan Title Old CSS */
.title{
font-family: 'Poppins', sans-serif;
font-size: 1.5rem;
font-weight: 700;
background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
text-align: center;
margin-bottom:10px;
}

/* subtitles */
video::cue{
font-size:22px;
color:white;
background:rgba(0,0,0,0.6);
padding:4px 8px;
border-radius:4px;
}

/* double tap seek */
.seek-indicator{
position:absolute;
top:50%;
transform:translateY(-50%);
font-size:40px;
color:white;
background:rgba(0,0,0,0.5);
padding:20px;
border-radius:50%;
opacity:0;
transition:0.3s;
pointer-events:none;
}
.seek-left{left:15%}
.seek-right{right:15%}
.seek-show{
opacity:1;
transform:translateY(-50%) scale(1.2);
}

/* fullscreen center */
.player:fullscreen,
.player:-webkit-full-screen{
width:100% !important;
height:100% !important;
border-radius:0 !important;
display:flex;
justify-content:center;
align-items:center;
}
.player:fullscreen video,
.player:-webkit-full-screen video{
width:auto;
height:100%;
max-width:100%;
max-height:100%;
object-fit:contain;
}

</style>
</head>
<body>

<div class="player" id="player">
<video id="video" src="{{ url_for('stream_video',url=video_url_encoded) }}" autoplay preload="auto"></video>
<input type="file" id="subtitleFile" accept=".srt" style="display:none">
<div class="loader" id="loader"></div>
<div class="seek-indicator seek-left" id="seekLeft">⏪ 10s</div>
<div class="seek-indicator seek-right" id="seekRight">10s ⏩</div>

<div class="controls" id="controls">
<div class="title">Pasan Ultra Player</div>

<div class="progress" id="progress">
<div class="buffered" id="buffered"></div>
<div class="played" id="played"></div>
</div>

<div class="row">
<div>
<button id="playPause">⏵</button>
<button id="mute">🔊</button>
<span class="time" id="current">0:00</span> /
<span class="time" id="duration">0:00</span>
</div>
<div>
<button id="ccBtn">CC</button>
<select id="speed">
<option value="0.5">0.5x</option>
<option value="1" selected>1x</option>
<option value="1.5">1.5x</option>
<option value="2">2x</option>
</select>
<button id="pip">📺</button>
<button id="fullscreen">⛶</button>
</div>
</div>
</div>

</div>

<script>
const video=document.getElementById("video")
const player=document.getElementById("player")
const loader=document.getElementById("loader")
const playPause=document.getElementById("playPause")
const progress=document.getElementById("progress")
const played=document.getElementById("played")
const buffered=document.getElementById("buffered")
const mute=document.getElementById("mute")
const speed=document.getElementById("speed")
const fullscreen=document.getElementById("fullscreen")
const pip=document.getElementById("pip")
const current=document.getElementById("current")
const duration=document.getElementById("duration")
const controls=document.getElementById("controls")
const ccBtn=document.getElementById("ccBtn")
const subtitleFile=document.getElementById("subtitleFile")
const seekLeft=document.getElementById("seekLeft")
const seekRight=document.getElementById("seekRight")

/* play/pause */
playPause.onclick=()=>{if(video.paused){video.play();playPause.textContent="❚❚"}else{video.pause();playPause.textContent="⏵"}}
/* loader */
video.onwaiting=()=>loader.style.display="block"
video.onplaying=()=>loader.style.display="none"
/* time update */
video.ontimeupdate=()=>{
if(video.duration){played.style.width=(video.currentTime/video.duration*100)+"%"}
current.textContent=format(video.currentTime)
}
/* duration */
video.onloadedmetadata=()=>duration.textContent=format(video.duration)
function format(t){const m=Math.floor(t/60);const s=Math.floor(t%60).toString().padStart(2,"0");return m+":"+s}

/* buffered progress */
video.onprogress=()=>{
if(video.buffered.length>0){
const bufferedEnd = video.buffered.end(video.buffered.length-1)
const duration = video.duration || 0
buffered.style.width = ((bufferedEnd/duration)*100)+"%"
}
}

/* progress click */
progress.onclick=e=>{const rect=progress.getBoundingClientRect(); video.currentTime=video.duration*((e.clientX-rect.left)/rect.width)}

/* mute */
mute.onclick=()=>{video.muted=!video.muted; mute.textContent=video.muted?"🔇":"🔊"}
/* speed */
speed.onchange=()=>video.playbackRate=speed.value
/* fullscreen */
fullscreen.onclick=()=>{if(!document.fullscreenElement){player.requestFullscreen()}else{document.exitFullscreen()}}
/* pip */
pip.onclick=async()=>{if(document.pictureInPictureElement){document.exitPictureInPicture()}else{await video.requestPictureInPicture()}}

/* subtitles */
ccBtn.onclick=()=>subtitleFile.click()
subtitleFile.onchange=function(){
const file=this.files[0]
if(!file) return
const reader=new FileReader()
reader.onload=function(){
const oldTrack=video.querySelector("track")
if(oldTrack) video.removeChild(oldTrack)
let srt=reader.result
let vtt="WEBVTT\n\n"+srt.replace(/\r+/g,'')
.replace(/(\d+)\n(\d{2}:\d{2}:\d{2}),(\d{3}) --> (\d{2}:\d{2}:\d{2}),(\d{3})/g,"$2.$3 --> $4.$5")
const blob=new Blob([vtt],{type:"text/vtt"})
const url=URL.createObjectURL(blob)
const track=document.createElement("track")
track.kind="subtitles"
track.label="English"
track.srclang="en"
track.src=url
track.default=true
video.appendChild(track)
}
reader.readAsText(file)
}

/* double tap seek */
let lastTap=0
player.addEventListener("click",e=>{
let now=Date.now()
if(now-lastTap<300){
if(e.clientX<window.innerWidth/2){video.currentTime=Math.max(0,video.currentTime-10);animate(seekLeft)}
else{video.currentTime=Math.min(video.duration,video.currentTime+10);animate(seekRight)}
}
lastTap=now
})
function animate(el){el.classList.add("seek-show"); setTimeout(()=>el.classList.remove("seek-show"),300)}

</script>
</body>
</html>
"""

# ================= ROUTES =================
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/player')
def player_page():
    url = request.args.get("url")
    if not url:
        return "No URL provided",400
    encoded=urllib.parse.quote(url)
    return render_template_string(VIDEO_PLAYER_HTML,video_url_encoded=encoded)

@app.route('/stream')
def stream_video():
    encoded=request.args.get("url")
    if not encoded:
        return "No URL provided",400
    video_url=urllib.parse.unquote(encoded)
    headers={'User-Agent':'Mozilla/5.0'}
    r=requests.get(video_url,headers=headers,stream=True)
    def generate():
        for chunk in r.iter_content(32768):
            if chunk: yield chunk
    return Response(generate(),status=r.status_code,headers=dict(r.headers))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
