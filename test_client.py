import requests
import json
import sys
import os

API_URL = "http://localhost:8000/extract"

def test_ocr(image_path):
    if not os.path.isabs(image_path):
        image_path = os.path.abspath(image_path)
    
    payload = {"image_path": image_path}
    
    print(f"Sending request to API for: {image_path}...")
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print("\n--- OCR RESULTS ---")
        print(json.dumps(result, indent=4))
        
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        if response.content:
            print(f"Detail: {response.json().get('detail')}")
    except Exception as e:
        print(f"Failed to connect to API: {e}")
        print("Make sure the server is running in another terminal: ./venv/bin/python api.py")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # Default to a sample in the current dir if none provided
        path = "SAMPLE KTP.jpg"
    
    test_ocr(path)
