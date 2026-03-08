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
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pasan Ultra Player</title>

<style>

/* ===== GLOBAL ===== */

body{
margin:0;
background:#0f172a;
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
}

video{
width:100%;
display:block;
}

/* ===== CENTER PLAY ===== */

.centerPlay{
position:absolute;
top:50%;
left:50%;
transform:translate(-50%,-50%);
font-size:70px;
cursor:pointer;
opacity:.8;
}

/* ===== LOADER ===== */

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

@keyframes spin{
100%{transform:rotate(360deg)}
}

/* ===== CONTROLS ===== */

.controls{
position:absolute;
bottom:0;
width:100%;
padding:15px;
background:linear-gradient(to top,rgba(0,0,0,.9),transparent);
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
}

/* ===== PROGRESS ===== */

.progress{
height:6px;
background:#374151;
border-radius:6px;
cursor:pointer;
margin-bottom:10px;
position:relative;
}

.played{
position:absolute;
height:100%;
background:#ef4444;
width:0%;
}

.buffered{
position:absolute;
height:100%;
background:#6b7280;
width:0%;
}

/* ===== SETTINGS ===== */

.settingsMenu{
position:absolute;
bottom:70px;
right:20px;
background:rgba(0,0,0,.95);
border-radius:10px;
display:none;
flex-direction:column;
min-width:160px;
}

.settingsMenu div{
padding:10px;
border-bottom:1px solid rgba(255,255,255,.1);
cursor:pointer;
}

.settingsMenu div:hover{
background:#ef4444;
}

/* ===== SUBTITLE ===== */

video::cue{
background:rgba(0,0,0,.7);
font-size:18px;
}

/* ===== SEEK INDICATOR ===== */

.seek{
position:absolute;
top:50%;
font-size:36px;
background:rgba(0,0,0,.6);
padding:20px;
border-radius:50%;
opacity:0;
transition:.25s;
}

.seek.left{left:15%}
.seek.right{right:15%}

.show{
opacity:1;
transform:scale(1.2);
}

</style>

</head>

<body>

<div class="player" id="player">

<video id="video"
src="{{ url_for('stream_video', url=video_url_encoded) }}"
preload="auto"></video>

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

<div class="settingsMenu" id="settingsMenu">

<div id="audioBtn">Audio</div>
<div id="subBtn">Subtitles</div>
<div id="speedBtn">Speed</div>

</div>

<input type="file" id="subFile" accept=".srt,.vtt" hidden>

</div>

<script>

/* ===== ELEMENTS ===== */

const video=document.getElementById("video")
const playBtn=document.getElementById("playBtn")
const centerPlay=document.getElementById("centerPlay")

const progress=document.getElementById("progress")
const played=document.getElementById("played")
const buffered=document.getElementById("buffered")

const settingsBtn=document.getElementById("settingsBtn")
const settingsMenu=document.getElementById("settingsMenu")

const pipBtn=document.getElementById("pipBtn")
const fsBtn=document.getElementById("fsBtn")

const muteBtn=document.getElementById("muteBtn")

/* ===== PLAY ===== */

function togglePlay(){

if(video.paused){
video.play()
centerPlay.style.display="none"
playBtn.textContent="❚❚"
}else{
video.pause()
centerPlay.style.display="block"
playBtn.textContent="▶"
}

}

playBtn.onclick=togglePlay
centerPlay.onclick=togglePlay

/* ===== TIME ===== */

video.ontimeupdate=()=>{
played.style.width=(video.currentTime/video.duration*100)+"%"
}

/* ===== SEEK ===== */

progress.onclick=e=>{
const rect=progress.getBoundingClientRect()
const x=e.clientX-rect.left
video.currentTime=(x/rect.width)*video.duration
}

/* ===== BUFFER ===== */

video.onprogress=()=>{
if(video.buffered.length>0){

let end=video.buffered.end(video.buffered.length-1)

buffered.style.width=(end/video.duration*100)+"%"

}
}

/* ===== VOLUME ===== */

muteBtn.onclick=()=>{
video.muted=!video.muted
muteBtn.textContent=video.muted?"🔇":"🔊"
}

/* ===== SETTINGS ===== */

settingsBtn.onclick=()=>{
settingsMenu.style.display=
settingsMenu.style.display==="flex"?"none":"flex"
}

/* ===== PIP ===== */

pipBtn.onclick=async()=>{
if(document.pictureInPictureElement)
document.exitPictureInPicture()
else
await video.requestPictureInPicture()
}

/* ===== FULLSCREEN ===== */

fsBtn.onclick=()=>{
if(!document.fullscreenElement)
player.requestFullscreen()
else
document.exitFullscreen()
}

/* ===== DOUBLE TAP SEEK ===== */

let lastTap=0

player.addEventListener("click",e=>{

let now=Date.now()
let gap=now-lastTap

if(gap<300){

let rect=player.getBoundingClientRect()
let x=e.clientX-rect.left

if(x<rect.width/2){
video.currentTime-=10
}else{
video.currentTime+=10
}

}

lastTap=now

})

/* ===== SRT SUPPORT ===== */

function srtToVtt(data){

let vtt="WEBVTT\n\n"

vtt+=data
.replace(/\r+/g,'')
.replace(/(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})/g,'$1\n$2')
.replace(/,/g,'.')

return vtt

}

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
