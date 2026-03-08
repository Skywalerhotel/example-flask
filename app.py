from flask import Flask, request, Response, render_template_string, stream_with_context
import requests
import re

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ProxyPlay</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --accent: #c8ff00;
    --accent2: #00ffe0;
    --text: #e8e8f0;
    --muted: #5a5a7a;
    --danger: #ff4060;
    --border: rgba(200,255,0,0.15);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Grid background */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(200,255,0,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(200,255,0,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  .app {
    position: relative;
    z-index: 1;
    max-width: 1100px;
    margin: 0 auto;
    padding: 24px 20px;
  }

  /* Header */
  header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
  }

  .logo {
    font-family: 'Space Mono', monospace;
    font-size: 22px;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -1px;
  }

  .logo span { color: var(--accent2); }

  .badge {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    background: var(--accent);
    color: #000;
    padding: 2px 8px;
    border-radius: 2px;
    font-weight: 700;
    letter-spacing: 1px;
  }

  /* URL Input */
  .url-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .url-input {
    flex: 1;
    min-width: 260px;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 12px 16px;
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    outline: none;
    border-radius: 4px;
    transition: border-color 0.2s;
  }

  .url-input:focus { border-color: var(--accent); }
  .url-input::placeholder { color: var(--muted); }

  .btn {
    background: var(--accent);
    color: #000;
    border: none;
    padding: 12px 24px;
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    border-radius: 4px;
    letter-spacing: 0.5px;
    transition: all 0.15s;
    white-space: nowrap;
  }

  .btn:hover { background: #d4ff20; transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }

  .btn-sm {
    padding: 8px 14px;
    font-size: 11px;
    background: var(--surface2);
    color: var(--accent);
    border: 1px solid var(--border);
  }

  .btn-sm:hover { background: var(--surface); border-color: var(--accent); }

  .btn-danger { background: var(--danger); color: #fff; }
  .btn-danger:hover { background: #ff5575; }

  /* Player wrapper */
  .player-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 20px;
    position: relative;
  }

  .video-container {
    position: relative;
    background: #000;
    width: 100%;
    aspect-ratio: 16/9;
    cursor: pointer;
  }

  video {
    width: 100%;
    height: 100%;
    display: block;
    background: #000;
  }

  /* Subtitle overlay */
  .subtitle-overlay {
    position: absolute;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    width: 90%;
    text-align: center;
    pointer-events: none;
    z-index: 10;
  }

  .subtitle-text {
    display: inline-block;
    background: rgba(0,0,0,0.8);
    color: #fff;
    font-size: 18px;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 4px;
    line-height: 1.5;
    text-shadow: 1px 1px 2px #000;
    max-width: 100%;
    word-break: break-word;
  }

  .subtitle-text:empty { display: none; }

  /* Big play button */
  .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
  }

  .play-overlay.show { opacity: 1; pointer-events: all; }

  .play-icon-big {
    width: 72px;
    height: 72px;
    background: rgba(200,255,0,0.9);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.15s;
  }

  .play-icon-big:hover { transform: scale(1.1); }

  .play-icon-big svg { margin-left: 4px; }

  /* Controls */
  .controls {
    background: var(--surface2);
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    user-select: none;
  }

  /* Progress / seek bar */
  .progress-wrap {
    position: relative;
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
    cursor: pointer;
    margin-bottom: 12px;
  }

  .progress-wrap:hover { height: 8px; margin-bottom: 10px; }

  .buffer-bar {
    position: absolute;
    left: 0; top: 0; height: 100%;
    background: rgba(255,255,255,0.15);
    border-radius: 3px;
    pointer-events: none;
    transition: width 0.5s ease;
  }

  .progress-bar {
    position: absolute;
    left: 0; top: 0; height: 100%;
    background: var(--accent);
    border-radius: 3px;
    pointer-events: none;
  }

  .progress-handle {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 14px;
    height: 14px;
    background: var(--accent);
    border-radius: 50%;
    pointer-events: none;
    transition: transform 0.1s;
    box-shadow: 0 0 8px rgba(200,255,0,0.5);
  }

  .progress-wrap:hover .progress-handle { transform: translate(-50%, -50%) scale(1.3); }

  /* Bottom controls row */
  .controls-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .ctrl-btn {
    background: none;
    border: none;
    color: var(--text);
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s, background 0.15s;
  }

  .ctrl-btn:hover { color: var(--accent); background: rgba(200,255,0,0.07); }
  .ctrl-btn.active { color: var(--accent); }

  .time-display {
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    color: var(--muted);
    white-space: nowrap;
  }

  /* Volume */
  .volume-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .volume-slider {
    -webkit-appearance: none;
    appearance: none;
    width: 80px;
    height: 4px;
    background: rgba(255,255,255,0.1);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .volume-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px; height: 12px;
    background: var(--accent2);
    border-radius: 50%;
    cursor: pointer;
  }

  /* Speed */
  .speed-select {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    padding: 4px 6px;
    border-radius: 4px;
    cursor: pointer;
    outline: none;
  }

  .speed-select:focus { border-color: var(--accent); }

  .spacer { flex: 1; }

  /* Seek buttons */
  .seek-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .seek-label {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    color: var(--muted);
    line-height: 1;
  }

  /* Settings panel */
  .settings-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  @media (max-width: 600px) {
    .settings-panel { grid-template-columns: 1fr; }
  }

  .section-title {
    font-size: 11px;
    font-family: 'Space Mono', monospace;
    color: var(--accent);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 12px;
  }

  /* Subtitle list */
  .sub-list {
    list-style: none;
    max-height: 180px;
    overflow-y: auto;
  }

  .sub-list::-webkit-scrollbar { width: 4px; }
  .sub-list::-webkit-scrollbar-track { background: var(--surface2); }
  .sub-list::-webkit-scrollbar-thumb { background: var(--muted); border-radius: 2px; }

  .sub-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.1s;
    gap: 8px;
  }

  .sub-item:hover { background: var(--surface2); }
  .sub-item.active { background: rgba(200,255,0,0.1); color: var(--accent); }

  .sub-name { flex: 1; font-size: 12px; }

  .sub-add {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }

  .sub-url-input {
    flex: 1;
    min-width: 160px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 7px 10px;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    outline: none;
    border-radius: 4px;
  }

  .sub-url-input:focus { border-color: var(--accent2); }

  /* Audio tracks */
  .track-list {
    list-style: none;
  }

  .track-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.1s;
  }

  .track-item:hover { background: var(--surface2); }
  .track-item.active { background: rgba(0,255,224,0.1); color: var(--accent2); }

  /* Buffer info */
  .buffer-info {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: var(--muted);
    margin-top: 4px;
  }

  /* Toast */
  #toast {
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 10px 22px;
    border-radius: 4px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    opacity: 0;
    transition: all 0.3s;
    z-index: 9999;
    pointer-events: none;
    white-space: nowrap;
  }

  #toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }

  /* Fullscreen */
  .video-container:fullscreen video { width: 100%; height: 100%; }

  /* Responsive */
  @media (max-width: 480px) {
    .url-bar { flex-direction: column; }
    .url-input { min-width: unset; }
    .volume-group { display: none; }
  }
