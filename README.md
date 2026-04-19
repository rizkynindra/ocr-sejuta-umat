## before install everything

Make sure to use Python3.12

## what to install

uv venv --python 3.12
source .venv/bin/activate
uv pip install -U vllm --torch-backend=auto

# install the nightly build of vLLM for GLM-4.7
uv pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly

# install transformers from source
uv pip install git+https://github.com/huggingface/transformers.git


# Run on RTX 3090
CUDA_VISIBLE_DEVICES=0 VLLM_USE_V1=0 vllm serve zai-org/GLM-OCR \
    --port 8001 \
    --trust-remote-code \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.85 \
    --speculative-config.method mtp \
    --speculative-config.num_speculative_tokens 1 \
    --enable-prefix-caching


# Run on L4
CUDA_VISIBLE_DEVICES=0 VLLM_USE_V1=0 vllm serve zai-org/GLM-OCR \
    --port 8001 \
    --trust-remote-code \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.85 \
    --speculative-config.method mtp \
    --speculative-config.num_speculative_tokens 1 \
    --enable-prefix-caching