"""
FaceFusion RunPod Serverless Handler
=====================================
接收换脸请求，处理视频/图片，返回结果

输入格式:
{
    "input": {
        "source_url": "https://xxx/source_face.jpg",      # 源脸图片 URL
        "target_url": "https://xxx/target_video.mp4",     # 目标视频/图片 URL
        "face_swapper_model": "inswapper_128_fp16",       # 可选，默认 inswapper_128_fp16
        "face_enhancer_model": "gpen_bfr_512",            # 可选，默认 gpen_bfr_512
        "face_enhancer_blend": 80,                        # 可选，默认 80
        "pixel_boost": "256x256",                         # 可选，默认 256x256
        "output_video_quality": 80,                       # 可选，默认 80
        "webhook_url": "https://xxx/callback"             # 可选，完成后回调
    }
}

输出格式:
{
    "output_url": "https://xxx/result.mp4",  # 结果文件 URL (上传到云存储)
    "status": "success",
    "processing_time": 123.45
}
"""

import os
import sys
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse
import requests

# RunPod handler
import runpod

# 配置
FACEFUSION_PATH = "/facefusion"
MODELS_PATH = "/facefusion/.assets/models"
TEMP_DIR = "/tmp/facefusion_jobs"
CONFIGS_PATH = "/facefusion/configs"

# 预制配置
PRESET_CONFIGS = {
    "fast": "video_fast.ini",
    "quality": "high_quality.ini",
    "serverless": "serverless.ini"
}

# 默认参数
DEFAULT_PARAMS = {
    "face_swapper_model": "inswapper_128_fp16",
    "face_enhancer_model": "gpen_bfr_512",
    "face_enhancer_blend": 80,
    "pixel_boost": "256x256",
    "output_video_quality": 80,
    "output_audio_encoder": "aac",
    "execution_providers": "cuda",
    "preset": "serverless",  # 默认使用 serverless 配置
}


def download_file(url: str, dest_path: str) -> str:
    """下载文件到指定路径"""
    print(f"Downloading: {url}")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Downloaded to: {dest_path}")
    return dest_path


def upload_to_storage(file_path: str) -> str:
    """
    上传结果文件到云存储
    这里需要根据你的存储方案实现
    可选方案: AWS S3, Cloudflare R2, RunPod 内置存储等
    """
    # 方案1: 使用 RunPod 的内置文件存储 (如果启用)
    # 返回文件的 base64 编码 (适合小文件)

    # 方案2: 上传到 S3/R2 (推荐大文件)
    # 需要配置环境变量: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET

    # 暂时返回本地路径，实际使用时需要实现上传逻辑
    import base64

    file_size = os.path.getsize(file_path)

    # 小于 10MB 的文件返回 base64
    if file_size < 10 * 1024 * 1024:
        with open(file_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:video/mp4;base64,{encoded}"

    # 大文件需要上传到云存储
    # TODO: 实现 S3/R2 上传
    raise ValueError(f"File too large ({file_size} bytes). Please configure cloud storage upload.")


def get_file_extension(url: str) -> str:
    """从 URL 获取文件扩展名"""
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext else '.mp4'


def run_facefusion(job_dir: str, source_path: str, target_path: str, output_path: str, params: dict) -> bool:
    """运行 FaceFusion headless 命令"""

    # 构建命令
    cmd = [
        sys.executable, "facefusion.py", "headless-run",
        "-s", source_path,
        "-t", target_path,
        "-o", output_path,
    ]

    # 使用预制配置文件
    preset = params.get("preset", "serverless")
    if preset in PRESET_CONFIGS:
        config_path = os.path.join(CONFIGS_PATH, PRESET_CONFIGS[preset])
        if os.path.exists(config_path):
            cmd.extend(["--config-path", config_path])

    # 添加自定义参数（会覆盖配置文件）
    cmd.extend([
        "--processors", "face_swapper", "face_enhancer",
        "--face-swapper-model", params.get("face_swapper_model", DEFAULT_PARAMS["face_swapper_model"]),
        "--face-swapper-pixel-boost", params.get("pixel_boost", DEFAULT_PARAMS["pixel_boost"]),
        "--face-enhancer-model", params.get("face_enhancer_model", DEFAULT_PARAMS["face_enhancer_model"]),
        "--face-enhancer-blend", str(params.get("face_enhancer_blend", DEFAULT_PARAMS["face_enhancer_blend"])),
        "--output-video-quality", str(params.get("output_video_quality", DEFAULT_PARAMS["output_video_quality"])),
        "--output-audio-encoder", params.get("output_audio_encoder", DEFAULT_PARAMS["output_audio_encoder"]),
        "--execution-providers", params.get("execution_providers", DEFAULT_PARAMS["execution_providers"]),
        "--log-level", "info",
    ])

    print(f"Running command: {' '.join(cmd)}")

    # 执行
    result = subprocess.run(
        cmd,
        cwd=FACEFUSION_PATH,
        capture_output=True,
        text=True,
        timeout=3600  # 1小时超时
    )

    print(f"STDOUT: {result.stdout}")
    if result.stderr:
        print(f"STDERR: {result.stderr}")

    if result.returncode != 0:
        raise RuntimeError(f"FaceFusion failed with code {result.returncode}: {result.stderr}")

    return os.path.exists(output_path)


def handler(job: dict) -> dict:
    """
    RunPod Serverless Handler
    """
    start_time = time.time()
    job_input = job.get("input", {})

    # 验证必需参数
    source_url = job_input.get("source_url")
    target_url = job_input.get("target_url")

    if not source_url or not target_url:
        return {"error": "Missing required parameters: source_url and target_url"}

    # 创建工作目录
    job_id = job.get("id", f"job_{int(time.time())}")
    job_dir = os.path.join(TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        # 下载源文件
        source_ext = get_file_extension(source_url)
        source_path = os.path.join(job_dir, f"source{source_ext}")
        download_file(source_url, source_path)

        # 下载目标文件
        target_ext = get_file_extension(target_url)
        target_path = os.path.join(job_dir, f"target{target_ext}")
        download_file(target_url, target_path)

        # 输出路径
        output_path = os.path.join(job_dir, f"output{target_ext}")

        # 运行换脸
        params = {
            "preset": job_input.get("preset", DEFAULT_PARAMS["preset"]),
            "face_swapper_model": job_input.get("face_swapper_model", DEFAULT_PARAMS["face_swapper_model"]),
            "face_enhancer_model": job_input.get("face_enhancer_model", DEFAULT_PARAMS["face_enhancer_model"]),
            "face_enhancer_blend": job_input.get("face_enhancer_blend", DEFAULT_PARAMS["face_enhancer_blend"]),
            "pixel_boost": job_input.get("pixel_boost", DEFAULT_PARAMS["pixel_boost"]),
            "output_video_quality": job_input.get("output_video_quality", DEFAULT_PARAMS["output_video_quality"]),
        }

        success = run_facefusion(job_dir, source_path, target_path, output_path, params)

        if not success or not os.path.exists(output_path):
            return {"error": "Face swap processing failed - output file not created"}

        # 上传结果
        output_url = upload_to_storage(output_path)

        processing_time = time.time() - start_time

        return {
            "output_url": output_url,
            "status": "success",
            "processing_time": round(processing_time, 2),
            "params_used": params
        }

    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "processing_time": round(time.time() - start_time, 2)
        }

    finally:
        # 清理临时文件
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)


# RunPod 入口
runpod.serverless.start({"handler": handler})