</style>
</head>
<body>
<div class="app">

  <header>
    <div class="logo">PROXY<span>PLAY</span></div>
    <div class="badge">URL PROXY</div>
  </header>

  <!-- URL Input -->
  <div class="url-bar">
    <input id="urlInput" class="url-input" type="text"
      placeholder="https://example.com/video.mp4 or .m3u8 …"
      value="" />
    <button class="btn" onclick="loadVideo()">▶ LOAD</button>
    <button class="btn btn-sm" onclick="clearPlayer()">✕ CLEAR</button>
  </div>

  <!-- Player -->
  <div class="player-wrap">
    <div class="video-container" id="videoContainer">
      <video id="vid" preload="auto" crossorigin="anonymous"></video>

      <div class="subtitle-overlay">
        <div class="subtitle-text" id="subText"></div>
      </div>

      <div class="play-overlay show" id="playOverlay" onclick="togglePlay()">
        <div class="play-icon-big">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="#000">
            <polygon points="5,3 19,12 5,21"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <!-- Progress bar -->
      <div class="progress-wrap" id="progressWrap" 
           onclick="seekClick(event)"
           onmousedown="startScrub(event)"
           ontouchstart="touchScrub(event)">
        <div class="buffer-bar" id="bufferBar"></div>
        <div class="progress-bar" id="progressBar"></div>
        <div class="progress-handle" id="progressHandle"></div>
      </div>
      <div class="buffer-info" id="bufferInfo">Buffer: 0s ahead</div>

      <!-- Controls row -->
      <div class="controls-row">
        <!-- Play/Pause -->
        <button class="ctrl-btn" id="playBtn" onclick="togglePlay()" title="Play/Pause (Space)">
          <svg id="playIcon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5,3 19,12 5,21"/>
          </svg>
        </button>

        <!-- Seek -60 -->
        <div class="seek-group">
          <button class="ctrl-btn" onclick="seekRel(-60)" title="Back 60s">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
              <text x="7" y="15.5" font-size="5" fill="currentColor" font-family="monospace">60</text>
            </svg>
          </button>
          <span class="seek-label">-60s</span>
        </div>

        <!-- Seek -10 -->
        <div class="seek-group">
          <button class="ctrl-btn" onclick="seekRel(-10)" title="Back 10s (←)">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11 5V1L6 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H5c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
            </svg>
          </button>
          <span class="seek-label">-10s</span>
        </div>

        <!-- Seek +10 -->
        <div class="seek-group">
          <button class="ctrl-btn" onclick="seekRel(10)" title="Forward 10s (→)">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M13 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/>
            </svg>
          </button>
          <span class="seek-label">+10s</span>
        </div>

        <!-- Seek +60 -->
        <div class="seek-group">
          <button class="ctrl-btn" onclick="seekRel(60)" title="Forward 60s">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M13 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/>
              <text x="7" y="15.5" font-size="5" fill="currentColor" font-family="monospace">60</text>
            </svg>
          </button>
          <span class="seek-label">+60s</span>
        </div>

        <span class="time-display" id="timeDisplay">0:00 / 0:00</span>

        <span class="spacer"></span>

        <!-- Volume -->
        <div class="volume-group">
          <button class="ctrl-btn" id="muteBtn" onclick="toggleMute()" title="Mute (M)">
            <svg id="volIcon" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
          </button>
          <input type="range" class="volume-slider" id="volSlider"
            min="0" max="1" step="0.02" value="1"
            oninput="setVolume(this.value)" />
        </div>

        <!-- Speed -->
        <select class="speed-select" id="speedSelect" onchange="setSpeed(this.value)" title="Playback speed">
          <option value="0.25">0.25×</option>
          <option value="0.5">0.5×</option>
          <option value="0.75">0.75×</option>
          <option value="1" selected>1×</option>
          <option value="1.25">1.25×</option>
          <option value="1.5">1.5×</option>
          <option value="2">2×</option>
          <option value="3">3×</option>
        </select>

        <!-- Subtitle toggle -->
        <button class="ctrl-btn" id="subToggleBtn" onclick="toggleSubtitles()" title="Toggle subtitles (C)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" opacity="0.4" id="subIcon">
            <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-8 11H5v-2h7v2zm7 0h-2v-2h2v2zm0-4H12v-2h7v2zM9 11H5V9h4v2z"/>
          </svg>
        </button>

        <!-- Fullscreen -->
        <button class="ctrl-btn" onclick="toggleFullscreen()" title="Fullscreen (F)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>

  <!-- Settings Panel -->
  <div class="settings-panel">
    <!-- Subtitles -->
    <div>
      <div class="section-title">📝 Subtitles / Captions</div>
      <div class="sub-add">
        <input id="subUrlInput" class="sub-url-input" type="text"
          placeholder="Subtitle URL (.vtt / .srt) or proxy path" />
        <input id="subLabelInput" class="sub-url-input" type="text"
          placeholder="Label" style="max-width:100px" />
        <button class="btn btn-sm" onclick="addSubtitle()">+ ADD</button>
      </div>
      <ul class="sub-list" id="subList">
        <li class="sub-item" style="color:var(--muted);font-size:12px;">No subtitles added</li>
      </ul>
    </div>

    <!-- Audio tracks -->
    <div>
      <div class="section-title">🔊 Audio Tracks</div>
      <ul class="track-list" id="trackList">
        <li class="track-item" style="color:var(--muted);font-size:12px;">Load a video first</li>
      </ul>

      <div class="section-title" style="margin-top:16px;">⚙️ Buffer Settings</div>
      <div style="display:flex;align-items:center;gap:10px;margin-top:8px;flex-wrap:wrap;">
        <span style="font-size:12px;color:var(--muted);">Preload ahead (s):</span>
        <input id="bufPreload" type="number" min="10" max="120" value="60"
          style="width:60px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:4px 8px;font-size:12px;border-radius:4px;outline:none;"
          onchange="applyBufferHint()" />
        <button class="btn btn-sm" onclick="applyBufferHint()">Apply</button>
      </div>
      <div class="buffer-info" id="bufferDetail" style="margin-top:8px;">Ranges: —</div>
    </div>
  </div>

