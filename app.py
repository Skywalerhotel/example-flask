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
    box-sizing:border-box;
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
<title>pasan Video Player</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">

<style>
*{ box-sizing:border-box; }
body{
    margin:0;
    background:#0f172a;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    font-family:'Poppins',Arial,sans-serif;
}

.player{
    width:95%;
    max-width:1000px;
    background:black;
    border-radius:18px;
    overflow:hidden;
    position:relative;
}

video{
    width:100%;
    height:auto;
    display:block;
    object-fit:contain;
}

/* Loader */
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
    z-index:5;
}
@keyframes spin{100%{transform:translate(-50%,-50%) rotate(360deg)}}

/* Controls */
.controls{
    position:absolute;
    bottom:0;
    width:100%;
    background:linear-gradient(to top,rgba(0,0,0,0.92),transparent);
    padding:15px;
    transition:opacity 0.3s;
    z-index:10;
}
.hide{opacity:0; pointer-events:none;}

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
    border-radius:5px;
}
.played{
    position:absolute;
    height:100%;
    background:#ef4444;
    width:0%;
    border-radius:5px;
}

.row{
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.title{
    font-family:'Poppins',sans-serif;
    font-size:1.4rem;
    font-weight:700;
    background:linear-gradient(135deg,#667eea 0%,#764ba2 50%,#f093fb 100%);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
    text-align:center;
    margin-bottom:8px;
}
.left,.right{
    display:flex;
    align-items:center;
    gap:10px;
}

.ctrl-btn{
    background:none;
    border:none;
    color:white;
    font-size:16px;
    cursor:pointer;
    padding:4px;
    border-radius:6px;
    transition:background 0.15s;
    line-height:1;
}
.ctrl-btn:hover{ background:rgba(255,255,255,0.15); }

select.ctrl-select{
    background:#1f2937;
    border:1px solid #374151;
    color:white;
    font-size:13px;
    cursor:pointer;
    padding:3px 6px;
    border-radius:6px;
}

input[type=range]{
    width:75px;
    cursor:pointer;
}

.time{
    font-size:13px;
    color:#e2e8f0;
    white-space:nowrap;
}

/* Settings Icon */
.settings-btn{
    background:none;
    border:none;
    color:white;
    font-size:17px;
    cursor:pointer;
    padding:4px 6px;
    border-radius:6px;
    transition:background 0.15s, transform 0.3s;
    line-height:1;
}
.settings-btn:hover{ background:rgba(255,255,255,0.15); }
.settings-btn.open{ transform:rotate(45deg); }

/* ===== SETTINGS PANEL ===== */
.settings-panel{
    position:absolute;
    bottom:80px;
    right:14px;
    width:310px;
    background:#111827;
    border:1px solid #1f2937;
    border-radius:14px;
    box-shadow:0 8px 32px rgba(0,0,0,0.7);
    z-index:20;
    overflow:hidden;
    transform-origin:bottom right;
    transform:scale(0.85);
    opacity:0;
    pointer-events:none;
    transition:transform 0.2s cubic-bezier(.34,1.56,.64,1), opacity 0.18s ease;
}
.settings-panel.open{
    transform:scale(1);
    opacity:1;
    pointer-events:all;
}

.settings-header{
    padding:14px 16px 10px;
    font-size:14px;
    font-weight:700;
    color:#94a3b8;
    text-transform:uppercase;
    letter-spacing:0.08em;
    border-bottom:1px solid #1f2937;
}

.settings-section{
    padding:12px 16px;
    border-bottom:1px solid #1e293b;
}
.settings-section:last-child{ border-bottom:none; }

.section-title{
    font-size:11px;
    font-weight:600;
    color:#64748b;
    text-transform:uppercase;
    letter-spacing:0.1em;
    margin-bottom:8px;
}

/* Subtitle rows */
.sub-row{
    display:flex;
    align-items:center;
    gap:8px;
    padding:6px 8px;
    border-radius:8px;
    cursor:pointer;
    transition:background 0.15s;
}
.sub-row:hover{ background:#1f2937; }
.sub-row.active{ background:#1e3a5f; }

.sub-dot{
    width:8px;
    height:8px;
    border-radius:50%;
    background:#374151;
    flex-shrink:0;
    transition:background 0.15s;
}
.sub-row.active .sub-dot{ background:#3b82f6; }

.sub-label{
    font-size:13px;
    color:#e2e8f0;
    flex:1;
}
.sub-badge{
    font-size:10px;
    padding:2px 6px;
    border-radius:4px;
    background:#1f2937;
    color:#64748b;
    font-weight:600;
}
.sub-row.active .sub-label{ color:#93c5fd; }

/* Upload button */
.upload-btn{
    display:flex;
    align-items:center;
    gap:8px;
    width:100%;
    padding:8px 10px;
    background:#1f2937;
    border:1.5px dashed #374151;
    border-radius:8px;
    color:#94a3b8;
    font-size:12px;
    font-family:'Poppins',Arial,sans-serif;
    cursor:pointer;
    transition:all 0.15s;
    margin-top:6px;
}
.upload-btn:hover{
    border-color:#3b82f6;
    color:#93c5fd;
    background:#172033;
}
.upload-btn svg{ flex-shrink:0; }

/* Audio rows */
.audio-row{
    display:flex;
    align-items:center;
    gap:8px;
    padding:6px 8px;
    border-radius:8px;
    cursor:pointer;
    transition:background 0.15s;
}
.audio-row:hover{ background:#1f2937; }
.audio-row.active{ background:#1f2937; border-left:3px solid #8b5cf6; }
.audio-dot{
    width:8px; height:8px; border-radius:50%;
    background:#374151; flex-shrink:0; transition:background 0.15s;
}
.audio-row.active .audio-dot{ background:#8b5cf6; }
.audio-label{ font-size:13px; color:#e2e8f0; flex:1; }
.audio-row.active .audio-label{ color:#c4b5fd; }

.no-tracks{
    font-size:12px;
    color:#4b5563;
    padding:4px 8px;
    font-style:italic;
}

/* Hidden file input */
#srtUpload{ display:none; }

/* Fullscreen */
.player:fullscreen{ width:100% !important; height:100% !important; border-radius:0 !important; }
.player:fullscreen video{ width:100%; height:100%; }

/* Seek indicator */
.seek-indicator{
    position:absolute;
    top:50%;
    transform:translateY(-50%);
    font-size:36px;
    color:white;
    background:rgba(0,0,0,0.5);
    padding:18px;
    border-radius:50%;
    opacity:0;
    transition:0.25s ease;
    pointer-events:none;
    z-index:5;
}
.seek-indicator.left{ left:12%; }
.seek-indicator.right{ right:12%; }
.seek-show{ opacity:1; transform:translateY(-50%) scale(1.2); }
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

<!-- ===== SETTINGS PANEL ===== -->
<div class="settings-panel" id="settingsPanel">
    <div class="settings-header">⚙ Settings</div>

    <!-- SUBTITLES SECTION -->
    <div class="settings-section">
        <div class="section-title">Subtitles / CC</div>
        <div id="subtitleList">
            <!-- Off option always first -->
            <div class="sub-row active" data-track="-1" onclick="selectSubtitle(this,-1)">
                <div class="sub-dot"></div>
                <span class="sub-label">Off</span>
            </div>
            <!-- Embedded tracks injected by JS -->
        </div>

        <!-- Upload External SRT -->
        <label class="upload-btn" for="srtUpload">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Load External SRT / VTT
        </label>
        <input type="file" id="srtUpload" accept=".srt,.vtt">
    </div>

    <!-- AUDIO TRACK SECTION -->
    <div class="settings-section">
        <div class="section-title">Audio Track</div>
        <div id="audioList">
            <div class="no-tracks" id="noAudioMsg">Detecting audio tracks…</div>
        </div>
    </div>
</div>

<!-- CONTROLS -->
<div class="controls" id="controls">
    <div class="title">pasan video player</div>
    <div class="progress" id="progress">
        <div class="buffered" id="buffered"></div>
        <div class="played" id="played"></div>
    </div>
    <div class="row">
        <div class="left">
            <button class="ctrl-btn" id="playPause">▶</button>
            <button class="ctrl-btn" id="mute">🔊</button>
            <input type="range" id="volume" min="0" max="1" step="0.05" value="1">
            <span class="time"><span id="current">0:00</span> / <span id="duration">0:00</span></span>
        </div>
        <div class="right">
            <select class="ctrl-select" id="speed">
                <option value="0.5">0.5×</option>
                <option value="1" selected>1×</option>
                <option value="1.5">1.5×</option>
                <option value="2">2×</option>
            </select>
            <button class="ctrl-btn" id="pip" title="Picture in Picture">📺</button>
            <button class="ctrl-btn" id="fullscreen" title="Fullscreen">⛶</button>
            <button class="settings-btn" id="settingsBtn" title="Settings">⚙</button>
        </div>
    </div>
</div>
</div><!-- end .player -->

<script>
const video         = document.getElementById("video");
const player        = document.getElementById("player");
const loader        = document.getElementById("loader");
const controls      = document.getElementById("controls");
const progress      = document.getElementById("progress");
const played        = document.getElementById("played");
const bufferedEl    = document.getElementById("buffered");
const playPause     = document.getElementById("playPause");
const muteBtn       = document.getElementById("mute");
const volumeEl      = document.getElementById("volume");
const speedEl       = document.getElementById("speed");
const fullscreenBtn = document.getElementById("fullscreen");
const pipBtn        = document.getElementById("pip");
const currentEl     = document.getElementById("current");
const durationEl    = document.getElementById("duration");
const settingsBtn   = document.getElementById("settingsBtn");
const settingsPanel = document.getElementById("settingsPanel");
const srtUpload     = document.getElementById("srtUpload");
const subtitleList  = document.getElementById("subtitleList");
const audioList     = document.getElementById("audioList");

// ===== PLAY / PAUSE =====
playPause.addEventListener("click", (e) => {
    e.stopPropagation();
    if (video.paused) { video.play(); }
    else { video.pause(); }
});

// Sync button icon with actual video state
video.addEventListener("play",  () => { playPause.textContent = "❚❚"; });
video.addEventListener("pause", () => { playPause.textContent = "▶"; });

// ===== LOADER =====
video.addEventListener("waiting", () => loader.style.display = "block");
video.addEventListener("playing", () => loader.style.display = "none");
video.addEventListener("canplay", () => loader.style.display = "none");

// ===== PROGRESS / TIME =====
video.addEventListener("timeupdate", () => {
    if (!isNaN(video.duration)) {
        played.style.width = (video.currentTime / video.duration * 100) + "%";
    }
    currentEl.textContent = format(video.currentTime);
});

video.addEventListener("loadedmetadata", () => {
    durationEl.textContent = format(video.duration);
    detectTracks();
});

function format(t) {
    if (isNaN(t)) return "0:00";
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60).toString().padStart(2, "0");
    return m + ":" + s;
}

video.addEventListener("progress", () => {
    if (video.buffered.length > 0) {
        const end = video.buffered.end(video.buffered.length - 1);
        if (!isNaN(video.duration)) {
            bufferedEl.style.width = (end / video.duration * 100) + "%";
        }
    }
});

// ===== SEEK BAR =====
progress.addEventListener("click", (e) => {
    e.stopPropagation();
    const rect = progress.getBoundingClientRect();
    video.currentTime = ((e.clientX - rect.left) / rect.width) * video.duration;
});

// ===== VOLUME =====
volumeEl.addEventListener("input", (e) => {
    e.stopPropagation();
    video.volume = volumeEl.value;
    video.muted = (volumeEl.value == 0);
    muteBtn.textContent = (video.muted || video.volume === 0) ? "🔇" : "🔊";
});

muteBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    video.muted = !video.muted;
    muteBtn.textContent = video.muted ? "🔇" : "🔊";
    if (!video.muted) volumeEl.value = video.volume || 1;
});

// ===== SPEED =====
speedEl.addEventListener("change", (e) => {
    e.stopPropagation();
    video.playbackRate = speedEl.value;
});

// ===== FULLSCREEN =====
fullscreenBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!document.fullscreenElement) player.requestFullscreen();
    else document.exitFullscreen();
});

// ===== PiP =====
pipBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
        if (document.pictureInPictureElement) document.exitPictureInPicture();
        else await video.requestPictureInPicture();
    } catch(err) { console.warn("PiP error:", err); }
});

// ===== KEYBOARD =====
document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.code === "Space")       { e.preventDefault(); playPause.click(); }
    if (e.code === "ArrowRight")  { e.preventDefault(); video.currentTime = Math.min(video.duration, video.currentTime + 10); }
    if (e.code === "ArrowLeft")   { e.preventDefault(); video.currentTime = Math.max(0, video.currentTime - 10); }
    if (e.code === "KeyM")        { muteBtn.click(); }
    if (e.code === "KeyF")        { fullscreenBtn.click(); }
});

