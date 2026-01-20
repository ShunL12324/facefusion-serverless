# FaceFusion RunPod Serverless Dockerfile
# Using CUDA 12.2 for RunPod compatibility

FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies and Python 3.12
RUN apt-get update && apt-get install -y \
    software-properties-common \
    git \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Setup Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

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

# Install RunPod SDK and yt-dlp (use pip install --upgrade to get latest)
RUN pip install runpod requests
RUN pip install --upgrade yt-dlp

# Apply NSFW patch (disable content check)
COPY patches/disable-nsfw-check.py /tmp/disable-nsfw-check.py
RUN python /tmp/disable-nsfw-check.py /facefusion

# Copy model download script and pre-download models
COPY download_models.py /tmp/download_models.py
RUN python /tmp/download_models.py standard

# Create temp directories with proper permissions
RUN mkdir -p /tmp /var/tmp /tmp/facefusion_jobs && \
    chmod 1777 /tmp /var/tmp

# Set temp directory environment variable
ENV TMPDIR=/tmp
ENV TEMP=/tmp
ENV TMP=/tmp

# Set CUDA library path
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.12/dist-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH

# Copy config files and handler
COPY configs/ /facefusion/configs/
COPY handler.py /facefusion/handler.py

# Entrypoint
WORKDIR /facefusion
CMD ["python", "handler.py"]
