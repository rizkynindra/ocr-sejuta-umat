import os
import requests
import base64
import io
from PIL import Image
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
API_URL = "http://127.0.0.1:8787/ocr"
# API_URL = "http://172.28.100.108:8787/ocr"

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    
    if file:
        try:
            # Read file content
            file_content = file.read()
            original_size = len(file_content)
            
            # Threshold: 700 KB (716,800 bytes)
            SIZE_THRESHOLD = 700 * 1024
            
            if original_size > SIZE_THRESHOLD:
                try:
                    # Try to open as image
                    img = Image.open(io.BytesIO(file_content))
                    
                    # Resize to 85% of original dimensions
                    width, height = img.size
                    new_size = (int(width * 0.85), int(height * 0.85))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Compress to 85% quality
                    buffer = io.BytesIO()
                    # Convert to RGB if it has alpha channel (JPEG doesn't support RGBA)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    img.save(buffer, format="JPEG", quality=85)
                    file_content = buffer.getvalue()
                    print(f"Compressed large file from {original_size} to {len(file_content)} bytes")
                except Exception as img_err:
                    # If it's not a standard image or PIL fails, proceed with original content
                    print(f"Skipping compression: {str(img_err)}")
            
            # Get task and custom prompt from form
            task = request.form.get('task', 'structured')
            custom_prompt = request.form.get('custom_prompt', '')

            # Encode to base64
            base64_data = base64.b64encode(file_content).decode('utf-8')
            
            payload = {
                "base64_data": base64_data,
                "task": task,
                "custom_prompt": custom_prompt
            }
            
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    # Using 5001 to avoid conflict with standard ports
    app.run(host='0.0.0.0', port=5001, debug=True)
