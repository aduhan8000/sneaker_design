"""Lesson 1 — Structuring the Interface
Goal: Flask routes + templates only. No AI, no captcha.
Run: python app.py  →  visit http://localhost:5000
"""
import os,json,requests,base64
from groq import Groq


from flask import Flask,render_template,jsonify,request
import requests
from dotenv import load_dotenv
GROQ_API_KEY=os.environ.get("GROQ_API_KEY","")
groq_client=Groq(api_key=GROQ_API_KEY)
HCAPTCHA_SITE_KEY=os.environ.get("HCAPTCHA_SITE_KEY","")

DESIGN_PROMPT = """You are an expert sneaker designer. Generate a detailed concept based on:
Style: {style}, Primary Color: {primary_color}, Accent Color: {accent_color},
Material: {material}, Occasion: {occasion}, Inspiration: {inspiration}

Respond with raw JSON only — no markdown, no explanation.
{{"name":"2-4 word creative name","tagline":"punchy tagline max 10 words",
"description":"2-3 sentence design description","materials":["mat1","mat2","mat3"],
"colorways":[{{"name":"colorway name","sole":"#hex","upper":"#hex","accent":"#hex",
"lace":"#hex","tongue":"#hex"}}],"features":["feat1","feat2","feat3","feat4"],
"sole_type":"sole tech description","target_audience":"who this is for",
"retail_price":"$XXX","style_tags":["tag1","tag2","tag3"]}}
Generate exactly 3 colorways. All hex codes must be valid #RRGGBB."""


load_dotenv()                          # loads .env file into environment
app = Flask(__name__)    
              # creates the Flask app
app.secret_key = "sneaker-studio-dev-key"  # needed for sessions later
def get_prefs(data):
    fields = [("style","casual"),("primary_color","white"),("accent_color","black"),
              ("material","leather"),("occasion","everyday"),("inspiration","")]
    return {k: data.get(k, d) for k, d in fields}


def generate_concept(prefs):
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY not set.")
    chat = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sneaker design expert. Pure JSON only."},
            {"role": "user",   "content": DESIGN_PROMPT.format(**prefs)},
        ],
        temperature=0.85, max_tokens=1200,
    )
    raw = chat.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip().rstrip("```").strip())


@app.route("/")                        # the / URL maps to this function
def index():
    return render_template("index.html")

@app.route("/studio")                  # the /studio URL
def studio():
    return render_template("studio.html", hcaptcha_site_key="")

@app.route("/history")                 # the /history URL
def history():
    return render_template("history.html", designs=[])
# app.py — the /generate route in Lesson 3
@app.route("/generate", methods=["POST"])
def generate():
    
    data  = request.get_json(silent=True) or request.form

    # GATE 1: Did the request include a CAPTCHA token at all?
    token = data.get("h-captcha-response", "")
    if not token:
        return jsonify({"error": "Please complete the CAPTCHA."}), 400

    # GATE 2: Is the token genuine? (calls hCaptcha's servers)
    if not verify_hcaptcha(token):
        return jsonify({"error": "CAPTCHA verification failed."}), 400

    # Only reaches here if BOTH gates passed
    # NOW the expensive AI work begins
    prefs = get_prefs(data)
    try:
        concept = generate_concept(prefs)  # calls Groq
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Malformed AI response: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Concept generation failed: {e}"}), 500
    return jsonify({"success": True, "concept": concept, "prefs": prefs})


def verify_hcaptcha(token):
    try:
        # Flask sends a POST request to hCaptcha's server
        # data= sends form-encoded values (like an HTML form)
        # "secret" = the private secret key
        # "response" = the token the user received
        r = requests.post(
            HCAPTCHA_VERIFY_URL,
            data={"secret": HCAPTCHA_SECRET, "response": token},
            timeout=5  # wait max 5 seconds for hCaptcha to reply
        )

        # hCaptcha replies with JSON like:
        # {"success": true}  — token is valid, human confirmed
        # {"success": false} — token is fake or already used
        return r.json().get("success", False)

    except Exception:
        # If hCaptcha's server is unreachable, fail safely
        # Return False — do not allow the request through
        return False
