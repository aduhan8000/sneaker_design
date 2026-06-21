"""Lesson 1 — Structuring the Interface
Goal: Flask routes + templates only. No AI, no captcha.
Run: python app.py  →  visit http://localhost:5000
"""
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()                          # loads .env file into environment
app = Flask(__name__)                  # creates the Flask app
app.secret_key = "sneaker-studio-dev-key"  # needed for sessions later

@app.route("/")                        # the / URL maps to this function
def index():
    return render_template("index.html")

@app.route("/studio")                  # the /studio URL
def studio():
    return render_template("studio.html", hcaptcha_site_key="")

@app.route("/history")                 # the /history URL
def history():
    return render_template("history.html", designs=[])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
