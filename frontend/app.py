from flask import Flask, render_template
from urllib.parse import quote as url_quote
app = Flask(__name__, template_folder="templates")

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True)
