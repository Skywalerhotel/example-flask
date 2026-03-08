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
<title>Pasan Video Player </title>

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

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
}

video{
width:100%;
height:auto;
display:block;
background:black;
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

/* controls */

.controls{
position:absolute;
bottom:0;
width:100%;
background:linear-gradient(to top,rgba(0,0,0,0.9),transparent);
padding:15px;
box-sizing:border-box;
}

.progress{
height:6px;
background:#374151;
border-radius:5px;
cursor:pointer;
position:relative;
margin-bottom:12px;
}

.buffered{
position:absolute;
height:100%;
background:#6b7280;
width:0%;
}

.played{
position:absolute;
height:100%;
background:#ef4444;
width:0%;
}

.row{
display:flex;
justify-content:space-between;
align-items:center;
}

button,select{
background:none;
border:none;
color:white;
font-size:16px;
cursor:pointer;
}

input[type=range]{
width:80px;
}

.time{
font-size:14px;
color:white;
}

/* title */

.title{
font-family: 'Poppins', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    position: relative;
}

/* subtitle styling */

video::cue{
font-size:20px;
color:white;
background:rgba(0,0,0,0.6);
padding:4px 8px;
border-radius:4px;
}

/* settings panel */

.settings{
position:absolute;
right:10px;
bottom:80px;
background:#111827;
color:white;
padding:12px;
border-radius:10px;
display:none;
}

.settings button{
display:block;
margin:5px 0;
}

</style>
</head>

<body>

<div class="player" id="player">

<video id="video"
src="{{ url_for('stream_video', url=video_url_encoded) }}"
autoplay preload="auto"></video>

<input type="file" id="subtitleFile" accept=".srt" style="display:none">

<div class="loader" id="loader"></div>

<div class="controls">

<div class="title">Pasan Video Player</div>

<div class="progress" id="progress">
<div class="buffered" id="buffered"></div>
<div class="played" id="played"></div>
</div>

<div class="row">

<div class="left">

<button id="playPause">▶</button>

<button id="mute">🔊</button>

<input type="range" id="volume" min="0" max="1" step="0.05" value="1">

<span class="time" id="current">0:00</span> /
<span class="time" id="duration">0:00</span>

</div>

<div class="right">

<button id="ccBtn">CC</button>

<button id="audioBtn">🎵</button>

<select id="speed">
<option value="0.5">0.5x</option>
<option value="1" selected>1x</option>
<option value="1.5">1.5x</option>
<option value="2">2x</option>
</select>

<button id="pip">📺</button>

<button id="fullscreen">⛶</button>

<button id="settingsBtn">⚙</button>

</div>

</div>

</div>

<div class="settings" id="settings">

<button id="loadSubtitle">Load Subtitle</button>

<button id="toggleSubtitle">Toggle Subtitle</button>

</div>

</div>

<script>

const video=document.getElementById("video")
const playPause=document.getElementById("playPause")
const loader=document.getElementById("loader")
const progress=document.getElementById("progress")
const played=document.getElementById("played")
const buffered=document.getElementById("buffered")
const volume=document.getElementById("volume")
const mute=document.getElementById("mute")
const speed=document.getElementById("speed")
const fullscreen=document.getElementById("fullscreen")
const pip=document.getElementById("pip")
const current=document.getElementById("current")
const duration=document.getElementById("duration")

const settingsBtn=document.getElementById("settingsBtn")
const settings=document.getElementById("settings")

const subtitleFile=document.getElementById("subtitleFile")
const loadSubtitle=document.getElementById("loadSubtitle")
const toggleSubtitle=document.getElementById("toggleSubtitle")

/* play pause */

playPause.onclick=()=>{

if(video.paused){
video.play()
playPause.textContent="❚❚"
}
else{
video.pause()
playPause.textContent="▶"
}

}

/* loader */

video.onwaiting=()=>loader.style.display="block"
video.onplaying=()=>loader.style.display="none"

/* time update */

video.ontimeupdate=()=>{

played.style.width=(video.currentTime/video.duration*100)+"%"

current.textContent=format(video.currentTime)

}

video.onloadedmetadata=()=>duration.textContent=format(video.duration)

function format(t){

const m=Math.floor(t/60)

const s=Math.floor(t%60).toString().padStart(2,"0")

return m+":"+s

}

/* buffered */

video.onprogress=()=>{

if(video.buffered.length>0){

const end=video.buffered.end(video.buffered.length-1)

buffered.style.width=(end/video.duration*100)+"%"

}

}

/* seek */

progress.onclick=(e)=>{

const rect=progress.getBoundingClientRect()

const x=e.clientX-rect.left

video.currentTime=(x/rect.width)*video.duration

}

/* volume */

volume.oninput=()=>video.volume=volume.value

mute.onclick=()=>{

video.muted=!video.muted

mute.textContent=video.muted?"🔇":"🔊"

}

/* speed */

speed.onchange=()=>video.playbackRate=speed.value

/* fullscreen */

fullscreen.onclick=()=>{

if(!document.fullscreenElement)
player.requestFullscreen()
else
document.exitFullscreen()

}

/* pip */

pip.onclick=async()=>{

if(document.pictureInPictureElement)
document.exitPictureInPicture()
else
await video.requestPictureInPicture()

}

/* settings */

settingsBtn.onclick=()=>{

settings.style.display=
settings.style.display=="block"?"none":"block"

}

/* subtitle load */

loadSubtitle.onclick=()=>subtitleFile.click()

subtitleFile.onchange=function(){

const file=this.files[0]

const reader=new FileReader()

reader.onload=function(){

const srt=reader.result

const vtt="WEBVTT\n\n"+srt
.replace(/\r+/g,"")
.replace(/(\d+)\n(\d{2}:\d{2}:\d{2}),/g,"$1\n$2.")
.replace(/ --> (\d{2}:\d{2}:\d{2}),/g," --> $1.")

const blob=new Blob([vtt],{type:"text/vtt"})

const url=URL.createObjectURL(blob)

const track=document.createElement("track")

track.kind="subtitles"
track.src=url
track.default=true

video.appendChild(track)

}

reader.readAsText(file)

}

/* toggle subtitle */

toggleSubtitle.onclick=()=>{

const tracks=video.textTracks

for(let i=0;i<tracks.length;i++){

tracks[i].mode=
tracks[i].mode==="showing"?"hidden":"showing"

}

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