// ===== AUTO HIDE CONTROLS =====
let hideTimer;
let mouseIdle = false;

function showControls() {
    controls.classList.remove("hide");
    clearTimeout(hideTimer);
    // Only hide if settings panel is closed
    hideTimer = setTimeout(() => {
        if (!settingsPanel.classList.contains("open") && !video.paused) {
            controls.classList.add("hide");
        }
    }, 3000);
}

function cancelHide() {
    clearTimeout(hideTimer);
    controls.classList.remove("hide");
}

player.addEventListener("mousemove", showControls);
player.addEventListener("mouseleave", () => {
    if (!settingsPanel.classList.contains("open") && !video.paused) {
        hideTimer = setTimeout(() => controls.classList.add("hide"), 1000);
    }
});

// Keep controls visible when paused
video.addEventListener("pause", cancelHide);
video.addEventListener("play",  showControls);

// ===== FORWARD BUFFER =====
setInterval(() => {
    if (video.buffered.length > 0) {
        const end = video.buffered.end(video.buffered.length - 1);
        if ((end - video.currentTime) < 60 && end < video.duration) {
            video.preload = "auto";
        }
    }
}, 4000);

// ===== DOUBLE TAP / CLICK ON VIDEO AREA =====
const seekLeft  = document.getElementById("seekLeft");
const seekRight = document.getElementById("seekRight");
let lastTap = 0;

