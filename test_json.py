from transformers import AutoProcessor, AutoModelForImageTextToText
import torch
import json

MODEL_PATH = "zai-org/GLM-OCR"

# Define the target extraction structure
prompt_json = {
    "NIK": "",
    "nama": "",
    "tempat_tanggal_lahir": "",
    "jenis_kelamin": "",
    "alamat": {
        "RT_RW": "",
        "KEL_DESA": "",
        "KECAMATAN": "",
        "KOTA_KABUPATEN": ""
    },
    "agama": "",
    "status_perkawinan": "",
    "pekerjaan": "",
    "kewarganegaraan": "",
    "berlaku_hingga": ""
}

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "url": "/Users/rizkynindra.sukma/PycharmProjects/GLM_OCR/SAMPLE KTP.jpg"
            },
            {
                "type": "text",
                "text": f"Extract information from this document into the following JSON format: {json.dumps(prompt_json, indent=4)}"
            }
        ],
    }
]

print("Loading model and processor...")
processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
model = AutoModelForImageTextToText.from_pretrained(
    pretrained_model_name_or_path=MODEL_PATH,
    torch_dtype="auto",
    device_map="auto",
    trust_remote_code=True,
)

print("Preparing inputs...")
inputs = processor.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_dict=True,
    return_tensors="pt"
).to(model.device)

inputs.pop("token_type_ids", None)

print("Generating output...")
generated_ids = model.generate(**inputs, max_new_tokens=8192)
output_text = processor.decode(generated_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)

print("\n--- RESULTS ---")
print(output_text)
