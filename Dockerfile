# FaceFusion RunPod Serverless Dockerfile
# Using CUDA 12.2 for RunPod compatibility

FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Setup Python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Clone FaceFusion
WORKDIR /
RUN git clone https://github.com/facefusion/facefusion.git

WORKDIR /facefusion

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install onnxruntime-gpu

# Install NVIDIA CUDA runtime libraries
RUN pip install \
    nvidia-cublas-cu12 \
    nvidia-cudnn-cu12 \
    nvidia-cufft-cu12 \
    nvidia-curand-cu12 \
    nvidia-cusolver-cu12 \
    nvidia-cusparse-cu12 \
    nvidia-cuda-runtime-cu12 \
    nvidia-cuda-nvrtc-cu12 \
    nvidia-nvjitlink-cu12

# Install RunPod SDK
RUN pip install runpod requests

# Apply NSFW patch (disable content check)
COPY patches/disable-nsfw-check.py /tmp/disable-nsfw-check.py
RUN python /tmp/disable-nsfw-check.py /facefusion

# Copy model download script and pre-download models
COPY download_models.py /tmp/download_models.py
RUN python /tmp/download_models.py standard

# Create temp directory
RUN mkdir -p /tmp/facefusion_jobs

# Set CUDA library path
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH

# Copy config files and handler
COPY configs/ /facefusion/configs/
COPY handler.py /facefusion/handler.py

# Entrypoint
WORKDIR /facefusion
CMD ["python", "handler.py"]