// Only attach to the video element itself, not the whole player
video.addEventListener("click", function(e) {
    const now = Date.now();
    const tapGap = now - lastTap;

    if (tapGap < 300 && tapGap > 0) {
        // Double tap — seek
        const rect = video.getBoundingClientRect();
        const x = e.clientX - rect.left;
        if (x < rect.width / 2) {
            video.currentTime = Math.max(0, video.currentTime - 10);
            animateSeek(seekLeft);
        } else {
            video.currentTime = Math.min(video.duration, video.currentTime + 10);
            animateSeek(seekRight);
        }
    } else {
        // Single tap — toggle play/pause
        if (video.paused) video.play();
        else video.pause();
    }
    lastTap = now;
});

function animateSeek(el) {
    el.classList.add("seek-show");
    setTimeout(() => el.classList.remove("seek-show"), 350);
}

// ======================================
// ===== SETTINGS PANEL =====
// ======================================

settingsBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = settingsPanel.classList.toggle("open");
    settingsBtn.classList.toggle("open", isOpen);
    if (isOpen) cancelHide();  // keep controls visible while settings open
    else showControls();
});

// Close settings when clicking outside the panel
document.addEventListener("click", (e) => {
    if (settingsPanel.classList.contains("open") &&
        !settingsPanel.contains(e.target) &&
        e.target !== settingsBtn) {
        settingsPanel.classList.remove("open");
        settingsBtn.classList.remove("open");
        showControls();
    }
});

