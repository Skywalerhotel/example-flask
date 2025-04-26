from flask import Flask, request, Response, render_template_string
import requests

app = Flask(__name__)

# Simple web page
HTML = """
<!doctype html>
<title>Stream Proxy</title>
<h2>Paste the Seedr Video Link:</h2>
<form method="get" action="/play">
  <input type="text" name="url" style="width:500px">
  <input type="submit" value="Play">
</form>

<hr>

<video id="videoPlayer" controls>
  <source id="videoSource" src="" type="video/mp4">
  Your browser does not support the video tag.
</video>

<script>
  document.querySelector("form").onsubmit = function(event) {
    event.preventDefault();
    var url = document.querySelector("input[name='url']").value;
    document.getElementById("videoSource").src = "/play?url=" + encodeURIComponent(url);
    document.getElementById("videoPlayer").load();
    document.getElementById("videoPlayer").play();
  };

  // Double tap to seek (left -10s, right +10s)
  let lastTap = 0;
  document.getElementById("videoPlayer").addEventListener('touchstart', function(event) {
    const currentTime = new Date().getTime();
    const timeDifference = currentTime - lastTap;

    if (timeDifference < 300 && timeDifference > 0) {
      // Double tap detected
      const video = event.target;
      const videoWidth = video.offsetWidth;
      const tapPosition = event.changedTouches[0].clientX;

      if (tapPosition < videoWidth / 2) {
        // Left double tap: skip 10 seconds back
        video.currentTime -= 10;
      } else {
        // Right double tap: skip 10 seconds forward
        video.currentTime += 10;
      }
    }
    lastTap = currentTime;
  });
</script>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/play')
def play_video():
    url = request.args.get('url')
    if not url:
        return "No URL provided.", 400

    def generate():
        with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

    return Response(generate(), content_type='video/mp4', status=206)

if __name__ == "__main__":
    app.run()
