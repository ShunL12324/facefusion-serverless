@echo off
REM FaceFusion RunPod 部署脚本 (Windows)
REM 用法: deploy.bat <dockerhub-username>

setlocal

set DOCKERHUB_USER=%1
if "%DOCKERHUB_USER%"=="" set DOCKERHUB_USER=your-username

set IMAGE_NAME=facefusion-serverless
set TAG=latest

echo ==========================================
echo   FaceFusion RunPod Deployment
echo ==========================================
echo Docker Hub User: %DOCKERHUB_USER%
echo Image: %DOCKERHUB_USER%/%IMAGE_NAME%:%TAG%
echo.

REM 1. 构建镜像
echo [1/3] Building Docker image...
docker build -t %DOCKERHUB_USER%/%IMAGE_NAME%:%TAG% .
if errorlevel 1 goto :error

REM 2. 登录 Docker Hub
echo.
echo [2/3] Logging into Docker Hub...
docker login
if errorlevel 1 goto :error

REM 3. 推送镜像
echo.
echo [3/3] Pushing image to Docker Hub...
docker push %DOCKERHUB_USER%/%IMAGE_NAME%:%TAG%
if errorlevel 1 goto :error

echo.
echo ==========================================
echo   Deployment Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Go to https://www.runpod.io/console/serverless
echo 2. Click 'New Endpoint'
echo 3. Enter image: %DOCKERHUB_USER%/%IMAGE_NAME%:%TAG%
echo 4. Select GPU type (RTX 4090 recommended)
echo 5. Set Container Disk: 20GB
echo 6. Create endpoint and get your Endpoint ID
echo.
goto :end

:error
echo.
echo ERROR: Deployment failed!
exit /b 1

:end
endlocal
