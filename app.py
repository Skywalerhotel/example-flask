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
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>pasan Video Player</title>
<style>
  * { box-sizing: border-box; user-select: none; -webkit-user-select: none; }
  body {
    margin: 0;
    background: #0f0f0f;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    font-family: Roboto, Arial, sans-serif;
    color: #fff;
  }

  .player {
    width: 96%;
    max-width: 1080px;
    aspect-ratio: 16 / 9;
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.65);
  }

  video {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: contain;
    background: #000;
  }

  /* Top Title Gradient */
  .top-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    padding: 14px 18px;
    background: linear-gradient(to bottom, rgba(0,0,0,0.75), transparent);
    font-size: 15px;
    font-weight: 500;
    transition: opacity 0.25s;
    pointer-events: none;
    z-index: 3;
  }

  /* Loader */
  .loader {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 52px; height: 52px;
    border: 4px solid rgba(255,255,255,0.2);
    border-top: 4px solid #ff0000;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
    display: none;
    z-index: 4;
    pointer-events: none;
  }
  @keyframes spin { 100% { transform: translate(-50%, -50%) rotate(360deg); } }

  /* 2x Hold Speed Pill */
  .speed-pill {
    position: absolute;
    top: 18px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.78);
    color: #fff;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
    opacity: 0;
    transition: opacity 0.15s;
    pointer-events: none;
    z-index: 5;
  }
  .speed-pill.show { opacity: 1; }

  /* Double Tap Seek Indicator */
  .seek-indicator {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 20px;
    font-weight: 600;
    color: #fff;
    background: rgba(0, 0, 0, 0.55);
    padding: 16px 22px;
    border-radius: 40px;
    opacity: 0;
    transition: opacity 0.2s ease, transform 0.2s ease;
    pointer-events: none;
    z-index: 4;
  }
  .seek-indicator.left { left: 12%; }
  .seek-indicator.right { right: 12%; }
  .seek-show { opacity: 1; transform: translateY(-50%) scale(1.08); }

  /* Bottom Controls */
  .controls {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.45) 60%, transparent 100%);
    padding: 24px 14px 10px;
    transition: opacity 0.25s;
    z-index: 6;
  }
  .hide { opacity: 0; pointer-events: none; }

  /* YouTube Seek Bar */
  .progress-wrap {
    position: relative;
    height: 16px;
    display: flex;
    align-items: center;
    cursor: pointer;
    margin-bottom: 6px;
  }
  .progress {
    position: relative;
    width: 100%;
    height: 3.5px;
    background: rgba(255, 255, 255, 0.25);
    transition: height 0.12s ease;
  }
  .progress-wrap:hover .progress,
  .progress-wrap.dragging .progress {
    height: 5.5px;
  }
  .buffered {
    position: absolute;
    top: 0; left: 0; height: 100%;
    background: rgba(255, 255, 255, 0.45);
    width: 0%;
  }
  .played {
    position: absolute;
    top: 0; left: 0; height: 100%;
    background: #ff0000;
    width: 0%;
  }
  .scrubber {
    position: absolute;
    top: 50%;
    left: 0%;
    width: 13px; height: 13px;
    background: #ff0000;
    border-radius: 50%;
    transform: translate(-50%, -50%) scale(0);
    transition: transform 0.12s ease;
    pointer-events: none;
  }
  .progress-wrap:hover .scrubber,
  .progress-wrap.dragging .scrubber {
    transform: translate(-50%, -50%) scale(1);
  }
  .hover-time {
    position: absolute;
    bottom: 20px;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.85);
    color: #fff;
    font-size: 12px;
    padding: 3px 7px;
    border-radius: 4px;
    display: none;
    pointer-events: none;
  }

  /* Control Buttons Row */
  .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .left, .right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn {
    background: none;
    border: none;
    color: #fff;
    width: 36px; height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border-radius: 50%;
    position: relative;
    padding: 0;
  }
  .btn:hover { background: rgba(255, 255, 255, 0.14); }
  .btn svg { width: 22px; height: 22px; fill: #fff; }
  .btn.active::after {
    content: "";
    position: absolute;
    bottom: 4px;
    width: 18px;
    height: 2.5px;
    background: #ff0000;
    border-radius: 2px;
  }

  .vol-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .vol-slider {
    width: 0;
    opacity: 0;
    accent-color: #fff;
    cursor: pointer;
    transition: width 0.2s ease, opacity 0.2s ease;
  }
  .vol-group:hover .vol-slider,
  .vol-slider:focus {
    width: 68px;
    opacity: 1;
  }

  .time {
    font-size: 13px;
    color: #e5e5e5;
    margin-left: 4px;
    font-variant-numeric: tabular-nums;
  }

  select.speed-select {
    background: rgba(255,255,255,0.12);
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 12px;
    cursor: pointer;
    outline: none;
  }
  select.speed-select option { background: #181818; color: #fff; }

  /* Popup Menus (Audio & Subtitles) */
  .popup-menu {
    position: absolute;
    bottom: 58px;
    right: 16px;
    background: rgba(24, 24, 24, 0.96);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    min-width: 200px;
    padding: 6px 0;
    display: none;
    z-index: 10;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  }
  .popup-menu.open { display: block; }
  .popup-header {
    font-size: 12px;
    font-weight: 600;
    color: #aaa;
    padding: 6px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 4px;
  }
  .popup-item {
    padding: 8px 14px;
    font-size: 13px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .popup-item:hover { background: rgba(255,255,255,0.1); }
  .popup-item.selected { color: #ff4e45; font-weight: 600; }

  /* Fullscreen */
  .player:fullscreen {
    width: 100vw !important;
    height: 100vh !important;
    max-width: none !important;
    border-radius: 0 !important;
  }
</style>
</head>
<body>

<div class="player" id="player">
  <video id="video"
    src="{{ url_for('stream_video', url=video_url_encoded) }}"
    autoplay preload="auto" crossorigin="anonymous"></video>

  <div class="top-bar" id="topBar">pasan video player</div>
  <div class="loader" id="loader"></div>
  <div class="speed-pill" id="speedPill">2x ⏩</div>
  <div class="seek-indicator left" id="seekLeft">⏪ 10s</div>
  <div class="seek-indicator right" id="seekRight">10s ⏩</div>

  <!-- Subtitle Menu -->
  <div class="popup-menu" id="subMenu">
    <div class="popup-header">Subtitles / CC</div>
    <div id="subList"></div>
    <div class="popup-item" id="uploadSubBtn">➕ Load .vtt / .srt file</div>
    <input type="file" id="subFileInput" accept=".vtt,.srt" style="display:none">
  </div>

  <!-- Audio Track Menu -->
  <div class="popup-menu" id="audioMenu">
    <div class="popup-header">Audio Track</div>
    <div id="audioList"></div>
  </div>

  <div class="controls" id="controls">
    <div class="progress-wrap" id="progressWrap">
      <div class="hover-time" id="hoverTime">0:00</div>
      <div class="progress" id="progress">
        <div class="buffered" id="buffered"></div>
        <div class="played" id="played"></div>
        <div class="scrubber" id="scrubber"></div>
      </div>
    </div>

    <div class="row">
      <div class="left">
        <button class="btn" id="playPause" title="Play/Pause (Space)">
          <svg id="playIcon" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
        </button>

        <div class="vol-group">
          <button class="btn" id="mute" title="Mute (M)">
            <svg id="volIcon" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
          </button>
          <input type="range" class="vol-slider" id="volume" min="0" max="1" step="0.05" value="1">
        </div>

        <span class="time"><span id="current">0:00</span> / <span id="duration">0:00</span></span>
      </div>

      <div class="right">
        <button class="btn" id="subBtn" title="Subtitles / CC">
          <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 12h4v2H4v-2zm10 6H4v-2h10v2zm6 0h-4v-2h4v2zm0-4H10v-2h10v2z"/></svg>
        </button>

        <button class="btn" id="audioBtn" title="Audio Track">
          <svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
        </button>

        <select class="speed-select" id="speed" title="Playback Speed">
          <option value="0.5">0.5x</option>
          <option value="1" selected>1x</option>
          <option value="1.25">1.25x</option>
          <option value="1.5">1.5x</option>
          <option value="2">2x</option>
        </select>

        <button class="btn" id="pip" title="Picture-in-Picture">
          <svg viewBox="0 0 24 24"><path d="M19 11h-8v6h8v-6zm4 8V4.98C23 3.88 22.1 3 21 3H3c-1.1 0-2 .88-2 1.98V19c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2zm-2 .02H3V4.97h18v14.05z"/></svg>
        </button>

        <button class="btn" id="fullscreen" title="Fullscreen (F)">
          <svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
        </button>
      </div>
    </div>
  </div>
</div>

<script>
const video = document.getElementById("video");
const player = document.getElementById("player");
const topBar = document.getElementById("topBar");
const loader = document.getElementById("loader");
const controls = document.getElementById("controls");
const progressWrap = document.getElementById("progressWrap");
const played = document.getElementById("played");
const buffered = document.getElementById("buffered");
const scrubber = document.getElementById("scrubber");
const hoverTime = document.getElementById("hoverTime");
const playPause = document.getElementById("playPause");
const playIcon = document.getElementById("playIcon");
const muteBtn = document.getElementById("mute");
const volume = document.getElementById("volume");
const speed = document.getElementById("speed");
const fullscreen = document.getElementById("fullscreen");
const pip = document.getElementById("pip");
const current = document.getElementById("current");
const duration = document.getElementById("duration");
const speedPill = document.getElementById("speedPill");
const seekLeft = document.getElementById("seekLeft");
const seekRight = document.getElementById("seekRight");

const subBtn = document.getElementById("subBtn");
const subMenu = document.getElementById("subMenu");
const subList = document.getElementById("subList");
const uploadSubBtn = document.getElementById("uploadSubBtn");
const subFileInput = document.getElementById("subFileInput");

const audioBtn = document.getElementById("audioBtn");
const audioMenu = document.getElementById("audioMenu");
const audioList = document.getElementById("audioList");

let hideTimer;
let isDragging = false;

const PLAY_SVG = '<path d="M8 5v14l11-7z"/>';
const PAUSE_SVG = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';

function updatePlayIcon() {
  playIcon.innerHTML = video.paused ? PLAY_SVG : PAUSE_SVG;
}

function togglePlay() {
  if (video.paused) video.play();
  else video.pause();
  updatePlayIcon();
}

playPause.onclick = togglePlay;
video.onplay = () => { updatePlayIcon(); showControls(); };
video.onpause = () => { updatePlayIcon(); showControls(); };

/* Loader */
video.onwaiting = () => loader.style.display = "block";
video.onplaying = () => loader.style.display = "none";
video.oncanplay = () => loader.style.display = "none";

/* Time & Progress */
function format(t) {
  if (isNaN(t)) return "0:00";
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = Math.floor(t % 60).toString().padStart(2, "0");
  return h > 0 ? `${h}:${m.toString().padStart(2, "0")}:${s}` : `${m}:${s}`;
}

video.ontimeupdate = () => {
  if (!isDragging && video.duration) {
    const pct = (video.currentTime / video.duration) * 100;
    played.style.width = pct + "%";
    scrubber.style.left = pct + "%";
  }
  current.textContent = format(video.currentTime);
};

video.onloadedmetadata = () => {
  duration.textContent = format(video.duration);
  renderAudioTracks();
  renderSubTracks();
};

video.onprogress = () => {
  if (video.buffered.length > 0 && video.duration) {
    const end = video.buffered.end(video.buffered.length - 1);
    buffered.style.width = (end / video.duration * 100) + "%";
  }
};

/* YouTube-Style Seek Bar (Click + Drag + Hover Preview) */
function seekFromEvent(e) {
  const rect = progressWrap.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const ratio = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
  if (video.duration) {
    video.currentTime = ratio * video.duration;
    played.style.width = (ratio * 100) + "%";
    scrubber.style.left = (ratio * 100) + "%";
  }
}

progressWrap.addEventListener("pointerdown", (e) => {
  isDragging = true;
  progressWrap.classList.add("dragging");
  progressWrap.setPointerCapture(e.pointerId);
  seekFromEvent(e);
});

progressWrap.addEventListener("pointermove", (e) => {
  const rect = progressWrap.getBoundingClientRect();
  const ratio = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
  if (video.duration) {
    hoverTime.style.display = "block";
    hoverTime.style.left = (ratio * 100) + "%";
    hoverTime.textContent = format(ratio * video.duration);
  }
  if (isDragging) seekFromEvent(e);
});

progressWrap.addEventListener("pointerup", () => {
  isDragging = false;
  progressWrap.classList.remove("dragging");
});

progressWrap.addEventListener("pointerleave", () => {
  hoverTime.style.display = "none";
});

/* Volume */
volume.oninput = () => {
  video.volume = volume.value;
  video.muted = volume.value == 0;
};
muteBtn.onclick = () => {
  video.muted = !video.muted;
  volume.value = video.muted ? 0 : (video.volume || 1);
};

/* Speed */
speed.onchange = () => video.playbackRate = parseFloat(speed.value);

/* Fullscreen & PiP */
fullscreen.onclick = () => {
  if (!document.fullscreenElement) player.requestFullscreen();
  else document.exitFullscreen();
};
pip.onclick = async () => {
  if (document.pictureInPictureElement) document.exitPictureInPicture();
  else if (video.requestPictureInPicture) await video.requestPictureInPicture();
};

/* ===== HOLD RIGHT SIDE FOR 2x SPEED ===== */
let holdTimer = null;
let isHoldingSpeed = false;
let prevSpeed = 1;
let suppressNextClick = false;

player.addEventListener("pointerdown", (e) => {
  if (e.target.closest(".controls") || e.target.closest(".popup-menu")) return;
  const rect = player.getBoundingClientRect();
  const isRightSide = (e.clientX - rect.left) > (rect.width / 2);

  if (isRightSide) {
    holdTimer = setTimeout(() => {
      isHoldingSpeed = true;
      suppressNextClick = true;
      prevSpeed = video.playbackRate;
      video.playbackRate = 2;
      speedPill.classList.add("show");
    }, 300);
  }
});

function stopHoldSpeed() {
  clearTimeout(holdTimer);
  if (isHoldingSpeed) {
    video.playbackRate = prevSpeed;
    speedPill.classList.remove("show");
    isHoldingSpeed = false;
  }
}

player.addEventListener("pointerup", stopHoldSpeed);
player.addEventListener("pointerleave", stopHoldSpeed);
player.addEventListener("pointercancel", stopHoldSpeed);

/* ===== DOUBLE TAP 10s SEEK & SINGLE CLICK PLAY/PAUSE ===== */
let lastTap = 0;
let clickTimer = null;

player.addEventListener("click", (e) => {
  if (e.target.closest(".controls") || e.target.closest(".popup-menu")) return;
  closeMenus();

  if (suppressNextClick) {
    suppressNextClick = false;
    return;
  }

  const now = Date.now();
  const tapGap = now - lastTap;
  lastTap = now;

  if (tapGap < 300 && tapGap > 0) {
    clearTimeout(clickTimer);
    const rect = player.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < rect.width / 2) {
      video.currentTime = Math.max(0, video.currentTime - 10);
      animateSeek(seekLeft);
    } else {
      video.currentTime = Math.min(video.duration || 0, video.currentTime + 10);
      animateSeek(seekRight);
    }
  } else {
    clickTimer = setTimeout(() => togglePlay(), 240);
  }
});

function animateSeek(el) {
  el.classList.add("seek-show");
  setTimeout(() => el.classList.remove("seek-show"), 400);
}

/* ===== SUBTITLES (CC) ===== */
function renderSubTracks() {
  subList.innerHTML = "";
  const tracks = Array.from(video.textTracks);
  const offItem = document.createElement("div");
  const anyShowing = tracks.some(t => t.mode === "showing");
  offItem.className = "popup-item" + (!anyShowing ? " selected" : "");
  offItem.textContent = "Off";
  offItem.onclick = () => {
    tracks.forEach(t => t.mode = "disabled");
    subBtn.classList.remove("active");
    renderSubTracks();
    closeMenus();
  };
  subList.appendChild(offItem);

  tracks.forEach((track, i) => {
    const item = document.createElement("div");
    item.className = "popup-item" + (track.mode === "showing" ? " selected" : "");
    item.textContent = track.label || `Subtitle ${i + 1}`;
    item.onclick = () => {
      tracks.forEach((t, idx) => t.mode = idx === i ? "showing" : "disabled");
      subBtn.classList.add("active");
      renderSubTracks();
      closeMenus();
    };
    subList.appendChild(item);
  });
}

uploadSubBtn.onclick = () => subFileInput.click();
subFileInput.onchange = (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    let text = reader.result;
    if (file.name.toLowerCase().endsWith(".srt")) {
      text = "WEBVTT\\n\\n" + text
        .replace(/\\r+/g, "")
        .replace(/(\\d{2}:\\d{2}:\\d{2}),(\\d{3})/g, "$1.$2");
    }
    const blob = new Blob([text], { type: "text/vtt" });
    const url = URL.createObjectURL(blob);
    const trackEl = document.createElement("track");
    trackEl.kind = "subtitles";
    trackEl.label = file.name;
    trackEl.src = url;
    trackEl.default = true;
    video.appendChild(trackEl);

    Array.from(video.textTracks).forEach(t => t.mode = "disabled");
    trackEl.track.mode = "showing";
    subBtn.classList.add("active");
    renderSubTracks();
    closeMenus();
  };
  reader.readAsText(file);
  subFileInput.value = "";
};

/* ===== AUDIO TRACK SWITCHER ===== */
function renderAudioTracks() {
  audioList.innerHTML = "";
  const tracks = video.audioTracks;

  if (!tracks || tracks.length <= 1) {
    const item = document.createElement("div");
    item.className = "popup-item selected";
    item.textContent = "Default Audio";
    audioList.appendChild(item);
    return;
  }

  for (let i = 0; i < tracks.length; i++) {
    const t = tracks[i];
    const item = document.createElement("div");
    item.className = "popup-item" + (t.enabled ? " selected" : "");
    item.textContent = t.label || t.language || `Audio Track ${i + 1}`;
    item.onclick = () => {
      for (let j = 0; j < tracks.length; j++) {
        tracks[j].enabled = (j === i);
      }
      renderAudioTracks();
      closeMenus();
    };
    audioList.appendChild(item);
  }
}

/* Menus Toggle */
function closeMenus() {
  subMenu.classList.remove("open");
  audioMenu.classList.remove("open");
}

subBtn.onclick = (e) => {
  e.stopPropagation();
  const isOpen = subMenu.classList.contains("open");
  closeMenus();
  if (!isOpen) { renderSubTracks(); subMenu.classList.add("open"); }
};

audioBtn.onclick = (e) => {
  e.stopPropagation();
  const isOpen = audioMenu.classList.contains("open");
  closeMenus();
  if (!isOpen) { renderAudioTracks(); audioMenu.classList.add("open"); }
};

/* Keyboard Shortcuts */
document.onkeydown = (e) => {
  if (e.code === "Space") { e.preventDefault(); togglePlay(); }
  if (e.code === "ArrowRight") video.currentTime += 10;
  if (e.code === "ArrowLeft") video.currentTime -= 10;
  if (e.key.toLowerCase() === "f") fullscreen.click();
  if (e.key.toLowerCase() === "m") muteBtn.click();
};

/* Auto Hide Controls */
function showControls() {
  controls.classList.remove("hide");
  topBar.classList.remove("hide");
  clearTimeout(hideTimer);
  if (!video.paused) {
    hideTimer = setTimeout(() => {
      if (!subMenu.classList.contains("open") && !audioMenu.classList.contains("open")) {
        controls.classList.add("hide");
        topBar.classList.add("hide");
      }
    }, 3000);
  }
}
player.onmousemove = showControls;
player.ontouchstart = showControls;

/* 60s Forward Buffer */
setInterval(() => {
  if (video.buffered.length > 0 && video.duration) {
    const end = video.buffered.end(video.buffered.length - 1);
    if ((end - video.currentTime) < 60 && end < video.duration) {
      video.preload = "auto";
    }
  }
}, 4000);
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
