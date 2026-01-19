# FaceFusion RunPod Serverless

Deploy FaceFusion face-swap as a RunPod Serverless GPU function.

## Features

- Face swap for videos and images
- Pre-loaded models for fast cold start
- Configurable quality presets (fast, quality, serverless)
- NSFW check disabled for unrestricted processing
- CUDA 12.8 + cuDNN on Ubuntu 24.04

## Deployment

### Option 1: GitHub Actions (Recommended)

1. Fork this repository
2. Add Docker Hub credentials as GitHub secrets:
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token
3. Update `DOCKERHUB_USERNAME` in `.github/workflows/build.yml`
4. Push to `main` branch to trigger automatic build

### Option 2: Manual Build

```bash
# Build image
docker build -t your-username/facefusion-serverless:latest .

# Push to Docker Hub
docker login
docker push your-username/facefusion-serverless:latest
```

### Create RunPod Endpoint

1. Go to [RunPod Serverless Console](https://www.runpod.io/console/serverless)
2. Click "New Endpoint"
3. Configure:
   - **Container Image**: `your-username/facefusion-serverless:latest`
   - **GPU Type**: RTX 4090 / A100 (recommended)
   - **Container Disk**: 20GB
   - **Max Workers**: Set based on your needs
   - **Idle Timeout**: 5-10 seconds

## API Usage

### Python Client

```python
import runpod

runpod.api_key = "your-runpod-api-key"
endpoint = runpod.Endpoint("your-endpoint-id")

# Face swap request
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

### cURL

```bash
curl -X POST "https://api.runpod.ai/v2/your-endpoint-id/runsync" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "source_url": "https://example.com/source.jpg",
      "target_url": "https://example.com/target.mp4"
    }
  }'
```

## API Parameters

### Input

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `source_url` | ✅ | - | Source face image URL |
| `target_url` | ✅ | - | Target video/image URL |
| `preset` | ❌ | `serverless` | Quality preset: `fast`, `quality`, `serverless` |
| `face_swapper_model` | ❌ | `inswapper_128_fp16` | Face swap model |
| `face_enhancer_model` | ❌ | `gpen_bfr_512` | Face enhancement model |
| `face_enhancer_blend` | ❌ | `80` | Enhancement blend (0-100) |
| `pixel_boost` | ❌ | `256x256` | Pixel boost resolution |
| `output_video_quality` | ❌ | `80` | Output quality (0-100) |

### Available Models

**Face Swapper:**
- `inswapper_128_fp16` (recommended, fastest)
- `inswapper_128`
- `hyperswap_1a_256`
- `blendswap_256`
- `ghost_3_256` (highest quality)

**Face Enhancer:**
- `gpen_bfr_512` (recommended)
- `gpen_bfr_1024`
- `gfpgan_1.4`
- `codeformer`

### Response

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

## Cloud Storage (Large Files)

For output files larger than 10MB, configure cloud storage upload.

### AWS S3 / Cloudflare R2

Set environment variables in RunPod Endpoint:

```
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
S3_BUCKET=your-bucket-name
S3_ENDPOINT=https://xxx.r2.cloudflarestorage.com  # For R2
```

Then modify the `upload_to_storage` function in `handler.py`.

## Pre-loaded Models

The following models are pre-downloaded during build to reduce cold start time:

- **Face Detection**: yoloface_8n
- **Face Landmarker**: 2dfan4, fan_68_5
- **Face Recognizer**: arcface_w600k_r50
- **Face Classifier**: fairface
- **Face Parser**: bisenet_resnet_34
- **Face Swapper**: inswapper_128_fp16
- **Face Enhancer**: gpen_bfr_512

## Cost Estimation

- **RTX 4090**: ~$0.44/hour
- **A100 40GB**: ~$0.79/hour

Processing a 1-minute video (1080p) takes approximately 2-5 minutes of GPU time.

## Local Testing

```bash
# Build test image
docker build -t facefusion-test .

# Run with GPU
docker run --gpus all -p 8000:8000 facefusion-test
```

## License

This project wraps [FaceFusion](https://github.com/facefusion/facefusion) for serverless deployment.