</div>

<!-- Toast -->
<div id="toast"></div>

<script>
const vid = document.getElementById('vid');
const progressBar = document.getElementById('progressBar');
const bufferBar = document.getElementById('bufferBar');
const progressHandle = document.getElementById('progressHandle');
const timeDisplay = document.getElementById('timeDisplay');
const playOverlay = document.getElementById('playOverlay');
const playIcon = document.getElementById('playIcon');
const subText = document.getElementById('subText');
const bufferInfo = document.getElementById('bufferInfo');
const bufferDetail = document.getElementById('bufferDetail');

let subtitles = []; // {label, url, cues}
let activeSubIdx = -1;
let subEnabled = true;
let scrubbing = false;
let toastTimer = null;

// ── Proxy URL builder ──────────────────────────────────────────
function proxyUrl(url) {
  if (!url) return '';
  return '/proxy?url=' + encodeURIComponent(url);
}

// ── Load video ─────────────────────────────────────────────────
function loadVideo() {
  const raw = document.getElementById('urlInput').value.trim();
  if (!raw) { toast('Paste a video URL first'); return; }
  vid.src = proxyUrl(raw);
  vid.load();
  vid.play().catch(() => {});
  playOverlay.classList.remove('show');
  refreshAudioTracks();
  toast('Loading…');
}

