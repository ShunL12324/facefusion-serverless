# FaceFusion RunPod Serverless Dockerfile
# Based on NVIDIA CUDA image with Ubuntu 24.04

FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Setup Python (Ubuntu 24.04 has Python 3.12 by default)
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Clone FaceFusion
WORKDIR /
RUN git clone https://github.com/facefusion/facefusion.git

WORKDIR /facefusion

# Install Python dependencies (--break-system-packages for PEP 668)
RUN pip install --upgrade pip --break-system-packages
RUN pip install -r requirements.txt --break-system-packages
RUN pip install onnxruntime-gpu --break-system-packages

# Install NVIDIA CUDA runtime libraries
RUN pip install --break-system-packages \
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
RUN pip install runpod requests --break-system-packages

# Apply NSFW patch (disable content check)
COPY patches/disable-nsfw-check.py /tmp/disable-nsfw-check.py
RUN python /tmp/disable-nsfw-check.py /facefusion

# Copy model download script and pre-download models
COPY download_models.py /tmp/download_models.py
RUN python /tmp/download_models.py standard

# Create temp directory
RUN mkdir -p /tmp/facefusion_jobs

# Set CUDA library path
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.12/dist-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH

# Copy config files and handler
COPY configs/ /facefusion/configs/
COPY handler.py /facefusion/handler.py

# Entrypoint
WORKDIR /facefusion
CMD ["python", "handler.py"]
