from flask import Flask, render_template_string
import requests

app = Flask(__name__)

@app.route('/')
def preview_website():
    # Fetch the website content using requests
    response = requests.get('http://col3neg.com')
    
    # Return the raw HTML of the website
    return render_template_string(response.text)

if __name__ == "__main__":
    app.run(debug=True)
