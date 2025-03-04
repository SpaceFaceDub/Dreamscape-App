import os
import json
import openai
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Load API key securely
openai.api_key = os.getenv("OPENAI_API_KEY")

# Debug: Check if API key is set
print("Loaded API Key:", openai.api_key)

if not openai.api_key:
    print("⚠️ ERROR: OpenAI API Key is missing!")
    exit(1)  # Stop if key is missing

# Ensure the folder for generated images exists
GALLERY_FOLDER = os.path.join('static', 'dream_art')
os.makedirs(GALLERY_FOLDER, exist_ok=True)

# JSON file to store gallery metadata
GALLERY_JSON = "gallery.json"

def save_image_metadata(title, prompt, filename):
    """Save metadata for each generated image into gallery.json."""
    data = []
    if os.path.exists(GALLERY_JSON):
        with open(GALLERY_JSON, "r") as f:
            try:
                data = json.load(f)
            except Exception:
                data = []
    data.append({
        "title": title,
        "prompt": prompt,
        "filename": filename,
        "timestamp": datetime.utcnow().isoformat()
    })
    with open(GALLERY_JSON, "w") as f:
        json.dump(data, f, indent=2)

def generate_image_prompt(dream_text):
    """
    Use GPT-3.5 Turbo to generate a vivid, detailed prompt for DALL·E.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at writing AI image prompts. Generate a vivid, detailed artistic description based on the user's dream."},
                {"role": "user", "content": dream_text}
            ],
            temperature=0.7,
            max_tokens=100
        )
        prompt = response['choices'][0]['message']['content'].strip()
        return prompt
    except Exception as e:
        print(f"⚠️ Error generating prompt: {e}")
        return dream_text  # Fallback

def generate_dalle_image(prompt):
    """
    Call the DALL·E API to generate an image based on the provided prompt.
    """
    try:
        response = openai.Image.create(
            model="dall-e-3",  # Ensure using latest model
            prompt=prompt,
            n=1,
            size="1024x1024",  # Use supported size
            quality="standard"  # Optional: "hd" for higher quality
        )
        image_url = response['data'][0]['url']
        return image_url
    except Exception as e:
        print(f"⚠️ Error generating image: {e}")
        return None

def download_image(url, filename):
    """
    Download an image from a URL and save it to the specified filename.
    """
    try:
        img_data = requests.get(url).content
        with open(filename, 'wb') as handler:
            handler.write(img_data)
        return True
    except Exception as e:
        print(f"⚠️ Error downloading image: {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        dream_title = request.form.get('dream_title', 'Untitled Dream')
        dream_text = request.form.get('dream_text', '')
        if not dream_text:
            flash("Please enter your dream details.", "danger")
            return redirect(url_for('index'))
        
        # Generate a detailed prompt using GPT
        image_prompt = generate_image_prompt(dream_text)
        print("Generated DALL·E prompt:", image_prompt)
        
        # Generate an image with DALL·E
        image_url = generate_dalle_image(image_prompt)
        if not image_url:
            flash("⚠️ Error: Failed to generate image.", "danger")
            return redirect(url_for('index'))
        
        # Create a unique filename based on timestamp
        filename = f"{int(datetime.utcnow().timestamp())}.png"
        filepath = os.path.join(GALLERY_FOLDER, filename)
        
        if not download_image(image_url, filepath):
            flash("⚠️ Error: Failed to download the image.", "danger")
            return redirect(url_for('index'))
        
        # Save metadata
        save_image_metadata(dream_title, image_prompt, filename)
        
        return render_template('result.html', 
                               dream_title=dream_title,
                               dream_text=dream_text,
                               generated_prompt=image_prompt,
                               image_filename=filename)
    return render_template('index.html')

@app.route('/gallery')
def gallery():
    data = []
    if os.path.exists(GALLERY_JSON):
        with open(GALLERY_JSON, "r") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print("⚠️ Error loading gallery data:", e)
    return render_template("gallery.html", images=data)

if __name__ == '__main__':
    app.run(debug=True)
