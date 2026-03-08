from flask import Flask, request, Response, render_template_string, stream_with_context, url_for
import requests, urllib.parse

app = Flask(__name__)

# ================= HOME PAGE =================

HOME_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stream Proxy</title>
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
.card{
    background:#111827;
    padding:30px;
    border-radius:16px;
    box-shadow:0 10px 30px rgba(0,0,0,0.4);
    width:90%;
    max-width:500px;
}
h2{color:white;margin-bottom:20px;text-align:center}
input{
    width:100%;
    padding:12px;
    border-radius:10px;
    border:none;
    margin-bottom:15px;
    background:#1f2937;
    color:white;
}
button{
    width:100%;
    padding:12px;
    border:none;
    border-radius:10px;
    background:#2563eb;
    color:white;
    font-weight:bold;
    cursor:pointer;
}
button:hover{background:#1d4ed8}
</style>
</head>
<body>
<div class="card">
<h2>Paste Video URL</h2>
<form method="get" action="{{ url_for('show_player') }}">
<input type="text" name="url" placeholder="https://example.com/video.mp4" required>
<button type="submit">Play Video</button>
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pasan Ultra Player PRO</title>

<style>
body{
margin:0;
background:#020617;
display:flex;
align-items:center;
justify-content:center;
height:100vh;
font-family:Arial;
color:white;
}
.player{
width:95%;
max-width:1100px;
background:black;
border-radius:18px;
overflow:hidden;
position:relative;
box-shadow:0 0 40px rgba(0,0,0,.6);
}
video{
width:100%;
display:block;
}
/* loader */
.loader{
position:absolute;
top:50%;
left:50%;
width:50px;
height:50px;
border:5px solid rgba(255,255,255,.2);
border-top:5px solid white;
border-radius:50%;
animation:spin 1s linear infinite;
display:none;
}
@keyframes spin{100%{transform:rotate(360deg)}}
/* controls */
.controls{
position:absolute;
bottom:0;
width:100%;
padding:15px;
background:linear-gradient(to top,rgba(0,0,0,.9),transparent);
transition:.3s;
}
.row{
display:flex;
justify-content:space-between;
align-items:center;
}
button{
background:none;
border:none;
color:white;
font-size:18px;
cursor:pointer;
padding:6px;
}
button:hover{color:#ef4444}
/* progress */
.progress{
height:6px;
background:#374151;
border-radius:6px;
cursor:pointer;
margin-bottom:10px;
position:relative;
}
.played{position:absolute;height:100%;background:#ef4444;width:0%;}
.buffered{position:absolute;height:100%;background:#6b7280;width:0%;}
/* center play */
.centerPlay{
position:absolute;
top:50%;
left:50%;
transform:translate(-50%,-50%);
font-size:70px;
cursor:pointer;
opacity:.85;
}
/* seek indicator */
.seek{
position:absolute;
top:50%;
font-size:36px;
background:rgba(0,0,0,.7);
padding:20px;
border-radius:50%;
opacity:0;
transition:.3s;
}
.seek.left{left:15%}
.seek.right{right:15%}
.show{opacity:1;transform:scale(1.2);}
/* settings */
.settingsMenu{
position:absolute;
bottom:80px;
right:20px;
background:rgba(0,0,0,.95);
border-radius:12px;
display:none;
flex-direction:column;
min-width:170px;
overflow:hidden;
}
.settingsMenu div{
padding:12px;
border-bottom:1px solid rgba(255,255,255,.08);
cursor:pointer;
}
.settingsMenu div:hover{background:#ef4444}
.speedMenu, .audioMenu{display:none;flex-direction:column;}
/* brightness overlay */
.brightness{
position:absolute;
top:0;
left:0;
width:100%;
height:100%;
background:black;
opacity:0;
pointer-events:none;
}
/* subtitle */
video::cue{background:rgba(0,0,0,.6);font-size:20px;}
</style>
</head>

<body>
<div class="player" id="player">

<video id="video" src="{{ url_for('stream_video', url=video_url_encoded) }}" preload="auto"></video>

<div class="brightness" id="brightness"></div>
<div class="centerPlay" id="centerPlay">▶</div>
<div class="loader" id="loader"></div>
<div class="seek left" id="seekL">⏪</div>
<div class="seek right" id="seekR">⏩</div>

<div class="controls" id="controls">
<div class="progress" id="progress">
<div class="buffered" id="buffered"></div>
<div class="played" id="played"></div>
</div>

<div class="row">
<div>
<button id="playBtn">▶</button>
<button id="muteBtn">🔊</button>
</div>

<div>
<button id="settingsBtn">⚙</button>
<button id="pipBtn">📺</button>
<button id="fsBtn">⛶</button>
</div>
</div>
</div>

<!-- SETTINGS MENU -->
<div class="settingsMenu" id="settingsMenu">
<div id="settingsBackBtn">← Back</div>
<div id="audioBtn">Audio</div>
<div id="subBtn">Load Subtitle</div>
<div id="speedBtn">Speed</div>

<div class="audioMenu" id="audioMenu"></div>
<div class="speedMenu" id="speedMenu">
<div data-speed="0.5">0.5x</div>
<div data-speed="1">1x</div>
<div data-speed="1.25">1.25x</div>
<div data-speed="1.5">1.5x</div>
<div data-speed="2">2x</div>
</div>
</div>

<input type="file" id="subFile" accept=".srt,.vtt" hidden>
</div>

<script>
const player=document.getElementById("player")
const video=document.getElementById("video")

const playBtn=document.getElementById("playBtn")
const centerPlay=document.getElementById("centerPlay")
const progress=document.getElementById("progress")
const played=document.getElementById("played")
const buffered=document.getElementById("buffered")
const settingsBtn=document.getElementById("settingsBtn")
const settingsMenu=document.getElementById("settingsMenu")
const settingsBackBtn=document.getElementById("settingsBackBtn")
const speedBtn=document.getElementById("speedBtn")
const speedMenu=document.getElementById("speedMenu")
const audioBtn=document.getElementById("audioBtn")
const audioMenu=document.getElementById("audioMenu")
const pipBtn=document.getElementById("pipBtn")
const fsBtn=document.getElementById("fsBtn")
const muteBtn=document.getElementById("muteBtn")
const loader=document.getElementById("loader")
const seekL=document.getElementById("seekL")
const seekR=document.getElementById("seekR")
const brightness=document.getElementById("brightness")
const subBtn=document.getElementById("subBtn")
const subFile=document.getElementById("subFile")
const controls=document.getElementById("controls")

/* Disable embedded subtitles by default */
for(let i=0;i<video.textTracks.length;i++){video.textTracks[i].mode="disabled"}

/* Auto-select first audio track */
if(video.audioTracks && video.audioTracks.length>0){
for(let i=0;i<video.audioTracks.length;i++){video.audioTracks[i].enabled=(i===0)}
}

/* Play/Pause */
function togglePlay(){
if(video.paused){video.play();playBtn.textContent="❚❚";centerPlay.style.display="none"}
else{video.pause();playBtn.textContent="▶";centerPlay.style.display="block"}
}
playBtn.onclick=togglePlay
centerPlay.onclick=togglePlay

/* Progress */
video.ontimeupdate=()=>{if(video.duration){played.style.width=(video.currentTime/video.duration*100)+"%"}}
progress.onclick=e=>{const rect=progress.getBoundingClientRect();const x=e.clientX-rect.left;video.currentTime=(x/rect.width)*video.duration}
video.onprogress=()=>{if(video.buffered.length>0 && video.duration){let end=video.buffered.end(video.buffered.length-1);buffered.style.width=(end/video.duration*100)+"%"}}

/* Loader */
video.onwaiting=()=>loader.style.display="block"
video.onplaying=()=>loader.style.display="none"

/* Mute */
muteBtn.onclick=()=>{video.muted=!video.muted;muteBtn.textContent=video.muted?"🔇":"🔊"}

/* Settings menu */
settingsBtn.onclick=()=>{settingsMenu.style.display=(settingsMenu.style.display==="flex"?"none":"flex")}
settingsBackBtn.onclick=()=>{settingsMenu.style.display="none";speedMenu.style.display="none";audioMenu.style.display="none"}

/* Speed menu */
speedBtn.onclick=()=>{audioMenu.style.display="none";speedMenu.style.display=(speedMenu.style.display==="flex"?"none":"flex")}
speedMenu.querySelectorAll("div").forEach(item=>{item.onclick=()=>{video.playbackRate=item.dataset.speed}})

/* Audio menu */
audioBtn.onclick=()=>{
speedMenu.style.display="none";audioMenu.style.display="flex";audioMenu.innerHTML=""
const tracks=video.audioTracks
if(tracks && tracks.length>0){
for(let i=0;i<tracks.length;i++){
let div=document.createElement("div")
div.textContent=tracks[i].label||("Track "+(i+1))
div.onclick=()=>{for(let j=0;j<tracks.length;j++){tracks[j].enabled=(i===j)}}
audioMenu.appendChild(div)
}
}else{let div=document.createElement("div");div.textContent="No multiple audio tracks found";audioMenu.appendChild(div)}
}

/* Subtitle loader */
subBtn.onclick=()=>subFile.click()
subFile.onchange=function(){
let file=this.files[0];if(!file)return
let reader=new FileReader()
reader.onload=function(){
let data=reader.result
if(file.name.endsWith(".srt")){data="WEBVTT\n\n"+data.replace(/,/g,'.')}
let blob=new Blob([data],{type:"text/vtt"})
let url=URL.createObjectURL(blob)
let track=document.createElement("track")
track.kind="subtitles";track.label="External";track.src=url;track.default=true
video.appendChild(track)
}
reader.readAsText(file)
}

/* Double tap seek */
let lastTap=0
player.addEventListener("touchend",function(e){
let now=Date.now()
if(now-lastTap<300){
let rect=player.getBoundingClientRect()
let x=e.changedTouches[0].clientX-rect.left
if(x<rect.width/2){video.currentTime-=10;seekL.classList.add("show");setTimeout(()=>seekL.classList.remove("show"),300)}
else{video.currentTime+=10;seekR.classList.add("show");setTimeout(()=>seekR.classList.remove("show"),300)}
}
lastTap=now
})

/* Keyboard shortcuts */
document.addEventListener("keydown",e=>{
if(e.code==="Space"){togglePlay()}
if(e.code==="ArrowRight"){video.currentTime+=10}
if(e.code==="ArrowLeft"){video.currentTime-=10}
})

/* Auto hide controls */
let hideTimer
player.onmousemove=()=>{controls.style.opacity=1;clearTimeout(hideTimer);hideTimer=setTimeout(()=>{controls.style.opacity=0},3000)}
</script>

</body>
</html>
"""

# ================= FLASK ROUTES =================

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/player')
def show_player():
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    encoded = urllib.parse.quote(url)
    return render_template_string(VIDEO_PLAYER_HTML, video_url_encoded=encoded)

@app.route('/stream')
def stream_video():
    encoded = request.args.get('url')
    if not encoded:
        return "Missing URL", 400

    video_url = urllib.parse.unquote(encoded)
    range_header = request.headers.get('Range')

    headers = {'User-Agent':'Mozilla/5.0'}
    if range_header:
        headers['Range'] = range_header

    upstream = requests.get(video_url, headers=headers, stream=True)

    def generate():
        for chunk in upstream.iter_content(chunk_size=32768):
            if chunk:
                yield chunk
        upstream.close()

    return Response(generate(), status=upstream.status_code, headers=dict(upstream.headers))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
