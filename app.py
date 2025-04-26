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
  <source id="videoSource" src="" type="video/x-matroska">
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

    # Handling HTTP Range requests to support seeking
    range_header = request.headers.get('Range', None)
    headers = {}
    if range_header:
        headers['Range'] = range_header

    def generate():
        with requests.get(url, stream=True, headers=headers) as r:
            if r.status_code == 206:  # Partial content
                content_range = r.headers.get('Content-Range')
                total_length = int(content_range.split('/')[-1]) if content_range else 0
            else:
                total_length = 0

            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

    return Response(generate(), content_type='video/x-matroska', status=206)

if __name__ == "__main__":
    app.run(debug=True)
