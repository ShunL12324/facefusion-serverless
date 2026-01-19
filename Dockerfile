# FaceFusion RunPod Serverless Dockerfile
# 基于 NVIDIA CUDA 镜像

FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# 克隆 FaceFusion
WORKDIR /
RUN git clone https://github.com/facefusion/facefusion.git

WORKDIR /facefusion

# 安装 Python 依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install onnxruntime-gpu==1.23.2

# 安装 NVIDIA CUDA 运行时库
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

# 安装 RunPod SDK
RUN pip install runpod requests

# 应用 NSFW patch (禁用内容检查)
COPY patches/disable-nsfw-check.py /tmp/disable-nsfw-check.py
RUN python /tmp/disable-nsfw-check.py /facefusion

# 复制模型下载脚本并预下载模型
COPY download_models.py /tmp/download_models.py
RUN python /tmp/download_models.py standard

# 创建临时目录
RUN mkdir -p /tmp/facefusion_jobs

# 设置 CUDA 库路径
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.12/dist-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH

# 复制配置文件和 handler
COPY configs/ /facefusion/configs/
COPY handler.py /facefusion/handler.py

# 入口
WORKDIR /facefusion
CMD ["python", "handler.py"]
