"""
FaceFusion RunPod 测试脚本
"""
import os
import time
import base64
import runpod

# ============================================================
# 配置 - 请修改为你的值
# ============================================================
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "你的API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "你的ENDPOINT_ID")

# 测试用图片/视频 URL (请替换为实际可访问的 URL)
SOURCE_URL = "https://example.com/source_face.jpg"
TARGET_URL = "https://example.com/target_video.mp4"


def test_face_swap():
    """测试换脸 API"""
    print("=" * 50)
    print("FaceFusion RunPod Test")
    print("=" * 50)
    print(f"Endpoint: {ENDPOINT_ID}")
    print(f"Source: {SOURCE_URL}")
    print(f"Target: {TARGET_URL}")
    print()

    # 初始化
    runpod.api_key = RUNPOD_API_KEY
    endpoint = runpod.Endpoint(ENDPOINT_ID)

    # 发送请求
    print("Submitting job...")
    run = endpoint.run({
        "input": {
            "source_url": SOURCE_URL,
            "target_url": TARGET_URL,
            "preset": "fast",  # fast, quality, serverless
            "face_swapper_model": "inswapper_128_fp16",
            "face_enhancer_model": "gpen_bfr_512",
            "face_enhancer_blend": 80,
            "pixel_boost": "256x256"
        }
    })

    print(f"Job ID: {run.job_id}")
    print()

    # 等待结果
    print("Processing", end="", flush=True)
    start_time = time.time()

    while True:
        status = run.status()

        if status == "COMPLETED":
            print(" Done!")
            result = run.output()
            break
        elif status == "FAILED":
            print(" Failed!")
            result = {"error": "Job failed"}
            break
        elif time.time() - start_time > 600:  # 10分钟超时
            print(" Timeout!")
            result = {"error": "Timeout"}
            break

        print(".", end="", flush=True)
        time.sleep(5)

    # 显示结果
    elapsed = time.time() - start_time
    print()
    print("=" * 50)
    print("Result")
    print("=" * 50)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total Time: {elapsed:.1f}s")

    if result.get("processing_time"):
        print(f"Processing Time: {result['processing_time']}s")

    if result.get("error"):
        print(f"Error: {result['error']}")

    if result.get("output_url"):
        output_url = result["output_url"]
        if output_url.startswith("data:"):
            # Base64 数据，保存到文件
            print("Output: Base64 encoded (saving to output.mp4)")
            header, encoded = output_url.split(",", 1)
            data = base64.b64decode(encoded)
            with open("output.mp4", "wb") as f:
                f.write(data)
            print(f"Saved to: output.mp4 ({len(data) / 1024 / 1024:.1f} MB)")
        else:
            print(f"Output URL: {output_url}")

    return result


if __name__ == "__main__":
    # 检查配置
    if RUNPOD_API_KEY == "你的API_KEY" or ENDPOINT_ID == "你的ENDPOINT_ID":
        print("请先配置 RUNPOD_API_KEY 和 ENDPOINT_ID")
        print()
        print("方法1: 修改脚本中的变量")
        print("方法2: 设置环境变量")
        print("  set RUNPOD_API_KEY=xxx")
        print("  set RUNPOD_ENDPOINT_ID=xxx")
        exit(1)

    test_face_swap()
