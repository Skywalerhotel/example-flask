from flask import Flask, request, Response, render_template_string, stream_with_context
import requests
import urllib.parse

app = Flask(__name__)

# ================= HOME PAGE =================

HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Pro Stream Proxy</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{
    background:#0f172a;
    color:white;
    font-family:Arial;
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
}
form{
    background:#111827;
    padding:30px;
    border-radius:15px;
    box-shadow:0 10px 30px rgba(0,0,0,.5);
}
input[type=text]{
    padding:12px;
    width:300px;
    border:none;
    border-radius:8px;
    margin-bottom:15px;
}
input[type=submit]{
    padding:12px;
    width:100%;
    background:#ff0033;
    border:none;
    color:white;
    border-radius:8px;
    cursor:pointer;
}
</style>
</head>
<body>
<form method="get" action="/player">
<h2>Paste Direct Video URL</h2>
<input type="text" name="url" placeholder="https://example.com/video.mp4" required>
<br>
<input type="submit" value="Play Video">
</form>
</body>
</html>
"""

# ================= PLAYER PAGE =================

PLAYER_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pro Player</title>

<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Arial}
body{
    background:#0f172a;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    height:100vh;
    overflow:hidden;
}
.player{
    width:100%;
    max-width:1000px;
    height:60vh;
    position:relative;
    background:black;
    border-radius:20px;
    overflow:hidden;
}
video{
    width:100%;
    height:100%;
    object-fit:cover;
}
.controls{
    position:absolute;
    bottom:0;
    width:100%;
    padding:15px;
    background:linear-gradient(to top,rgba(0,0,0,.9),transparent);
}
.progress{
    width:100%;
    height:6px;
    background:#444;
    border-radius:5px;
    margin-bottom:10px;
    position:relative;
    cursor:pointer;
}
.buffered{
    position:absolute;
    height:100%;
    background:#777;
    width:0%;
}
.filled{
    position:absolute;
    height:100%;
    background:#ff0033;
    width:0%;
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
    margin-right:10px;
    cursor:pointer;
}
.seek-indicator{
    position:absolute;
    top:50%;
    transform:translateY(-50%);
    font-size:30px;
    background:rgba(0,0,0,.5);
    padding:15px;
    border-radius:50%;
    opacity:0;
    transition:.3s;
}
.left{left:20%}
.right{right:20%}
.show{opacity:1}
.footer{
    margin-top:15px;
    color:white;
    font-size:14px;
    opacity:.8;
}
</style>
</head>

<body>

<div class="player" id="player">

<video id="video" preload="auto" autoplay>
<source src="/stream?url={{url}}" type="video/mp4">
</video>

<div class="seek-indicator left" id="leftInd">⏪ 10s</div>
<div class="seek-indicator right" id="rightInd">10s ⏩</div>

<div class="controls">
<div class="progress" id="progress">
<div class="buffered" id="buffered"></div>
<div class="filled" id="filled"></div>
</div>

<div class="row">
<div>
<button id="play">▶</button>
<button onclick="seek(-60)">⏪60</button>
<button onclick="seek(60)">60⏩</button>
<span id="time">0:00 / 0:00</span>
</div>
<div>
<button onclick="fullscreen()">⛶</button>
</div>
</div>
</div>
</div>

<div class="footer">
developed by pasan Baggya 😉
</div>

<script>
const video=document.getElementById("video");
const play=document.getElementById("play");
const filled=document.getElementById("filled");
const buffered=document.getElementById("buffered");
const progress=document.getElementById("progress");
const time=document.getElementById("time");
const player=document.getElementById("player");

play.onclick=()=>{
if(video.paused){video.play();play.textContent="❚❚";}
else{video.pause();play.textContent="▶";}
};

video.ontimeupdate=()=>{
let percent=(video.currentTime/video.duration)*100;
filled.style.width=percent+"%";
time.textContent=format(video.currentTime)+" / "+format(video.duration);
};

video.onprogress=()=>{
if(video.buffered.length>0){
let end=video.buffered.end(video.buffered.length-1);
buffered.style.width=(end/video.duration)*100+"%";
}
};

function format(t){
let m=Math.floor(t/60);
let s=Math.floor(t%60).toString().padStart(2,"0");
return m+":"+s;
}

progress.onclick=e=>{
let rect=progress.getBoundingClientRect();
video.currentTime=((e.clientX-rect.left)/rect.width)*video.duration;
};

function seek(sec){video.currentTime+=sec;}

function fullscreen(){
if(!document.fullscreenElement)player.requestFullscreen();
else document.exitFullscreen();
}

/* DOUBLE TAP MOBILE */
let lastTap=0;
player.addEventListener("touchstart",function(e){
let now=Date.now();
if(now-lastTap<300){
let rect=player.getBoundingClientRect();
let x=e.touches[0].clientX-rect.left;
if(x<rect.width/2){video.currentTime-=10;show("leftInd");}
else{video.currentTime+=10;show("rightInd");}
}
lastTap=now;
});

player.addEventListener("dblclick",function(e){
let rect=player.getBoundingClientRect();
if(e.clientX-rect.left<rect.width/2){
video.currentTime-=10;show("leftInd");
}else{
video.currentTime+=10;show("rightInd");
}
});

function show(id){
let el=document.getElementById(id);
el.classList.add("show");
setTimeout(()=>el.classList.remove("show"),300);
}
</script>

</body>
</html>
"""

# ================= ROUTES =================

@app.route("/")
def home():
    return HOME_HTML

@app.route("/player")
def player():
    url = request.args.get("url")
    if not url:
        return "No URL provided", 400
    return render_template_string(PLAYER_HTML, url=urllib.parse.quote(url))

@app.route("/stream")
def stream():
    encoded = request.args.get("url")
    if not encoded:
        return "Missing URL", 400

    video_url = urllib.parse.unquote(encoded)
    range_header = request.headers.get("Range")

    headers = {"User-Agent": "Mozilla/5.0"}
    if range_header:
        headers["Range"] = range_header

    r = requests.get(video_url, headers=headers, stream=True)

    def generate():
        for chunk in r.iter_content(32768):
            if chunk:
                yield chunk

    response = Response(generate(), status=r.status_code)
    for h in ["Content-Type","Content-Length","Content-Range","Accept-Ranges"]:
        if h in r.headers:
            response.headers[h] = r.headers[h]

    return response

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