function clearPlayer() {
  vid.pause();
  vid.src = '';
  vid.removeAttribute('src');
  document.getElementById('urlInput').value = '';
  playOverlay.classList.add('show');
  progressBar.style.width = '0%';
  bufferBar.style.width = '0%';
  progressHandle.style.left = '0%';
  subText.textContent = '';
  timeDisplay.textContent = '0:00 / 0:00';
  bufferInfo.textContent = 'Buffer: 0s ahead';
  bufferDetail.textContent = 'Ranges: —';
}

// ── Play / Pause ────────────────────────────────────────────────
function togglePlay() {
  if (vid.paused) {
    vid.play();
    playOverlay.classList.remove('show');
    playIcon.innerHTML = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
  } else {
    vid.pause();
    playOverlay.classList.add('show');
    playIcon.innerHTML = '<polygon points="5,3 19,12 5,21"/>';
  }
}

vid.addEventListener('ended', () => {
  playOverlay.classList.add('show');
  playIcon.innerHTML = '<polygon points="5,3 19,12 5,21"/>';
});

vid.addEventListener('click', togglePlay);

// ── Time update ─────────────────────────────────────────────────
vid.addEventListener('timeupdate', () => {
  if (!vid.duration || scrubbing) return;
  const pct = (vid.currentTime / vid.duration) * 100;
  progressBar.style.width = pct + '%';
  progressHandle.style.left = pct + '%';
  timeDisplay.textContent = fmt(vid.currentTime) + ' / ' + fmt(vid.duration);
  updateSubtitle(vid.currentTime);
  updateBuffer();
});

vid.addEventListener('progress', updateBuffer);
vid.addEventListener('waiting', () => toast('Buffering…'));
vid.addEventListener('canplay', () => toast('Ready ▶', 1200));

