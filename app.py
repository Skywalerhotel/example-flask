from flask import Flask, request, Response, render_template_string
import requests, urllib.parse

app = Flask(__name__)

HOME = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pasan Ultra Player</title>
<style>
body{
margin:0;
height:100vh;
display:flex;
align-items:center;
justify-content:center;
background:#0f172a;
font-family:Arial;
}
.box{
background:#111827;
padding:30px;
border-radius:14px;
width:90%;
max-width:420px;
}
input{
width:100%;
padding:12px;
border-radius:8px;
border:none;
margin-bottom:10px;
background:#1f2937;
color:white;
}
button{
width:100%;
padding:12px;
border:none;
border-radius:8px;
background:#2563eb;
color:white;
font-weight:bold;
}
</style>
</head>
<body>

<div class="box">
<form action="/player">
<input name="url" placeholder="Paste MP4 / MKV URL" required>
<button>Play Video</button>
</form>
</div>

</body>
</html>
"""

PLAYER = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">

<style>

html,body{
margin:0;
height:100%;
background:black;
display:flex;
align-items:center;
justify-content:center;
}

.player{
width:95%;
max-width:1100px;
position:relative;
background:black;
display:flex;
align-items:center;
justify-content:center;
}

video{
width:100%;
max-height:100vh;
object-fit:contain;
}

.controls{
position:absolute;
bottom:0;
width:100%;
padding:12px;
background:linear-gradient(to top,rgba(0,0,0,.9),transparent);
transition:.3s;
}

button{
background:none;
border:none;
color:white;
font-size:18px;
margin-right:6px;
cursor:pointer;
}

.progress{
height:6px;
background:#374151;
margin-bottom:8px;
cursor:pointer;
position:relative;
}

.played{
position:absolute;
height:100%;
background:#ef4444;
width:0%;
}

.buffer{
position:absolute;
height:100%;
background:#6b7280;
width:0%;
}

.center{
position:absolute;
top:50%;
left:50%;
transform:translate(-50%,-50%);
font-size:60px;
color:white;
cursor:pointer;
}

.settingsMenu{
position:absolute;
bottom:70px;
right:15px;
background:rgba(0,0,0,.95);
border-radius:12px;
display:none;
flex-direction:column;
min-width:200px;
}

.settingsMenu div{
padding:10px;
border-bottom:1px solid rgba(255,255,255,.1);
cursor:pointer;
}

.settingsMenu div:hover{
background:#ef4444;
}

.audioMenu,.subMenu,.speedMenu{
display:none;
flex-direction:column;
}

</style>
</head>

<body>

<div class="player" id="player">

<video id="video"
src="/stream?url={{url}}"
crossorigin="anonymous"
preload="auto"></video>

<div class="center" id="center">▶</div>

<div class="controls" id="controls">

<div class="progress" id="progress">
<div class="buffer" id="buffer"></div>
<div class="played" id="played"></div>
</div>

<button id="play">▶</button>
<button id="back60">⏪60</button>
<button id="fwd60">60⏩</button>
<button id="mute">🔊</button>
<button id="settingsBtn">⚙</button>
<button id="pip">PiP</button>
<button id="fs">⛶</button>

</div>

<div class="settingsMenu" id="settingsMenu">

<div id="settingsBack">← Back</div>

<div id="audioOpen">Audio Tracks</div>

<div id="subOpen">Subtitles</div>

<div id="speedOpen">Playback Speed</div>

<div class="audioMenu" id="audioMenu"></div>

<div class="subMenu" id="subMenu"></div>

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

const video=document.getElementById("video")
const play=document.getElementById("play")
const center=document.getElementById("center")
const progress=document.getElementById("progress")
const played=document.getElementById("played")
const buffer=document.getElementById("buffer")
const mute=document.getElementById("mute")
const fs=document.getElementById("fs")
const pip=document.getElementById("pip")
const back60=document.getElementById("back60")
const fwd60=document.getElementById("fwd60")
const player=document.getElementById("player")

const settingsBtn=document.getElementById("settingsBtn")
const settingsMenu=document.getElementById("settingsMenu")
const settingsBack=document.getElementById("settingsBack")

const audioMenu=document.getElementById("audioMenu")
const audioOpen=document.getElementById("audioOpen")

const subMenu=document.getElementById("subMenu")
const subOpen=document.getElementById("subOpen")

const speedMenu=document.getElementById("speedMenu")
const speedOpen=document.getElementById("speedOpen")

const subFile=document.getElementById("subFile")

function toggle(){
if(video.paused){
video.play()
play.textContent="❚❚"
center.style.display="none"
}else{
video.pause()
play.textContent="▶"
center.style.display="block"
}
}

play.onclick=toggle
center.onclick=toggle

video.ontimeupdate=()=>{
if(video.duration)
played.style.width=(video.currentTime/video.duration*100)+"%"
}

video.onprogress=()=>{
if(video.buffered.length){
let end=video.buffered.end(video.buffered.length-1)
buffer.style.width=(end/video.duration*100)+"%"
}
}

progress.onclick=e=>{
let r=progress.getBoundingClientRect()
let x=e.clientX-r.left
video.currentTime=(x/r.width)*video.duration
}

back60.onclick=()=>video.currentTime-=60
fwd60.onclick=()=>video.currentTime+=60

mute.onclick=()=>{
video.muted=!video.muted
mute.textContent=video.muted?"🔇":"🔊"
}

pip.onclick=async()=>{
if(document.pictureInPictureElement)
document.exitPictureInPicture()
else
video.requestPictureInPicture()
}

fs.onclick=()=>{
if(!document.fullscreenElement)
player.requestFullscreen()
else
document.exitFullscreen()
}

settingsBtn.onclick=()=>{
settingsMenu.style.display="flex"
}

settingsBack.onclick=()=>{
settingsMenu.style.display="none"
audioMenu.style.display="none"
subMenu.style.display="none"
speedMenu.style.display="none"
}

audioOpen.onclick=()=>{

audioMenu.style.display="flex"
subMenu.style.display="none"
speedMenu.style.display="none"

audioMenu.innerHTML=""

const tracks=video.audioTracks

if(tracks && tracks.length){

for(let i=0;i<tracks.length;i++){

let div=document.createElement("div")
div.textContent=tracks[i].label || "Track "+(i+1)

div.onclick=()=>{

for(let j=0;j<tracks.length;j++)
tracks[j].enabled=(j===i)

}

audioMenu.appendChild(div)

}

}else{

audioMenu.innerHTML="<div>No audio tracks</div>"

}

}

subOpen.onclick=()=>{

subMenu.style.display="flex"
audioMenu.style.display="none"
speedMenu.style.display="none"

subMenu.innerHTML=""

let off=document.createElement("div")
off.textContent="Subtitles Off"

off.onclick=()=>{
for(let i=0;i<video.textTracks.length;i++)
video.textTracks[i].mode="disabled"
}

subMenu.appendChild(off)

for(let i=0;i<video.textTracks.length;i++){

let div=document.createElement("div")
div.textContent=video.textTracks[i].label || "Subtitle "+(i+1)

div.onclick=()=>{

for(let j=0;j<video.textTracks.length;j++)
video.textTracks[j].mode="disabled"

video.textTracks[i].mode="showing"

}

subMenu.appendChild(div)

}

let load=document.createElement("div")
load.textContent="Load External Subtitle"

load.onclick=()=>subFile.click()

subMenu.appendChild(load)

}

speedOpen.onclick=()=>{

speedMenu.style.display="flex"
audioMenu.style.display="none"
subMenu.style.display="none"

}

speedMenu.querySelectorAll("div").forEach(item=>{

item.onclick=()=>{

video.playbackRate=item.dataset.speed

}

})

subFile.onchange=function(){

let file=this.files[0]
if(!file)return

let reader=new FileReader()

reader.onload=function(){

let data=reader.result

if(file.name.endsWith(".srt"))
data="WEBVTT\\n\\n"+data.replace(/,/g,'.')

let blob=new Blob([data],{type:"text/vtt"})
let url=URL.createObjectURL(blob)

let track=document.createElement("track")
track.kind="subtitles"
track.src=url
track.default=true

video.appendChild(track)

}

reader.readAsText(file)

}

video.addEventListener("loadedmetadata",()=>{

if(video.audioTracks && video.audioTracks.length){

for(let i=0;i<video.audioTracks.length;i++)
video.audioTracks[i].enabled=(i===0)

}

for(let i=0;i<video.textTracks.length;i++)
video.textTracks[i].mode="disabled"

})

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return HOME

@app.route("/player")
def player():
    url=request.args.get("url")
    return render_template_string(PLAYER,url=urllib.parse.quote(url))

@app.route("/stream")
def stream():

    url=urllib.parse.unquote(request.args.get("url"))
    range_header=request.headers.get("Range")

    headers={"User-Agent":"Mozilla/5.0"}
    if range_header:
        headers["Range"]=range_header

    r=requests.get(url,headers=headers,stream=True)

    def generate():
        for chunk in r.iter_content(65536):
            yield chunk

    return Response(generate(),status=r.status_code,headers=dict(r.headers))

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000,threaded=True)
