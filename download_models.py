"""
预下载 FaceFusion 核心模型
基于 FaceFusion 源码提取的准确模型路径
"""

import os
import sys
import urllib.request
from pathlib import Path

# 模型存放路径
MODELS_DIR = Path("/facefusion/.assets/models")

# HuggingFace 基础 URL 模板
# 格式: https://huggingface.co/facefusion/{repo}/resolve/main/{filename}
def hf_url(repo: str, filename: str) -> str:
    return f"https://huggingface.co/facefusion/{repo}/resolve/main/{filename}"


# ============================================================
# 核心模型（必需）- 来自 FaceFusion 源码
# ============================================================

CORE_MODELS = {
    # Face Detector (face_detector.py) - 使用 many 模式需要所有模型
    "yoloface_8n.onnx": hf_url("models-3.0.0", "yoloface_8n.onnx"),
    "yoloface_8n.hash": hf_url("models-3.0.0", "yoloface_8n.hash"),
    "retinaface_10g.onnx": hf_url("models-3.0.0", "retinaface_10g.onnx"),
    "retinaface_10g.hash": hf_url("models-3.0.0", "retinaface_10g.hash"),
    "scrfd_2.5g.onnx": hf_url("models-3.0.0", "scrfd_2.5g.onnx"),
    "scrfd_2.5g.hash": hf_url("models-3.0.0", "scrfd_2.5g.hash"),
    "yunet_2023_mar.onnx": hf_url("models-3.4.0", "yunet_2023_mar.onnx"),
    "yunet_2023_mar.hash": hf_url("models-3.4.0", "yunet_2023_mar.hash"),

    # Face Landmarker (face_landmarker.py) - 使用 many 模式
    "2dfan4.onnx": hf_url("models-3.0.0", "2dfan4.onnx"),
    "2dfan4.hash": hf_url("models-3.0.0", "2dfan4.hash"),
    "peppa_wutz.onnx": hf_url("models-3.0.0", "peppa_wutz.onnx"),
    "peppa_wutz.hash": hf_url("models-3.0.0", "peppa_wutz.hash"),
    "fan_68_5.onnx": hf_url("models-3.0.0", "fan_68_5.onnx"),
    "fan_68_5.hash": hf_url("models-3.0.0", "fan_68_5.hash"),

    # Face Recognizer (face_recognizer.py) - models-3.0.0
    "arcface_w600k_r50.onnx": hf_url("models-3.0.0", "arcface_w600k_r50.onnx"),
    "arcface_w600k_r50.hash": hf_url("models-3.0.0", "arcface_w600k_r50.hash"),

    # Face Classifier (face_classifier.py) - models-3.0.0
    "fairface.onnx": hf_url("models-3.0.0", "fairface.onnx"),
    "fairface.hash": hf_url("models-3.0.0", "fairface.hash"),

    # Face Parser/Masker (face_masker.py) - models-3.0.0
    "bisenet_resnet_34.onnx": hf_url("models-3.0.0", "bisenet_resnet_34.onnx"),
    "bisenet_resnet_34.hash": hf_url("models-3.0.0", "bisenet_resnet_34.hash"),

    # Face Occluder (遮挡检测) - models-3.2.0
    "xseg_3.onnx": hf_url("models-3.2.0", "xseg_3.onnx"),
    "xseg_3.hash": hf_url("models-3.2.0", "xseg_3.hash"),

    # Expression Restorer (表情修复) - models-3.0.0
    "live_portrait_feature_extractor.onnx": hf_url("models-3.0.0", "live_portrait_feature_extractor.onnx"),
    "live_portrait_feature_extractor.hash": hf_url("models-3.0.0", "live_portrait_feature_extractor.hash"),
    "live_portrait_generator.onnx": hf_url("models-3.0.0", "live_portrait_generator.onnx"),
    "live_portrait_generator.hash": hf_url("models-3.0.0", "live_portrait_generator.hash"),
    "live_portrait_motion_extractor.onnx": hf_url("models-3.0.0", "live_portrait_motion_extractor.onnx"),
    "live_portrait_motion_extractor.hash": hf_url("models-3.0.0", "live_portrait_motion_extractor.hash"),
}


# ============================================================
# 换脸模型 - 来自 face_swapper/core.py
# ============================================================