// Prevent clicks inside settings panel from bubbling to player/video
settingsPanel.addEventListener("click", (e) => e.stopPropagation());
controls.addEventListener("click", (e) => e.stopPropagation());

// ======================================
// ===== SUBTITLE TRACK DETECTION =====
// ======================================

let externalSubTrack = null;
let activeSubIndex = -1; // -1 = off

function detectTracks() {
    // Small delay to let the browser parse embedded tracks
    setTimeout(buildSubtitleUI, 600);
    setTimeout(buildAudioUI, 600);
}

function buildSubtitleUI() {
    const tracks = video.textTracks;
    // Remove old entries except "Off"
    const rows = subtitleList.querySelectorAll(".sub-row[data-track]");
    rows.forEach(r => { if (r.dataset.track != "-1") r.remove(); });

    if (tracks.length === 0) {
        // Keep just "Off" – already there
        return;
    }

    for (let i = 0; i < tracks.length; i++) {
        const t = tracks[i];
        const lang = t.language || "";
        const label = t.label || ("Track " + (i + 1));
        const kind  = t.kind || "subtitles";

        const row = document.createElement("div");
        row.className = "sub-row";
        row.dataset.track = i;
        row.onclick = () => selectSubtitle(row, i);
        row.innerHTML = `
            <div class="sub-dot"></div>
            <span class="sub-label">${escHtml(label)}${lang ? " ["+escHtml(lang)+"]":""}</span>
            <span class="sub-badge">${escHtml(kind)}</span>`;
        subtitleList.appendChild(row);

        // Disable all tracks by default (honour "Off" default)
        t.mode = "disabled";
    }
}

function selectSubtitle(rowEl, index) {
    // Remove active from all
    subtitleList.querySelectorAll(".sub-row").forEach(r => r.classList.remove("active"));
    rowEl.classList.add("active");
    activeSubIndex = index;

    const tracks = video.textTracks;

    // Remove any injected external track cue element
    if (externalSubTrack && index !== 9999) {
        externalSubTrack.mode = "disabled";
    }

    if (index === -1) {
        // Turn off all
        for (let i = 0; i < tracks.length; i++) tracks[i].mode = "disabled";
        hideCueDisplay();
        return;
    }

    if (index === 9999) {
        // External SRT/VTT track
        if (externalSubTrack) {
            for (let i = 0; i < tracks.length; i++) tracks[i].mode = "disabled";
            externalSubTrack.mode = "showing";
        }
        return;
    }

    // Embedded track
    for (let i = 0; i < tracks.length; i++) {
        tracks[i].mode = (i === index) ? "showing" : "disabled";
    }
}

