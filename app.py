from flask import Flask, request, Response, render_template_string
import requests, urllib.parse

app = Flask(__name__)

HOME = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pasan Ultra Player</title>
<style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#0f172a;font-family:Arial}
.box{background:#111827;padding:30px;border-radius:14px;width:90%;max-width:420px}
input{width:100%;padding:12px;border-radius:8px;border:none;margin-bottom:10px;background:#1f2937;color:white}
button{width:100%;padding:12px;border:none;border-radius:8px;background:#2563eb;color:white;font-weight:bold}
</style>
</head>
<body>
<div class="box">
<form action="/player">
<input name="url" placeholder="Paste MP4 / MKV URL" required>
<button>PLAY VIDEO</button>
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
<title>Pasan Ultra Player</title>

<style>

body{
margin:0;
background:black;
display:flex;
align-items:center;
justify-content:center;
height:100vh;
font-family:Arial;
}

.player{
width:95%;
max-width:1100px;
position:relative;
background:black;
}

video{
width:100%;
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

.seek{
position:absolute;
top:50%;
font-size:34px;
background:rgba(0,0,0,.7);
padding:20px;
border-radius:50%;
opacity:0;
}

.seek.show{
opacity:1;
transform:scale(1.3);
}

.left{left:15%}
.right{right:15%}

.gestureInfo{
position:absolute;
top:50%;
left:50%;
transform:translate(-50%,-50%);
background:rgba(0,0,0,.7);
padding:12px 16px;
border-radius:10px;
display:none;
color:white;
}

video::cue{
font-size:20px;
background:rgba(0,0,0,.6);
}

</style>
</head>

<body>

<div class="player" id="player">

<video id="video" crossorigin="anonymous"
src="/stream?url={{url}}" preload="auto"></video>

<div class="brightness" id="brightness"></div>

<div class="center" id="center">▶</div>

<div class="seek left" id="seekL">-10s</div>
<div class="seek right" id="seekR">+10s</div>

<div class="gestureInfo" id="gestureInfo"></div>

<div class="controls" id="controls">

<div class="progress" id="progress">
<div class="buffer" id="buffer"></div>
<div class="played" id="played"></div>
</div>

<button id="play">▶</button>
<button id="back">⏪60</button>
<button id="fwd">60⏩</button>
<button id="mute">🔊</button>
<button id="speed">1x</button>
<button id="pip">PiP</button>
<button id="fs">⛶</button>
<button id="sub">SUB</button>

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
const pip=document.getElementById("pip")
const fs=document.getElementById("fs")
const back=document.getElementById("back")
const fwd=document.getElementById("fwd")
const speed=document.getElementById("speed")
const sub=document.getElementById("sub")
const subFile=document.getElementById("subFile")
const player=document.getElementById("player")
const brightness=document.getElementById("brightness")
const seekL=document.getElementById("seekL")
const seekR=document.getElementById("seekR")
const gestureInfo=document.getElementById("gestureInfo")
const controls=document.getElementById("controls")

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
if(video.buffered.length && video.duration){
let end=video.buffered.end(video.buffered.length-1)
buffer.style.width=(end/video.duration*100)+"%"
}
}

progress.onclick=e=>{
let r=progress.getBoundingClientRect()
let x=e.clientX-r.left
video.currentTime=(x/r.width)*video.duration
}

mute.onclick=()=>{
video.muted=!video.muted
mute.textContent=video.muted?"🔇":"🔊"
}

back.onclick=()=>video.currentTime=Math.max(0,video.currentTime-60)
fwd.onclick=()=>video.currentTime=Math.min(video.duration,video.currentTime+60)

const speeds=[0.5,1,1.25,1.5,2]

speed.onclick=()=>{
let i=speeds.indexOf(video.playbackRate)
video.playbackRate=speeds[(i+1)%speeds.length]
speed.textContent=video.playbackRate+"x"
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

sub.onclick=()=>subFile.click()

subFile.onchange=function(){
let f=this.files[0]
if(!f)return
let r=new FileReader()
r.onload=function(){
let d=r.result
if(f.name.endsWith(".srt"))
d="WEBVTT\\n\\n"+d.replace(/,/g,'.')
let blob=new Blob([d],{type:"text/vtt"})
let url=URL.createObjectURL(blob)
let track=document.createElement("track")
track.kind="subtitles"
track.src=url
track.default=true
video.appendChild(track)
}
r.readAsText(f)
}

/* double tap 10s */

let lastTap=0

player.addEventListener("touchend",e=>{

let now=Date.now()

if(now-lastTap<300){

let rect=player.getBoundingClientRect()
let x=e.changedTouches[0].clientX-rect.left

if(x<rect.width/2){
video.currentTime-=10
seekL.classList.add("show")
setTimeout(()=>seekL.classList.remove("show"),300)
}else{
video.currentTime+=10
seekR.classList.add("show")
setTimeout(()=>seekR.classList.remove("show"),300)
}

}

lastTap=now

})

/* gestures */

let startX,startY,startVol,startBright,startTime

player.addEventListener("touchstart",e=>{
startX=e.touches[0].clientX
startY=e.touches[0].clientY
startVol=video.volume
startBright=parseFloat(brightness.style.opacity)||0
startTime=video.currentTime
})

player.addEventListener("touchmove",e=>{

let x=e.touches[0].clientX
let y=e.touches[0].clientY
let dx=x-startX
let dy=y-startY

if(Math.abs(dx)>Math.abs(dy)){
let seek=startTime+(dx*0.1)
video.currentTime=Math.max(0,Math.min(video.duration,seek))
gestureInfo.style.display="block"
gestureInfo.textContent="Seek "+Math.floor(video.currentTime)+"s"
}else{

if(startX<player.clientWidth/2){
let b=startBright+(dy*-0.003)
b=Math.max(0,Math.min(.7,b))
brightness.style.opacity=b
gestureInfo.style.display="block"
gestureInfo.textContent="Brightness "+Math.floor(b*100)+"%"
}else{
let v=startVol+(dy*-0.003)
v=Math.max(0,Math.min(1,v))
video.volume=v
gestureInfo.style.display="block"
gestureInfo.textContent="Volume "+Math.floor(v*100)+"%"
}

}

})

player.addEventListener("touchend",()=>{
setTimeout(()=>gestureInfo.style.display="none",400)
})

/* keyboard */

document.addEventListener("keydown",e=>{
if(e.code==="Space")toggle()
if(e.code==="ArrowRight")video.currentTime+=10
if(e.code==="ArrowLeft")video.currentTime-=10
})

/* auto hide controls */

let hideTimer

player.onmousemove=()=>{
controls.style.opacity=1
clearTimeout(hideTimer)
hideTimer=setTimeout(()=>controls.style.opacity=0,3000)
}

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