SWAPPER_MODELS = {
    # InSwapper FP16 (推荐) - models-3.0.0
    "inswapper_128_fp16.onnx": hf_url("models-3.0.0", "inswapper_128_fp16.onnx"),
    "inswapper_128_fp16.hash": hf_url("models-3.0.0", "inswapper_128_fp16.hash"),
}


# ============================================================
# 增强模型 - 来自 face_enhancer/core.py
# ============================================================

ENHANCER_MODELS = {
    # GPEN BFR 512 (推荐) - models-3.0.0
    "gpen_bfr_512.onnx": hf_url("models-3.0.0", "gpen_bfr_512.onnx"),
    "gpen_bfr_512.hash": hf_url("models-3.0.0", "gpen_bfr_512.hash"),
}


# ============================================================
# 可选模型（高质量/完整功能）
# ============================================================

OPTIONAL_MODELS = {
    # 高清增强器 - models-3.0.0
    "gpen_bfr_1024.onnx": hf_url("models-3.0.0", "gpen_bfr_1024.onnx"),
    "gpen_bfr_1024.hash": hf_url("models-3.0.0", "gpen_bfr_1024.hash"),
    "gfpgan_1.4.onnx": hf_url("models-3.0.0", "gfpgan_1.4.onnx"),
    "gfpgan_1.4.hash": hf_url("models-3.0.0", "gfpgan_1.4.hash"),

    # 全精度换脸模型 - models-3.0.0
    "inswapper_128.onnx": hf_url("models-3.0.0", "inswapper_128.onnx"),
    "inswapper_128.hash": hf_url("models-3.0.0", "inswapper_128.hash"),

    # Face Occluder (遮挡检测) - models-3.1.0
    "xseg_1.onnx": hf_url("models-3.1.0", "xseg_1.onnx"),
    "xseg_1.hash": hf_url("models-3.1.0", "xseg_1.hash"),
}


# ============================================================
# 下载函数
# ============================================================

def download_file(url: str, dest: Path) -> bool:
    """下载文件"""
    if dest.exists():
        print(f"  [SKIP] {dest.name} already exists")
        return True

    print(f"  [DOWNLOAD] {dest.name} from {url.split('/')[-3]}...")
    try:
        urllib.request.urlretrieve(url, dest)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  [OK] {dest.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [ERROR] {dest.name}: {e}")
        return False


def download_models(models: dict, name: str) -> int:
    """下载一组模型"""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    success = 0
    for filename, url in models.items():
        dest = MODELS_DIR / filename
        if download_file(url, dest):
            success += 1

    return success


def main():
    # 创建目录
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 解析参数
    scope = sys.argv[1] if len(sys.argv) > 1 else "standard"

    print(f"\n{'#'*60}")
    print(f"  FaceFusion Model Downloader")
    print(f"  Scope: {scope}")
    print(f"  Target: {MODELS_DIR}")
    print(f"{'#'*60}")

    total = 0
    success = 0

    # 核心模型（必需）
    total += len(CORE_MODELS)
    success += download_models(CORE_MODELS, "Core Models (Required)")

    # 换脸模型
    total += len(SWAPPER_MODELS)
    success += download_models(SWAPPER_MODELS, "Face Swapper (inswapper_128_fp16)")

    # 增强模型
    total += len(ENHANCER_MODELS)
    success += download_models(ENHANCER_MODELS, "Face Enhancer (gpen_bfr_512)")

    # 可选模型（仅 full 模式）
    if scope == "full":
        total += len(OPTIONAL_MODELS)
        success += download_models(OPTIONAL_MODELS, "Optional Models")

    # 统计
    print(f"\n{'='*60}")
    print(f"  Download Complete: {success}/{total} files")
    print(f"{'='*60}")

    # 计算总大小
    total_size = sum(f.stat().st_size for f in MODELS_DIR.glob("*.onnx") if f.exists())
    print(f"\nTotal model size: {total_size / (1024**3):.2f} GB")

    # 列出已下载的模型
    print("\nDownloaded models:")
    for f in sorted(MODELS_DIR.glob("*.onnx")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name}: {size_mb:.1f} MB")

    return 0 if success == total else 1


if __name__ == "__main__":
    sys.exit(main())
