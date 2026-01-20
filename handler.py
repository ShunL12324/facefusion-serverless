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
        "pixel_boost": "512x512",                         # 可选，默认 512x512 (可选 256x256, 1024x1024)
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
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, quote
import requests

# RunPod handler
import runpod

# R2 配置 (从环境变量读取)
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "default")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else ""

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
    "pixel_boost": "512x512",
    "output_video_quality": 80,
    "output_audio_encoder": "aac",
    "execution_providers": "cuda",
    "preset": "serverless",  # 默认使用 serverless 配置
}

# yt-dlp 支持的网站域名模式
YTDLP_SUPPORTED_DOMAINS = [
    # 主流视频平台
    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
    "tiktok.com", "twitter.com", "x.com", "instagram.com", "facebook.com",
    "twitch.tv", "bilibili.com", "douyin.com",
    # 成人网站
    "pornhub.com", "xvideos.com", "xnxx.com", "redtube.com",
    "youporn.com", "xhamster.com", "spankbang.com", "eporner.com",
    "tube8.com", "thumbzilla.com", "xtube.com",
]


def is_ytdlp_url(url: str) -> bool:
    """检查 URL 是否需要 yt-dlp 下载"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 移除 www. 前缀
        if domain.startswith("www."):
            domain = domain[4:]
        # 检查是否匹配支持的域名
        for supported in YTDLP_SUPPORTED_DOMAINS:
            if domain == supported or domain.endswith("." + supported):
                return True
        return False
    except:
        return False


def download_with_ytdlp(url: str, dest_path: str) -> str:
    """使用 yt-dlp 下载视频"""
    import subprocess

    print(f"Downloading with yt-dlp: {url}")

    # 打印当前版本
    try:
        ver = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        print(f"yt-dlp version before update: {ver.stdout.strip()}")
    except:
        pass

    # 尝试更新 yt-dlp
    print("Updating yt-dlp...")
    try:
        update = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                               capture_output=True, text=True, timeout=120)
        print(f"Update result: {update.returncode}")
        if update.stdout:
            print(f"Update stdout: {update.stdout[-500:]}")
        if update.stderr:
            print(f"Update stderr: {update.stderr[-500:]}")
    except Exception as e:
        print(f"Update failed: {e}")

    # 打印更新后版本
    try:
        ver = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        print(f"yt-dlp version after update: {ver.stdout.strip()}")
    except:
        pass

    # 获取目标目录和文件名
    dest_dir = os.path.dirname(dest_path)
    dest_name = os.path.splitext(os.path.basename(dest_path))[0]

    # yt-dlp 命令
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",  # 优先 mp4 格式
        "--no-playlist",              # 不下载播放列表
        "-o", os.path.join(dest_dir, f"{dest_name}.%(ext)s"),
        "--no-warnings",
        url
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        print(f"yt-dlp stderr: {result.stderr}")
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    # 查找下载的文件
    import glob
    downloaded_files = glob.glob(os.path.join(dest_dir, f"{dest_name}.*"))
    if not downloaded_files:
        raise RuntimeError("yt-dlp did not produce any output file")

    downloaded_file = downloaded_files[0]

    # 如果下载的文件名与目标不同，重命名
    if downloaded_file != dest_path:
        actual_ext = os.path.splitext(downloaded_file)[1]
        new_dest = os.path.splitext(dest_path)[0] + actual_ext
        if downloaded_file != new_dest:
            os.rename(downloaded_file, new_dest)
            downloaded_file = new_dest

    print(f"Downloaded to: {downloaded_file}")
    return downloaded_file


def download_file(url: str, dest_path: str) -> str:
    """下载文件到指定路径（自动检测是否使用 yt-dlp）"""

    # 检查是否需要 yt-dlp
    if is_ytdlp_url(url):
        return download_with_ytdlp(url, dest_path)

    # 普通 HTTP 下载
    print(f"Downloading: {url}")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Downloaded to: {dest_path}")
    return dest_path


def _sign(key, msg):
    """HMAC-SHA256 签名"""
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def _get_signature_key(key, date_stamp, region, service):
    """生成 AWS S3 签名密钥"""
    k_date = _sign(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, 'aws4_request')
    return k_signing


def upload_to_r2(file_path: str, object_key: str) -> str:
    """上传文件到 R2 并返回预签名 URL"""
    if not R2_ACCOUNT_ID or not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        raise ValueError("R2 credentials not configured. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY environment variables.")

    print(f"Uploading to R2: {object_key}")
    file_size = os.path.getsize(file_path)
    print(f"  File size: {file_size / (1024 * 1024):.1f} MB")

    # 准备请求
    method = 'PUT'
    service = 's3'
    region = 'auto'
    host = f"{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    endpoint = f"{R2_ENDPOINT}/{R2_BUCKET}/{object_key}"

    # 时间戳
    t = datetime.now(timezone.utc)
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')

    # 确定 Content-Type
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp',
        '.mp4': 'video/mp4', '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska',
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    # 使用 UNSIGNED-PAYLOAD 避免计算大文件哈希
    payload_hash = 'UNSIGNED-PAYLOAD'

    # 规范请求
    canonical_uri = f'/{R2_BUCKET}/{object_key}'
    canonical_querystring = ''
    canonical_headers = (
        f'content-type:{content_type}\n'
        f'host:{host}\n'
        f'x-amz-content-sha256:{payload_hash}\n'
        f'x-amz-date:{amz_date}\n'
    )
    signed_headers = 'content-type;host;x-amz-content-sha256;x-amz-date'
    canonical_request = (
        f'{method}\n{canonical_uri}\n{canonical_querystring}\n'
        f'{canonical_headers}\n{signed_headers}\n{payload_hash}'
    )

    # 待签名字符串
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
    string_to_sign = (
        f'{algorithm}\n{amz_date}\n{credential_scope}\n'
        f'{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
    )

    # 计算签名
    signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # 授权头
    authorization_header = (
        f'{algorithm} Credential={R2_ACCESS_KEY_ID}/{credential_scope}, '
        f'SignedHeaders={signed_headers}, Signature={signature}'
    )

    # 发送请求（流式上传）
    headers = {
        'Content-Type': content_type,
        'Host': host,
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': amz_date,
        'Authorization': authorization_header,
        'Content-Length': str(file_size),
    }

    with open(file_path, 'rb') as f:
        response = requests.put(endpoint, data=f, headers=headers, timeout=3600)

    if response.status_code not in [200, 201]:
        raise Exception(f"R2 upload failed: {response.status_code} - {response.text}")

    print(f"  Upload successful!")
    return object_key


def generate_presigned_url(object_key: str, expires_in: int = 3600) -> str:
    """生成 R2 预签名下载 URL"""
    method = 'GET'
    service = 's3'
    region = 'auto'
    host = f"{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # 时间戳
    t = datetime.now(timezone.utc)
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')

    # URL encode the object key (keep slashes for canonical URI)
    encoded_key_for_uri = quote(object_key, safe='/')
    encoded_key_for_url = quote(object_key, safe='')
    canonical_uri = f'/{R2_BUCKET}/{encoded_key_for_uri}'

    credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
    credential = f'{R2_ACCESS_KEY_ID}/{credential_scope}'

    canonical_querystring = (
        f'X-Amz-Algorithm=AWS4-HMAC-SHA256'
        f'&X-Amz-Credential={quote(credential, safe="")}'
        f'&X-Amz-Date={amz_date}'
        f'&X-Amz-Expires={expires_in}'
        f'&X-Amz-SignedHeaders=host'
    )

    canonical_headers = f'host:{host}\n'
    signed_headers = 'host'
    payload_hash = 'UNSIGNED-PAYLOAD'

    canonical_request = (
        f'{method}\n{canonical_uri}\n{canonical_querystring}\n'
        f'{canonical_headers}\n{signed_headers}\n{payload_hash}'
    )

    # 待签名字符串
    algorithm = 'AWS4-HMAC-SHA256'
    string_to_sign = (
        f'{algorithm}\n{amz_date}\n{credential_scope}\n'
        f'{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
    )

    # 计算签名
    signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # 完整 URL (use encoded key for URL path)
    presigned_url = f'{R2_ENDPOINT}/{R2_BUCKET}/{encoded_key_for_url}?{canonical_querystring}&X-Amz-Signature={signature}'
    return presigned_url


def upload_to_storage(file_path: str, job_id: str) -> str:
    """
    上传结果文件到 R2 并返回预签名 URL
    """
    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    print(f"File size {file_size} bytes, uploading to R2")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_key = f"facefusion/output/{job_id}_{timestamp}{ext}"

    upload_to_r2(file_path, object_key)

    # 生成 24 小时有效的预签名 URL
    presigned_url = generate_presigned_url(object_key, expires_in=86400)
    return presigned_url


def get_file_extension(url: str) -> str:
    """从 URL 获取文件扩展名"""
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext else '.mp4'


def run_facefusion(job_dir: str, source_path: str, target_path: str, output_path: str, params: dict) -> bool:
    """运行 FaceFusion headless 命令"""

    # 确保临时目录存在
    os.makedirs("/tmp", exist_ok=True)
    os.makedirs("/var/tmp", exist_ok=True)

    # 设置 CUDA 内存分配策略，避免碎片化
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    os.environ["ORT_CUDA_ARENA_EXTEND_STRATEGY"] = "kSameAsRequested"

    # 打印 GPU 状态
    try:
        gpu_info = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,memory.used", "--format=csv"],
                                   capture_output=True, text=True, timeout=10)
        print(f"GPU Status:\n{gpu_info.stdout}")
    except Exception as e:
        print(f"nvidia-smi failed: {e}")

    # 打印调试信息
    print(f"Python: {sys.executable}")
    print(f"CWD: {os.getcwd()}")
    print(f"Source exists: {os.path.exists(source_path)}, size: {os.path.getsize(source_path) if os.path.exists(source_path) else 0}")
    print(f"Target exists: {os.path.exists(target_path)}, size: {os.path.getsize(target_path) if os.path.exists(target_path) else 0}")

    # 检查 facefusion.py 是否存在
    facefusion_script = os.path.join(FACEFUSION_PATH, "facefusion.py")
    print(f"FaceFusion script exists: {os.path.exists(facefusion_script)}")

    # 先测试 FaceFusion 是否能正常导入
    test_cmd = [sys.executable, "-c", "import facefusion; print('FaceFusion OK')"]
    test_result = subprocess.run(test_cmd, cwd=FACEFUSION_PATH, capture_output=True, text=True)
    print(f"Import test: {test_result.stdout} {test_result.stderr}")

    # 构建命令 - 使用简化参数
    cmd = [
        sys.executable, "facefusion.py", "headless-run",
        "-s", source_path,
        "-t", target_path,
        "-o", output_path,
        "--temp-dir", job_dir,  # 使用 job 目录作为临时目录，避免 /tmp 空间不足
        "--processors", "face_swapper", "face_enhancer", "expression_restorer",
        "--face-swapper-model", params.get("face_swapper_model", DEFAULT_PARAMS["face_swapper_model"]),
        "--face-swapper-pixel-boost", params.get("pixel_boost", DEFAULT_PARAMS["pixel_boost"]),
        "--face-swapper-weight", "0.85",
        "--face-enhancer-model", params.get("face_enhancer_model", DEFAULT_PARAMS["face_enhancer_model"]),
        "--face-enhancer-blend", str(params.get("face_enhancer_blend", DEFAULT_PARAMS["face_enhancer_blend"])),
        "--expression-restorer-model", "live_portrait",
        "--expression-restorer-factor", "80",
        "--face-selector-mode", "one",
        "--face-detector-model", "many",
        "--face-detector-score", "0.35",
        "--face-landmarker-model", "many",
        "--face-mask-types", "box", "occlusion",
        "--face-occluder-model", "xseg_3",
        "--face-mask-blur", "0.3",
        "--output-video-quality", str(params.get("output_video_quality", DEFAULT_PARAMS["output_video_quality"])),
        "--execution-providers", "cuda",
        "--log-level", "debug",
    ]

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
        # 包含更详细的错误信息
        error_details = f"Code: {result.returncode}\n"
        if result.stdout:
            error_details += f"STDOUT: {result.stdout[-2000:]}\n"  # 最后2000字符
        if result.stderr:
            error_details += f"STDERR: {result.stderr[-2000:]}"
        raise RuntimeError(f"FaceFusion failed:\n{error_details}")

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
        source_path = download_file(source_url, source_path)  # 使用实际下载路径

        # 下载目标文件
        target_ext = get_file_extension(target_url)
        target_path = os.path.join(job_dir, f"target{target_ext}")
        target_path = download_file(target_url, target_path)  # 使用实际下载路径

        # 输出路径 (使用目标文件的实际扩展名)
        actual_target_ext = os.path.splitext(target_path)[1]
        output_path = os.path.join(job_dir, f"output{actual_target_ext}")

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
        output_url = upload_to_storage(output_path, job_id)

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
