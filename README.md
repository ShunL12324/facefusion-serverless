# FaceFusion RunPod Serverless

将 FaceFusion 视频换脸部署为 RunPod Serverless GPU 函数。

## 部署步骤

### 1. 构建 Docker 镜像

```bash
cd facefusion-serverless

# 构建镜像
docker build -t your-dockerhub-username/facefusion-serverless:latest .

# 推送到 Docker Hub
docker push your-dockerhub-username/facefusion-serverless:latest
```

### 2. 创建 RunPod Serverless Endpoint

1. 登录 [RunPod Console](https://www.runpod.io/console/serverless)
2. 点击 "New Endpoint"
3. 配置:
   - **Container Image**: `your-dockerhub-username/facefusion-serverless:latest`
   - **GPU Type**: RTX 4090 / A100 (推荐)
   - **Container Disk**: 20GB
   - **Max Workers**: 根据需求设置
   - **Idle Timeout**: 5-10 秒

### 3. 调用 API

```python
import runpod
import time

runpod.api_key = "your-runpod-api-key"
endpoint = runpod.Endpoint("your-endpoint-id")

# 发起换脸请求
result = endpoint.run_sync({
    "input": {
        "source_url": "https://example.com/source_face.jpg",
        "target_url": "https://example.com/target_video.mp4",
        "face_swapper_model": "inswapper_128_fp16",
        "face_enhancer_model": "gpen_bfr_512",
        "face_enhancer_blend": 80,
        "pixel_boost": "256x256"
    }
})

print(result)
```

## API 参数

### 输入参数

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `source_url` | ✅ | - | 源脸图片 URL |
| `target_url` | ✅ | - | 目标视频/图片 URL |
| `face_swapper_model` | ❌ | `inswapper_128_fp16` | 换脸模型 |
| `face_enhancer_model` | ❌ | `gpen_bfr_512` | 增强模型 |
| `face_enhancer_blend` | ❌ | `80` | 增强混合度 (0-100) |
| `pixel_boost` | ❌ | `256x256` | 像素提升 |
| `output_video_quality` | ❌ | `80` | 输出质量 (0-100) |

### 可用模型

**Face Swapper:**
- `inswapper_128_fp16` (推荐，最快)
- `inswapper_128`
- `hyperswap_1a_256`
- `blendswap_256`
- `ghost_3_256` (最高质量)

**Face Enhancer:**
- `gpen_bfr_512` (推荐)
- `gpen_bfr_1024`
- `gfpgan_1.4`
- `codeformer`

### 返回结果

```json
{
    "output_url": "data:video/mp4;base64,xxx...",
    "status": "success",
    "processing_time": 45.67,
    "params_used": {
        "face_swapper_model": "inswapper_128_fp16",
        "face_enhancer_model": "gpen_bfr_512"
    }
}
```

## 云存储配置 (大文件)

对于大于 10MB 的输出文件，需要配置云存储上传。

### 使用 AWS S3 / Cloudflare R2

在 RunPod Endpoint 环境变量中设置:

```
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
S3_BUCKET=your-bucket-name
S3_ENDPOINT=https://xxx.r2.cloudflarestorage.com  # R2 使用
```

然后修改 `handler.py` 中的 `upload_to_storage` 函数。

## 预下载模型 (减少冷启动)

在 Dockerfile 中取消注释以下行:

```dockerfile
RUN python facefusion.py force-download --download-scope lite
```

这会预下载基本模型，减少首次调用延迟。

## 成本估算

- **RTX 4090**: ~$0.44/小时
- **A100 40GB**: ~$0.79/小时

处理 1 分钟视频 (1080p) 大约需要 2-5 分钟 GPU 时间。

## 本地测试

```bash
# 构建测试镜像
docker build -t facefusion-test .

# 运行测试
docker run --gpus all -p 8000:8000 facefusion-test
```