function updateBuffer() {
  if (!vid.duration) return;
  const buf = vid.buffered;
  let ahead = 0;
  let ranges = [];
  for (let i = 0; i < buf.length; i++) {
    ranges.push(fmt(buf.start(i)) + '–' + fmt(buf.end(i)));
    if (buf.start(i) <= vid.currentTime && buf.end(i) > vid.currentTime) {
      ahead = buf.end(i) - vid.currentTime;
      const pct = (buf.end(i) / vid.duration) * 100;
      bufferBar.style.width = pct + '%';
    }
  }
  bufferInfo.textContent = 'Buffer: ' + ahead.toFixed(1) + 's ahead';
  bufferDetail.textContent = 'Ranges: ' + (ranges.join(', ') || '—');
}

// ── Seek ────────────────────────────────────────────────────────
function seekRel(delta) {
  const t = Math.max(0, Math.min(vid.duration || 0, vid.currentTime + delta));
  vid.currentTime = t;
  toast((delta > 0 ? '+' : '') + delta + 's → ' + fmt(t));
}

function seekClick(e) {
  if (!vid.duration) return;
  const rect = e.currentTarget.getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  vid.currentTime = ratio * vid.duration;
}

function startScrub(e) {
  scrubbing = true;
  document.addEventListener('mousemove', onScrubMove);
  document.addEventListener('mouseup', endScrub);
}

function onScrubMove(e) {
  if (!scrubbing || !vid.duration) return;
  const rect = document.getElementById('progressWrap').getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  const pct = ratio * 100;
  progressBar.style.width = pct + '%';
  progressHandle.style.left = pct + '%';
  vid.currentTime = ratio * vid.duration;
}

function endScrub() {
  scrubbing = false;
  document.removeEventListener('mousemove', onScrubMove);
  document.removeEventListener('mouseup', endScrub);
}

function touchScrub(e) {
  e.preventDefault();
  const touch = e.touches[0];
  const rect = document.getElementById('progressWrap').getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width));
  if (vid.duration) vid.currentTime = ratio * vid.duration;
}

// ── Volume / Mute ───────────────────────────────────────────────
function setVolume(v) {
  vid.volume = parseFloat(v);
  vid.muted = v == 0;
  updateVolIcon();
}

function toggleMute() {
  vid.muted = !vid.muted;
  document.getElementById('volSlider').value = vid.muted ? 0 : vid.volume;
  updateVolIcon();
}

function updateVolIcon() {
  const icon = document.getElementById('volIcon');
  if (vid.muted || vid.volume === 0) {
    icon.innerHTML = '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>';
  } else if (vid.volume < 0.5) {
    icon.innerHTML = '<path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z"/>';
  } else {
    icon.innerHTML = '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>';
  }
}

// ── Speed ───────────────────────────────────────────────────────
function setSpeed(v) {
  vid.playbackRate = parseFloat(v);
  toast('Speed: ' + v + '×');
}

// ── Fullscreen ──────────────────────────────────────────────────
function toggleFullscreen() {
  const c = document.getElementById('videoContainer');
  if (!document.fullscreenElement) c.requestFullscreen().catch(() => {});
  else document.exitFullscreen();
}

// ── Buffer hint (MediaSource / native) ─────────────────────────
function applyBufferHint() {
  const secs = parseInt(document.getElementById('bufPreload').value) || 60;
  // For native video: set preload and nudge
  vid.preload = 'auto';
  toast('Buffer hint: ' + secs + 's (browser-controlled)');
}

// ── Subtitles ───────────────────────────────────────────────────
function addSubtitle() {
  const url = document.getElementById('subUrlInput').value.trim();
  const label = document.getElementById('subLabelInput').value.trim() || ('Track ' + (subtitles.length + 1));
  if (!url) { toast('Enter a subtitle URL'); return; }

  const proxied = proxyUrl(url);
  fetch(proxied)
    .then(r => r.text())
    .then(text => {
      const ext = url.split('?')[0].toLowerCase();
      const cues = ext.endsWith('.srt') ? parseSRT(text) : parseVTT(text);
      const idx = subtitles.length;
      subtitles.push({ label, url, cues });
      renderSubList();
      setActiveSub(idx);
      document.getElementById('subUrlInput').value = '';
      document.getElementById('subLabelInput').value = '';
      toast('Subtitle loaded: ' + label);
    })
    .catch(() => toast('Failed to load subtitle'));
}

