"""
FaceFusion RunPod 客户端示例
==============================
用于调用部署在 RunPod 上的 FaceFusion 服务
"""

import runpod
import time
import base64
import os
from pathlib import Path


class FaceFusionClient:
    def __init__(self, api_key: str, endpoint_id: str):
        """
        初始化客户端

        Args:
            api_key: RunPod API Key
            endpoint_id: RunPod Endpoint ID
        """
        runpod.api_key = api_key
        self.endpoint = runpod.Endpoint(endpoint_id)

    def swap_face(
        self,
        source_url: str,
        target_url: str,
        face_swapper_model: str = "inswapper_128_fp16",
        face_enhancer_model: str = "gpen_bfr_512",
        face_enhancer_blend: int = 80,
        pixel_boost: str = "256x256",
        output_video_quality: int = 80,
        timeout: int = 600,
        save_to: str = None
    ) -> dict:
        """
        执行换脸操作

        Args:
            source_url: 源脸图片 URL
            target_url: 目标视频/图片 URL
            face_swapper_model: 换脸模型
            face_enhancer_model: 增强模型
            face_enhancer_blend: 增强混合度 (0-100)
            pixel_boost: 像素提升
            output_video_quality: 输出质量 (0-100)
            timeout: 超时时间 (秒)
            save_to: 保存结果到本地文件路径

        Returns:
            处理结果字典
        """
        print(f"Submitting face swap job...")
        print(f"  Source: {source_url}")
        print(f"  Target: {target_url}")
        print(f"  Model: {face_swapper_model} + {face_enhancer_model}")

        # 提交任务
        run = self.endpoint.run({
            "input": {
                "source_url": source_url,
                "target_url": target_url,
                "face_swapper_model": face_swapper_model,
                "face_enhancer_model": face_enhancer_model,
                "face_enhancer_blend": face_enhancer_blend,
                "pixel_boost": pixel_boost,
                "output_video_quality": output_video_quality
            }
        })

        print(f"Job ID: {run.job_id}")
        print("Processing...")

        # 等待结果
        start_time = time.time()
        while True:
            status = run.status()

            if status == "COMPLETED":
                result = run.output()
                break
            elif status == "FAILED":
                result = {"error": "Job failed", "status": "failed"}
                break
            elif time.time() - start_time > timeout:
                result = {"error": "Timeout", "status": "timeout"}
                break

            elapsed = int(time.time() - start_time)
            print(f"  Status: {status} ({elapsed}s elapsed)")
            time.sleep(5)

        # 保存结果
        if save_to and result.get("status") == "success":
            output_url = result.get("output_url", "")
            if output_url.startswith("data:"):
                # Base64 编码的数据
                self._save_base64_file(output_url, save_to)
                print(f"Saved to: {save_to}")
            else:
                # URL，需要下载
                self._download_file(output_url, save_to)
                print(f"Downloaded to: {save_to}")

        return result

    def _save_base64_file(self, data_url: str, path: str):
        """保存 base64 编码的文件"""
        # 格式: data:video/mp4;base64,xxx
        header, encoded = data_url.split(",", 1)
        data = base64.b64decode(encoded)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def _download_file(self, url: str, path: str):
        """下载文件"""
        import requests
        response = requests.get(url, stream=True)
        response.raise_for_status()

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)


# 使用示例
if __name__ == "__main__":
    # 配置
    API_KEY = os.environ.get("RUNPOD_API_KEY", "your-api-key")
    ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "your-endpoint-id")

    # 创建客户端
    client = FaceFusionClient(API_KEY, ENDPOINT_ID)

    # 执行换脸
    result = client.swap_face(
        source_url="https://example.com/source_face.jpg",
        target_url="https://example.com/target_video.mp4",
        face_swapper_model="inswapper_128_fp16",
        face_enhancer_model="gpen_bfr_512",
        save_to="output/result.mp4"
    )

    print("\nResult:")
    print(f"  Status: {result.get('status')}")
    print(f"  Processing Time: {result.get('processing_time')}s")

    if result.get("error"):
        print(f"  Error: {result.get('error')}")
