<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Modern Video Player</title>

<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Arial}

body{
    background:#0f172a;
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
}

.player{
    position:relative;
    width:100%;
    max-width:900px;
    background:black;
    overflow:hidden;
}

video{
    width:100%;
    height:100%;
    display:block;
    background:black;
}

/* Loader */
.loader{
    position:absolute;
    top:50%;left:50%;
    transform:translate(-50%,-50%);
    border:4px solid rgba(255,255,255,.2);
    border-top:4px solid white;
    border-radius:50%;
    width:40px;height:40px;
    animation:spin 1s linear infinite;
    display:none;
}
@keyframes spin{100%{transform:translate(-50%,-50%) rotate(360deg)}}

/* Controls */
.controls{
    position:absolute;
    bottom:0;
    width:100%;
    background:linear-gradient(to top,rgba(0,0,0,.9),transparent);
    padding:10px;
    display:flex;
    align-items:center;
    gap:10px;
    opacity:1;
    transition:.3s;
}

.controls.hide{opacity:0}

button,select,input{
    background:none;
    border:none;
    color:white;
    font-size:16px;
}

button{cursor:pointer}

.progress{
    flex:1;
    height:6px;
    background:#444;
    border-radius:5px;
    cursor:pointer;
    position:relative;
}

.progress-filled{
    height:100%;
    width:0%;
    background:red;
    border-radius:5px;
}

.seek-indicator{
    position:absolute;
    top:50%;
    transform:translateY(-50%);
    font-size:35px;
    background:rgba(0,0,0,.5);
    padding:20px;
    border-radius:50%;
    opacity:0;
    transition:.3s;
    pointer-events:none;
}
.seek-indicator.left{left:15%}
.seek-indicator.right{right:15%}
.seek-show{opacity:1;transform:translateY(-50%) scale(1.2)}

.time{font-size:14px}

input[type=range]{
    width:80px;
}

.fullscreen{
    position:absolute;
    top:10px;
    right:10px;
    font-size:18px;
}
</style>
</head>

<body>

<div class="player" id="player">
    <video id="video" preload="auto">
        <source src="https://www.w3schools.com/html/mov_bbb.mp4" type="video/mp4">
    </video>

    <div class="loader" id="loader"></div>

    <!-- Double Tap Indicators -->
    <div class="seek-indicator left" id="seekLeft">⏪ 10s</div>
    <div class="seek-indicator right" id="seekRight">10s ⏩</div>

    <div class="controls" id="controls">
        <button id="play">▶</button>
        <button id="back60">⏪60</button>
        <button id="forward60">60⏩</button>

        <div class="progress" id="progress">
            <div class="progress-filled" id="progressFilled"></div>
        </div>

        <span class="time" id="time">0:00 / 0:00</span>

        <input type="range" id="volume" min="0" max="1" step="0.01">
        <select id="speed">
            <option value="1">1x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2x</option>
        </select>

        <button id="pip">📺</button>
        <button id="fullscreen">⛶</button>
    </div>
</div>

<script>
const video=document.getElementById("video");
const player=document.getElementById("player");
const playBtn=document.getElementById("play");
const progress=document.getElementById("progress");
const progressFilled=document.getElementById("progressFilled");
const timeDisplay=document.getElementById("time");
const volume=document.getElementById("volume");
const speed=document.getElementById("speed");
const loader=document.getElementById("loader");
const controls=document.getElementById("controls");
const seekLeft=document.getElementById("seekLeft");
const seekRight=document.getElementById("seekRight");

volume.value=1;

/* Play Pause */
playBtn.onclick=()=>{
    if(video.paused){video.play();playBtn.innerText="❚❚"}
    else{video.pause();playBtn.innerText="▶"}
};

/* Update Progress */
video.ontimeupdate=()=>{
    let percent=(video.currentTime/video.duration)*100;
    progressFilled.style.width=percent+"%";

    let cur=formatTime(video.currentTime);
    let dur=formatTime(video.duration);
    timeDisplay.innerText=cur+" / "+dur;
};

function formatTime(sec){
    let m=Math.floor(sec/60);
    let s=Math.floor(sec%60);
    if(s<10)s="0"+s;
    return m+":"+s;
}

/* Seek */
progress.onclick=(e)=>{
    let pos=e.offsetX/progress.offsetWidth;
    video.currentTime=pos*video.duration;
};

/* Volume */
volume.oninput=()=>video.volume=volume.value;

/* Speed */
speed.onchange=()=>video.playbackRate=speed.value;

/* Fullscreen */
document.getElementById("fullscreen").onclick=()=>{
    if(!document.fullscreenElement)player.requestFullscreen();
    else document.exitFullscreen();
};

/* PiP */
document.getElementById("pip").onclick=()=>{
    if(document.pictureInPictureElement)
        document.exitPictureInPicture();
    else video.requestPictureInPicture();
};

/* 60s Seek */
document.getElementById("forward60").onclick=()=>{
    video.currentTime=Math.min(video.duration,video.currentTime+60);
};
document.getElementById("back60").onclick=()=>{
    video.currentTime=Math.max(0,video.currentTime-60);
};

/* Loader */
video.onwaiting=()=>loader.style.display="block";
video.onplaying=()=>loader.style.display="none";

/* Auto Hide Controls */
let hideTimeout;
player.onmousemove=()=>{
    controls.classList.remove("hide");
    clearTimeout(hideTimeout);
    hideTimeout=setTimeout(()=>controls.classList.add("hide"),2000);
};

/* Double Tap 10s */
let lastTap=0;
player.addEventListener("click",(e)=>{
    let now=Date.now();
    if(now-lastTap<300){
        const rect=player.getBoundingClientRect();
        const x=e.clientX-rect.left;
        if(x<rect.width/2){
            video.currentTime=Math.max(0,video.currentTime-10);
            animateSeek(seekLeft);
        }else{
            video.currentTime=Math.min(video.duration,video.currentTime+10);
            animateSeek(seekRight);
        }
    }
    lastTap=now;
});

function animateSeek(el){
    el.classList.add("seek-show");
    setTimeout(()=>el.classList.remove("seek-show"),300);
}

/* Keyboard */
document.addEventListener("keydown",(e)=>{
    if(e.code==="Space"){e.preventDefault();playBtn.click();}
    if(e.code==="ArrowRight")video.currentTime+=10;
    if(e.code==="ArrowLeft")video.currentTime-=10;
});
</script>

</body>
</html>