function hideCueDisplay() {
    const tracks = video.textTracks;
    for (let i = 0; i < tracks.length; i++) tracks[i].mode = "disabled";
}

// ======================================
// ===== EXTERNAL SRT / VTT UPLOAD =====
// ======================================

srtUpload.addEventListener("change", function() {
    const file = this.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const content = e.target.result;
        let vttContent;

        if (file.name.toLowerCase().endsWith(".srt")) {
            vttContent = srtToVtt(content);
        } else {
            vttContent = content; // already VTT
        }

        // Remove previous external track element if any
        const old = document.getElementById("externalTrackEl");
        if (old) old.remove();

        const blob = new Blob([vttContent], { type: "text/vtt" });
        const url  = URL.createObjectURL(blob);

        const trackEl = document.createElement("track");
        trackEl.id    = "externalTrackEl";
        trackEl.kind  = "subtitles";
        trackEl.label = file.name;
        trackEl.src   = url;
        video.appendChild(trackEl);

        // Wait for track to load
        trackEl.addEventListener("load", () => {
            externalSubTrack = video.textTracks[video.textTracks.length - 1];

            // Remove old external row if present
            const oldRow = document.getElementById("extSubRow");
            if (oldRow) oldRow.remove();

            // Add row
            const row = document.createElement("div");
            row.className = "sub-row";
            row.id = "extSubRow";
            row.dataset.track = "9999";
            row.onclick = () => selectSubtitle(row, 9999);
            row.innerHTML = `
                <div class="sub-dot"></div>
                <span class="sub-label">${escHtml(file.name)}</span>
                <span class="sub-badge" style="background:#1a3a2a;color:#4ade80;">ext</span>`;
            subtitleList.appendChild(row);

            // Auto-select the uploaded track
            selectSubtitle(row, 9999);
        });
    };
    reader.readAsText(file);
    this.value = ""; // reset so same file can be re-uploaded
});

// Simple SRT → VTT converter
function srtToVtt(srt) {
    let vtt = "WEBVTT\n\n";
    vtt += srt
        .replace(/\r\n/g, "\n")
        .replace(/\r/g, "\n")
        .replace(/(\d{2}:\d{2}:\d{2}),(\d{3})/g, "$1.$2")
        .trim();
    return vtt;
}

// ======================================
// ===== AUDIO TRACK DETECTION =====
// ======================================

function buildAudioUI() {
    audioList.innerHTML = "";

    // AudioTrackList API (supported in some browsers)
    const audioTracks = video.audioTracks;

    if (!audioTracks || audioTracks.length === 0) {
        audioList.innerHTML = '<div class="no-tracks">No multiple audio tracks detected</div>';
        return;
    }

    for (let i = 0; i < audioTracks.length; i++) {
        const t = audioTracks[i];
        const label = t.label || t.language || ("Track " + (i + 1));
        const lang  = t.language || "";

        const row = document.createElement("div");
        row.className = "audio-row" + (t.enabled ? " active" : "");
        row.dataset.idx = i;
        row.onclick = () => selectAudio(i);
        row.innerHTML = `
            <div class="audio-dot"></div>
            <span class="audio-label">${escHtml(label)}${lang && lang !== label ? " ["+escHtml(lang)+"]" : ""}</span>`;
        audioList.appendChild(row);
    }
}

function selectAudio(idx) {
    const audioTracks = video.audioTracks;
    if (!audioTracks) return;

    for (let i = 0; i < audioTracks.length; i++) {
        audioTracks[i].enabled = (i === idx);
    }

    // Update UI
    audioList.querySelectorAll(".audio-row").forEach((r, i) => {
        r.classList.toggle("active", i === idx);
    });
}

// ======================================
// ===== UTILS =====
// ======================================

function escHtml(str) {
    return String(str)
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;");
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

    headers = {'User-Agent': 'Mozilla/5.0'}
    if range_header:
        headers['Range'] = range_header

    upstream = requests.get(video_url, headers=headers, stream=True)

    def generate():
        for chunk in upstream.iter_content(chunk_size=32768):
            if chunk:
                yield chunk
        upstream.close()

    return Response(
        generate(),
        status=upstream.status_code,
        headers=dict(upstream.headers)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
