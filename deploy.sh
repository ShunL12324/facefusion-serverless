#!/bin/bash
# FaceFusion RunPod 部署脚本
# 用法: ./deploy.sh <dockerhub-username>

set -e

DOCKERHUB_USER=${1:-"your-username"}
IMAGE_NAME="facefusion-serverless"
TAG="latest"

echo "=========================================="
echo "  FaceFusion RunPod Deployment"
echo "=========================================="
echo "Docker Hub User: $DOCKERHUB_USER"
echo "Image: $DOCKERHUB_USER/$IMAGE_NAME:$TAG"
echo ""

# 1. 构建镜像
echo "[1/3] Building Docker image..."
docker build -t $DOCKERHUB_USER/$IMAGE_NAME:$TAG .

# 2. 登录 Docker Hub
echo ""
echo "[2/3] Logging into Docker Hub..."
docker login

# 3. 推送镜像
echo ""
echo "[3/3] Pushing image to Docker Hub..."
docker push $DOCKERHUB_USER/$IMAGE_NAME:$TAG

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Go to https://www.runpod.io/console/serverless"
echo "2. Click 'New Endpoint'"
echo "3. Enter image: $DOCKERHUB_USER/$IMAGE_NAME:$TAG"
echo "4. Select GPU type (RTX 4090 recommended)"
echo "5. Set Container Disk: 20GB"
echo "6. Create endpoint and get your Endpoint ID"
echo ""
