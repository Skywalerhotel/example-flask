from flask import Flask, request, Response, render_template_string, url_for
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
<title>ULTRA PLAYER PRO v6</title>
<style>
body{margin:0; background:#0f172a; display:flex; justify-content:center; align-items:center; height:100vh; font-family:Arial;}
.player{width:95%; max-width:1000px; background:black; border-radius:18px; overflow:hidden; position:relative;}
video{width:100%; height:auto; object-fit:contain;}
.loader{position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:55px; height:55px; border:5px solid rgba(255,255,255,0.2); border-top:5px solid white; border-radius:50%; animation:spin 1s linear infinite; display:none;}
@keyframes spin{100%{transform:translate(-50%,-50%) rotate(360deg)}}
.controls{position:absolute; bottom:0; width:100%; background:linear-gradient(to top,rgba(0,0,0,0.9),transparent); padding:15px; box-sizing:border-box; transition:opacity 0.3s;}
.hide{opacity:0}
.progress{height:6px; background:#374151; border-radius:5px; cursor:pointer; position:relative; margin-bottom:12px;}
.buffered{position:absolute; height:100%; background:#6b7280; width:0%; border-radius:5px;}
.played{position:absolute; height:100%; background:#ef4444; width:0%; border-radius:5px;}
.row{display:flex; justify-content:space-between; align-items:center;}
.left,.right{display:flex; align-items:center; gap:12px;}
button,select{background:none; border:none; color:white; font-size:16px; cursor:pointer;}
input[type=range]{width:80px;}
.time{font-size:14px; color:white;}
.player:fullscreen{width:100% !important; height:100% !important; border-radius:0 !important;}
.player:fullscreen video{width:100%; height:100%;}
.seek-indicator{position:absolute; top:50%; transform:translateY(-50%); font-size:38px; color:white; background:rgba(0,0,0,0.5); padding:20px; border-radius:50%; opacity:0; transition:0.25s ease; pointer-events:none;}
.seek-indicator.left{ left:15%; }
.seek-indicator.right{ right:15%; }
.seek-show{opacity:1; transform:translateY(-50%) scale(1.2);}
.settingsMenu{position:absolute; bottom:70px; right:15px; background:rgba(0,0,0,.95); border-radius:12px; display:none; flex-direction:column; min-width:200px; color:white;}
.settingsMenu div{padding:10px; border-bottom:1px solid rgba(255,255,255,.15); cursor:pointer; color:white; font-size:16px;}
.settingsMenu div:hover{background:#ef4444;}
.audioMenu,.subMenu,.speedMenu{display:none; flex-direction:column;}
</style>
</head>
<body>

<div class="player" id="player">
<video id="video"
src="{{ url_for('stream_video', url=video_url_encoded) }}"
autoplay preload="auto"></video>

<div class="loader" id="loader"></div>
<div class="seek-indicator left" id="seekLeft">⏪ 10s</div>
<div class="seek-indicator right" id="seekRight">10s ⏩</div>

<div class="controls" id="controls">
<div class="row left">
<button id="playPause">▶</button>
<button id="mute">🔊</button>
<input type="range" id="volume" min="0" max="1" step="0.05" value="1">
<span class="time" id="current">0:00</span> / 
<span class="time" id="duration">0:00</span>
</div>
<div class="progress" id="progress">
<div class="buffered" id="buffered"></div>
<div class="played" id="played"></div>
</div>
<div class="row right">
<select id="speed">
<option value="0.5">0.5x</option>
<option value="1" selected>1x</option>
<option value="1.25">1.25x</option>
<option value="1.5">1.5x</option>
<option value="2">2x</option>
</select>
<button id="settingsBtn">⚙</button>
<button id="pip">📺</button>
<button id="fullscreen">⛶</button>
</div>
</div>

<div class="settingsMenu" id="settingsMenu">
<div id="settingsBack">← Back</div>
<div id="audioBtn">Audio Tracks</div>
<div id="subBtn">Subtitles</div>
<div id="speedBtn">Speed</div>

<div class="audioMenu" id="audioMenu"></div>
<div class="subMenu" id="subMenu"></div>
<div class="speedMenu" id="speedMenu"></div>

<input type="file" id="subFile" accept=".srt,.vtt" hidden>
</div>

<script>
const video=document.getElementById("video");
const player=document.getElementById("player");
const loader=document.getElementById("loader");
const controls=document.getElementById("controls");
const progress=document.getElementById("progress");
const played=document.getElementById("played");
const buffered=document.getElementById("buffered");
const playPause=document.getElementById("playPause");
const mute=document.getElementById("mute");
const volume=document.getElementById("volume");
const speed=document.getElementById("speed");
const fullscreen=document.getElementById("fullscreen");
const pip=document.getElementById("pip");
const current=document.getElementById("current");
const duration=document.getElementById("duration");
const seekLeft=document.getElementById("seekLeft");
const seekRight=document.getElementById("seekRight");

const settingsBtn=document.getElementById("settingsBtn");
const settingsMenu=document.getElementById("settingsMenu");
const settingsBack=document.getElementById("settingsBack");
const audioBtn=document.getElementById("audioBtn");
const subBtn=document.getElementById("subBtn");
const speedBtn=document.getElementById("speedBtn");
const audioMenu=document.getElementById("audioMenu");
const subMenu=document.getElementById("subMenu");
const speedMenu=document.getElementById("speedMenu");
const subFile=document.getElementById("subFile");

let hideTimer;

/* Play/Pause */
playPause.onclick=()=>{video.paused?video.play(),playPause.textContent="❚❚":video.pause(),playPause.textContent="▶";};
video.onplay=()=>showControls();

/* Volume */
volume.oninput=()=>video.volume=volume.value;
mute.onclick=()=>{video.muted=!video.muted;mute.textContent=video.muted?"🔇":"🔊";};

/* Speed */
speed.onchange=()=>video.playbackRate=speed.value;

/* Fullscreen */
fullscreen.onclick=()=>!document.fullscreenElement?player.requestFullscreen():document.exitFullscreen();

/* PiP */
pip.onclick=async()=>document.pictureInPictureElement?document.exitPictureInPicture():await video.requestPictureInPicture();

/* Loader */
video.onwaiting=()=>loader.style.display="block";
video.onplaying=()=>loader.style.display="none";

/* Time */
video.ontimeupdate=()=>{
played.style.width=(video.currentTime/video.duration*100)+"%";
current.textContent=format(video.currentTime);
};
video.onloadedmetadata=()=>duration.textContent=format(video.duration);
function format(t){const m=Math.floor(t/60); const s=Math.floor(t%60).toString().padStart(2,"0"); return m+":"+s;}

/* Buffered */
video.onprogress=()=>{
if(video.buffered.length>0){buffered.style.width=(video.buffered.end(video.buffered.length-1)/video.duration*100)+"%";}
};

/* Progress Click */
progress.onclick=(e)=>{const r=progress.getBoundingClientRect();video.currentTime=(e.clientX-r.left)/r.width*video.duration;};

/* Auto-hide controls */
function showControls(){controls.classList.remove("hide");clearTimeout(hideTimer);hideTimer=setTimeout(()=>controls.classList.add("hide"),3000);}
player.onmousemove=showControls;
player.ontouchstart=showControls;

/* ===== Double Tap 10s ===== */
let lastTap=0;
player.addEventListener("click",(e)=>{
let now=Date.now();
let tapGap=now-lastTap;
if(tapGap<300&&tapGap>0){
let rect=player.getBoundingClientRect();let x=e.clientX-rect.left;
if(x<rect.width/2){video.currentTime=Math.max(0,video.currentTime-10);animateSeek(seekLeft);}
else{video.currentTime=Math.min(video.duration,video.currentTime+10);animateSeek(seekRight);}
video.play();
}
lastTap=now;
});
function animateSeek(el){el.classList.add("seek-show");setTimeout(()=>el.classList.remove("seek-show"),350);}

/* ===== Settings Menu ===== */
settingsBtn.onclick=()=>settingsMenu.style.display="flex";
settingsBack.onclick=()=>{
settingsMenu.style.display="none";
audioMenu.style.display=subMenu.style.display=speedMenu.style.display="none";
};

/* Audio Tracks */
audioBtn.onclick=()=>{
audioMenu.style.display="flex";subMenu.style.display=speedMenu.style.display="none";audioMenu.innerHTML="";
const tracks=video.audioTracks;if(tracks&&tracks.length){
for(let i=0;i<tracks.length;i++){let div=document.createElement("div");div.textContent=tracks[i].label||"Track "+(i+1);div.onclick=()=>{for(let j=0;j<tracks.length;j++)tracks[j].enabled=(i===j);};audioMenu.appendChild(div);}}else{audioMenu.innerHTML="<div>No audio tracks</div>";}};

/* Subtitles */
subBtn.onclick=()=>{
subMenu.style.display="flex";audioMenu.style.display=speedMenu.style.display="none";subMenu.innerHTML="";
let off=document.createElement("div");off.textContent="Subtitles Off";off.onclick=()=>{for(let i=0;i<video.textTracks.length;i++)video.textTracks[i].mode="disabled";};subMenu.appendChild(off);
for(let i=0;i<video.textTracks.length;i++){let div=document.createElement("div");div.textContent=video.textTracks[i].label||"Subtitle "+(i+1);div.onclick=()=>{for(let j=0;j<video.textTracks.length;j++)video.textTracks[j].mode="disabled";video.textTracks[i].mode="showing";};subMenu.appendChild(div);}
let load=document.createElement("div");load.textContent="Load External Subtitle";load.onclick=()=>subFile.click();subMenu.appendChild(load);
};

/* Load external subtitle */
subFile.onchange=function(){
let file=this.files[0];if(!file)return;
let reader=new FileReader();
reader.onload=function(){let data=reader.result;if(file.name.endsWith(".srt"))data="WEBVTT\\n\\n"+data.replace(/,/g,'.');let blob=new Blob([data],{type:"text/vtt"});let url=URL.createObjectURL(blob);let track=document.createElement("track");track.kind="subtitles";track.src=url;track.default=true;video.appendChild(track);};reader.readAsText(file);
};

/* Default tracks setup */
video.addEventListener("loadedmetadata",()=>{
if(video.audioTracks&&video.audioTracks.length){for(let i=0;i<video.audioTracks.length;i++)video.audioTracks[i].enabled=(i===0);}
for(let i=0;i<video.textTracks.length;i++)video.textTracks[i].mode="disabled";
});

/* Swipe gestures: volume & brightness */
let startY,startX,volumeStart,brightnessStart;
player.addEventListener("touchstart",(e)=>{startY=e.touches[0].clientY;startX=e.touches[0].clientX;volumeStart=video.volume;brightnessStart=player.style.filter?parseFloat(player.style.filter.replace("brightness(","").replace(")","")):1;});
player.addEventListener("touchmove",(e)=>{let dy=startY-e.touches[0].clientY;let dx=e.touches[0].clientX-startX;let rect=player.getBoundingClientRect();if(startX<rect.width/2){let b=Math.min(Math.max(brightnessStart+dy/300,0),2);player.style.filter="brightness("+b+")";}else{let v=Math.min(Math.max(volumeStart+dy/300,0),1);video.volume=v;volume.value=v;}});
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
