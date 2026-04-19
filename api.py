import json
import os
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
import uuid
from logger_utils import sys_logger
from fastapi import Request

MODEL_PATH = "zai-org/GLM-OCR"
import time
VLLM_BASE_URL = "http://127.0.0.1:8001/v1"

# Global variable for the client
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    print(f"Initializing vLLM client pointing to {VLLM_BASE_URL}...")
    client = AsyncOpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)
    yield
    # Clean up if necessary
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

class OCRRequest(BaseModel):
    base64_data: str
    file_type: str = None  # Optional
    task: str = "structured"  # text, formula, table, structured, custom
    custom_prompt: str = None

# KTP
DEFAULT_PROMPT_JSON = {
    "NIK": "numeric string (digits only)",
    "nama": "string (alphabetic characters A-Z only)",
    "tempat_tanggal_lahir": "string",
    "jenis_kelamin": "string",
    "alamat": "string",
    "RT_RW": "string",
    "KEL_DESA": "string",
    "KECAMATAN": "string",
    "agama": "string",
    "status_perkawinan": "string",
    "pekerjaan": "string",
    "kewarganegaraan": "string"
}

# F1B
# DEFAULT_PROMPT_JSON = {
#     "Terhitung_Sejak": "",
#     "Nama_Badan_Usaha_instansi_asosiasi": "",
#     "Nomor_Referensi": "",
#     "Nomor_Induk": "",
#     "Nama_Lengkap_Pekerja": "",
#     "Tanggal_Lahir": "",
#     "Keterangan": ""
# }

def decode_base64(base64_str: str):
    try:
        # Remove data URI header if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        return base64.b64decode(base64_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 data: {str(e)}")

@app.post("/ocr")
async def extract_info(request_data: OCRRequest, request: Request):
    start_time = time.time()
    trans_id = f"TR-{uuid.uuid4()}"
    trace_id = request.headers.get("X-TRACE-ID", f"TC-{uuid.uuid4()}")
    client_ip = request.client.host
    endpoint = "/ocr"
    method = "POST"
    func_name = "extract_info"
    caller_info = "[anonymous] as [Guest]"
    
    # Standard log: START
    sys_logger.info(
        trans_id, endpoint, method, func_name, caller_info,
        0, client_ip, trace_id, "START", "Processing OCR request",
        body=f"Base64 Image Data ({len(request_data.base64_data)} bytes)"
    )

    try:
        file_bytes = decode_base64(request_data.base64_data)
        
        # Automatic detection logic
        is_pdf = False
        if request_data.file_type:
            is_pdf = request_data.file_type.lower() == 'pdf'
        else:
            # Check for %PDF header
            is_pdf = file_bytes.startswith(b"%PDF")
        
        if is_pdf:
            result = await process_pdf(file_bytes, task=request_data.task, custom_prompt=request_data.custom_prompt)
        else:
            # Load image once from bytes
            try:
                image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                result = await process_image(image, task=request_data.task, custom_prompt=request_data.custom_prompt)
            except Exception as e:
                result = {"status": "error", "error": str(e)}
                raise HTTPException(status_code=400, detail=f"Failed to open image or detect type: {str(e)}")
        
        exec_time = (time.time() - start_time) * 1000  # ms
        
        # Standard log: STOP (Success)
        sys_logger.info(
            trans_id, endpoint, method, func_name, caller_info,
            exec_time, client_ip, trace_id, "STOP", "OCR request completed",
            result=result
        )
        return result

    except Exception as e:
        exec_time = (time.time() - start_time) * 1000  # ms
        sys_logger.error(
            trans_id, endpoint, method, func_name, caller_info,
            exec_time, client_ip, trace_id, "STOP", f"OCR request failed: {str(e)}",
            error=str(e)
        )
        raise

async def process_image(image: Image.Image, task: str = "structured", custom_prompt: str = None):
    start_time = time.time()
    # Convert PIL Image back to base64 for the OpenAI API
    # Added quality=80 to reduce payload size
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=80)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{img_b64}"

    prep_time = time.time() - start_time
    print(f"DEBUG: Image preparation took {prep_time:.2f}s")

    # Define prompt based on task
    if task == "text":
        prompt_text = "Text Recognition"
    elif task == "formula":
        prompt_text = "formula recognition"
    elif task == "table":
        prompt_text = "table recognition"
    elif task == "custom":
        if custom_prompt:
            # If user didn't provide braces, treat it as a list of fields
            custom_prompt_stripped = custom_prompt.strip()
            if not custom_prompt_stripped.startswith('{'):
                # Split by comma or newline
                import re
                fields = [f.strip() for f in re.split(r'[,\n]+', custom_prompt_stripped) if f.strip()]
                # Create a simple JSON template
                template = {field: "string" for field in fields}
                processed_prompt = json.dumps(template, indent=4)
            else:
                processed_prompt = custom_prompt_stripped
                
            prompt_text = f"Extract information from this document. Use the following template as a guide for the structure and types: {processed_prompt}"
        else:
            prompt_text = f"Extract information from this document. Use the following template as a guide for the structure and types: {json.dumps(DEFAULT_PROMPT_JSON, indent=4)}"
    else:  # Default to structured
        prompt_text = f"Extract information from this document. Use the following template as a guide for the structure and types: {json.dumps(DEFAULT_PROMPT_JSON, indent=4)}"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": data_url}
                },
                {
                    "type": "text",
                    "text": prompt_text
                }
            ],
        }
    ]

    try:
        vllm_start = time.time()
        response = await client.chat.completions.create(
            model=MODEL_PATH,
            messages=messages,
            max_tokens=800,  # Reduced from 2048 for better latency
            temperature=0.1
        )
        vllm_time = time.time() - vllm_start
        print(f"DEBUG: vLLM request took {vllm_time:.2f}s")
        
        output_text = response.choices[0].message.content
        
        # Attempt to parse json if possible, or just return text
        try:
            # Find the first '{' and the last '}' to extract the JSON object
            start_idx = output_text.find('{')
            end_idx = output_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                clean_output = output_text[start_idx:end_idx+1]
                json_result = json.loads(clean_output)
                return {"status": "success", "data": json_result}
            
            return {"status": "success", "data": output_text}
        except Exception:
            return {"status": "success", "data": output_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_pdf(pdf_bytes: bytes, task: str = "structured", custom_prompt: str = None):
    results = []
    try:
        doc = fitz.open("pdf", stream=pdf_bytes)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Better resolution
            
            # Convert pixmap to PIL Image directly in memory
            img_data = pix.tobytes("png")
            page_image = Image.open(io.BytesIO(img_data)).convert("RGB")
            
            # Process this page as an image
            page_result = await process_image(page_image, task=task, custom_prompt=custom_prompt)
            results.append({
                "page": page_num + 1,
                "data": page_result.get("data") if page_result.get("status") == "success" else page_result
            })
            
        doc.close()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8787)
