import os
import requests
import base64
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
# API_URL = "http://0.0.0.0:8787/ocr"
API_URL = "http://172.28.100.108:8787/ocr"

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
            # Read file and encode to base64
            file_content = file.read()
            base64_data = base64.b64encode(file_content).decode('utf-8')
            
            payload = {
                "base64_data": base64_data
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