function renderSubList() {
  const list = document.getElementById('subList');
  if (!subtitles.length) {
    list.innerHTML = '<li class="sub-item" style="color:var(--muted);font-size:12px;">No subtitles added</li>';
    return;
  }
  list.innerHTML = subtitles.map((s, i) => `
    <li class="sub-item ${i === activeSubIdx ? 'active' : ''}" onclick="setActiveSub(${i})">
      <span class="sub-name">${s.label}</span>
      <button class="btn btn-sm btn-danger" style="padding:3px 8px;font-size:10px;"
        onclick="removeSub(event,${i})">✕</button>
    </li>
  `).join('');
}

function setActiveSub(idx) {
  activeSubIdx = idx;
  subEnabled = true;
  document.getElementById('subIcon').setAttribute('opacity', '1');
  renderSubList();
  toast('Subtitle: ' + subtitles[idx].label);
}

function removeSub(e, idx) {
  e.stopPropagation();
  subtitles.splice(idx, 1);
  if (activeSubIdx >= subtitles.length) activeSubIdx = subtitles.length - 1;
  renderSubList();
  subText.textContent = '';
}

function toggleSubtitles() {
  subEnabled = !subEnabled;
  document.getElementById('subIcon').setAttribute('opacity', subEnabled ? '1' : '0.3');
  if (!subEnabled) subText.textContent = '';
  toast(subEnabled ? 'Subtitles ON' : 'Subtitles OFF');
}

function updateSubtitle(t) {
  if (!subEnabled || activeSubIdx < 0 || !subtitles[activeSubIdx]) {
    subText.textContent = ''; return;
  }
  const cues = subtitles[activeSubIdx].cues;
  let found = '';
  for (const c of cues) {
    if (t >= c.start && t <= c.end) { found = c.text; break; }
  }
  subText.textContent = found;
}

// ── SRT parser ──────────────────────────────────────────────────
function parseSRT(text) {
  const cues = [];
  const blocks = text.trim().split(/\n\s*\n/);
  for (const block of blocks) {
    const lines = block.trim().split('\n');
    if (lines.length < 2) continue;
    const timeLine = lines.find(l => l.includes('-->'));
    if (!timeLine) continue;
    const [startStr, endStr] = timeLine.split('-->').map(s => s.trim());
    const start = srtTime(startStr), end = srtTime(endStr);
    const textLines = lines.filter(l => !l.includes('-->') && !/^\d+$/.test(l.trim()));
    cues.push({ start, end, text: textLines.join('\n').replace(/<[^>]+>/g, '') });
  }
  return cues;
}

function srtTime(s) {
  const [hms, ms] = s.replace(',', '.').split('.');
  const [h, m, sec] = hms.split(':').map(Number);
  return h * 3600 + m * 60 + sec + (parseFloat('0.' + (ms || '0')));
}

// ── VTT parser ──────────────────────────────────────────────────
function parseVTT(text) {
  const cues = [];
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length) {
    if (lines[i].includes('-->')) {
      const [startStr, endStr] = lines[i].split('-->').map(s => s.trim().split(' ')[0]);
      const start = vttTime(startStr), end = vttTime(endStr);
      i++;
      const textLines = [];
      while (i < lines.length && lines[i].trim() !== '') {
        textLines.push(lines[i].replace(/<[^>]+>/g, ''));
        i++;
      }
      if (textLines.length) cues.push({ start, end, text: textLines.join('\n') });
    } else { i++; }
  }
  return cues;
}

function vttTime(s) {
  const parts = s.split(':').map(parseFloat);
  if (parts.length === 3) return parts[0]*3600 + parts[1]*60 + parts[2];
  return parts[0]*60 + parts[1];
}