HF_API_KEY=os.environ("HUGGINGFACE_API_KEY","")
HF_IMAGE_URL="https://rout.geter.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
def hex_to_color_name(h):
    h=h.lstrip('#').lower()
    try:
        r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    except:
        return h
    mx,mn=max(r,g,b),min(r,g,b)
    br,sat=mx/255,(mx-mn)/mx if mx else 0
    if br <0.15:
        return "black"
    if br>0.88 and sat<0.15 :
        return "white"
    if sat<0.18:
        return "dark gray" if br<0.4 else "gray" if br<0.65 else "light gray"
    if mx==r: return ("orange" if g>120 else "dark orange") if g> b+60 else "magenta" if b >g+40 else 'red'
    if mx==g: 
        return 'yellow-green' if r>b+60 else "cyan-green" if b>r+40 else 'green'
    if mx==b:
        return "purple" if r >g+60 else "cyan" if g>r +40 else 'blue' 
    return "colorful"
# app.py — building the image prompt from the user's choices
def build_image_prompt(prefs):
    # Translate hex colours to plain English (explained in Topic 3)
    p = hex_to_color_name(prefs["primary_color"])   # e.g. "dark navy"
    a = hex_to_color_name(prefs["accent_color"])    # e.g. "gold"

    
    prompt = (
        f"Professional product photography of a {prefs['style']} sneaker, "
        f"{p} {prefs['material']} upper, {a} accent, {a} heel, white sole, "
        f"side view, white background, sharp focus, 8k, shoe only"
    )

    # Add the inspiration theme if the user typed one
    if prefs.get("inspiration"):
        prompt += f", {prefs['inspiration']} theme"
    

    return prompt


def generate_sneaker_image(prompt):
    if not HF_API_KEY:
        return None

    try:
        # Send the prompt to HuggingFace FLUX model
        # json={"inputs": prompt} sends the prompt as a JSON body
        # timeout=60 — image generation takes up to 60 seconds
        r = requests.post(
            HF_IMAGE_URL,
            headers={
                "Authorization": f"Bearer {HF_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"inputs": prompt},
            timeout=60
        )

        # Check if the response is an image (not an error message)
        # r.status_code == 200 means the request succeeded
        # r.headers["content-type"].startswith("image") means
        #   the response contains image data, not text or JSON
        if r.status_code == 200 and r.headers.get("content-type","").startswith("image"):

            
            mime = r.headers["content-type"].split(";")[0].strip()
            return f"data:{mime};base64,{base64.b64encode(r.content).decode()}"
           

    except Exception:
        pass

    return None

# HOW THE IMAGE PROMPT TRAVELS FROM /generate TO /generate-image

# Step 1: /generate calls Groq and gets the concept JSON
# Then it builds the image prompt and EMBEDS it inside the concept:
@app.route("/generate", methods=["POST"])
def generate():
    # ... captcha check, get_prefs, generate_concept ...
    concept["image_prompt"] = build_image_prompt(prefs)
    #                        ↑ added to the concept before returning
    return jsonify({"success": True, "concept": concept, "prefs": prefs})

# Step 2: JavaScript receives the concept and renders it on screen
# Then it IMMEDIATELY starts the image request using the embedded prompt:
# fetchImage(d.concept.image_prompt)

# Step 3: /generate-image receives the prompt and calls HuggingFace
@app.route("/generate-image", methods=["POST"])
def generate_image():
    data   = request.get_json(silent=True) or {}
    prompt = data.get("image_prompt", "")

    # Gate 1: no prompt provided
    if not prompt:
        return jsonify({"error": "No image prompt."}), 400

    # Gate 2: no HuggingFace API key configured
    # 503 = Service Unavailable (the image service is not set up)
    if not HF_API_KEY:
        return jsonify({"error": "HF_API_KEY not configured."}), 503

    # Call HuggingFace and return the image as a data URI
    image_url = generate_sneaker_image(prompt)
    if not image_url:
        return jsonify({"error": "Image generation failed. Try again."}), 500
    
    return jsonify({"success": True, "image_url": image_url})



if __name__ == "__main__":
    app.run(debug=True, port=5000)