// ── Audio tracks ────────────────────────────────────────────────
function refreshAudioTracks() {
  const list = document.getElementById('trackList');
  // VideoElement.audioTracks is available in some browsers
  setTimeout(() => {
    const tracks = vid.audioTracks;
    if (!tracks || tracks.length === 0) {
      list.innerHTML = '<li class="track-item" style="color:var(--muted);font-size:12px;">Default track only</li>';
      return;
    }
    list.innerHTML = '';
    for (let i = 0; i < tracks.length; i++) {
      const t = tracks[i];
      const li = document.createElement('li');
      li.className = 'track-item' + (t.enabled ? ' active' : '');
      li.textContent = t.label || t.language || ('Track ' + (i+1));
      li.onclick = () => {
        for (let j = 0; j < tracks.length; j++) tracks[j].enabled = (j === i);
        list.querySelectorAll('.track-item').forEach((el,j) => el.classList.toggle('active', j===i));
        toast('Audio: ' + (t.label || 'Track ' + (i+1)));
      };
      list.appendChild(li);
    }
  }, 1500);
}

// ── Keyboard shortcuts ──────────────────────────────────────────
document.addEventListener('keydown', e => {
  const tag = document.activeElement.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  if (e.key === ' ') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); seekRel(-10); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); seekRel(10); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); setVolume(Math.min(1, vid.volume + 0.1)); document.getElementById('volSlider').value = vid.volume; }
  else if (e.key === 'ArrowDown') { e.preventDefault(); setVolume(Math.max(0, vid.volume - 0.1)); document.getElementById('volSlider').value = vid.volume; }
  else if (e.key === 'm' || e.key === 'M') toggleMute();
  else if (e.key === 'f' || e.key === 'F') toggleFullscreen();
  else if (e.key === 'c' || e.key === 'C') toggleSubtitles();
  else if (e.key === 'j') seekRel(-60);
  else if (e.key === 'l') seekRel(60);
});

// ── Helpers ─────────────────────────────────────────────────────
function fmt(s) {
  if (!s || isNaN(s)) return '0:00';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return (h ? h + ':' : '') + (h ? String(m).padStart(2,'0') : m) + ':' + String(sec).padStart(2,'0');
}

function toast(msg, duration = 2200) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), duration);
}

// Init
applyBufferHint();
</script>
</body>
</html>
"""

SKIP_HEADERS = {'host', 'content-length', 'transfer-encoding', 'connection',
                'keep-alive', 'te', 'trailers', 'upgrade'}

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/proxy')
def proxy():
    url = request.args.get('url', '').strip()
    if not url:
        return 'Missing url parameter', 400

    # Forward selected request headers
    forward_headers = {
        k: v for k, v in request.headers
        if k.lower() not in SKIP_HEADERS
    }
    forward_headers['User-Agent'] = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0 Safari/537.36'
    )

    try:
        r = requests.get(url, headers=forward_headers, stream=True, timeout=20,
                         allow_redirects=True)
    except requests.exceptions.RequestException as e:
        return f'Proxy error: {e}', 502

    # Build response headers
    resp_headers = {}
    for k, v in r.headers.items():
        if k.lower() not in SKIP_HEADERS | {'content-encoding'}:
            resp_headers[k] = v

    resp_headers['Access-Control-Allow-Origin'] = '*'
    resp_headers['Access-Control-Allow-Headers'] = '*'

    # Rewrite subtitle/m3u8 URLs inside text responses
    content_type = r.headers.get('Content-Type', '').lower()
    if any(t in content_type for t in ('text', 'application/x-mpegurl', 'application/vnd.apple')):
        text = r.text
        # Rewrite absolute URLs in m3u8
        def rewrite(match):
            u = match.group(1)
            if u.startswith('http'):
                return '/proxy?url=' + requests.utils.quote(u, safe='')
            # Relative → make absolute using base URL
            from urllib.parse import urljoin
            abs_u = urljoin(url, u)
            return '/proxy?url=' + requests.utils.quote(abs_u, safe='')
        text = re.sub(r'(https?://[^\s\"\'\n>]+)', lambda m: '/proxy?url=' + requests.utils.quote(m.group(1), safe=''), text)
        return Response(text, status=r.status_code, headers=resp_headers,
                        content_type=content_type)

    return Response(
        stream_with_context(r.iter_content(chunk_size=65536)),
        status=r.status_code,
        headers=resp_headers,
        content_type=r.headers.get('Content-Type', 'application/octet-stream')
    )

@app.route('/proxy', methods=['OPTIONS'])
def proxy_options():
    return Response('', 204, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
        'Access-Control-Allow-Headers': '*',
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
