#!/bin/bash
# AI 审计平台 - Docker 镜像构建脚本

IMAGE_NAME="ai-audit-platform"
IMAGE_TAG="latest"

echo "🐳 AI 审计平台 Docker 镜像构建"
echo "================================"

# 构建镜像
echo ""
echo "1. 构建镜像..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 镜像构建成功！"
    echo ""
    echo "镜像信息:"
    docker images ${IMAGE_NAME}:${IMAGE_TAG} --format "  名称: {{.Repository}}\n  标签: {{.Tag}}\n  大小: {{.Size}}\n  创建: {{.CreatedAt}}"
    echo ""
    echo "启动命令:"
    echo "  docker run -d -p 8000:8000 -v \$(pwd)/data:/app/data ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "或使用 docker-compose:"
    echo "  docker-compose up -d"
    echo ""
    
    # 询问是否导出
    read -p "是否导出为 tar 文件？(y/n): " choice
    if [ "$choice" = "y" ]; then
        echo ""
        echo "2. 导出镜像..."
        docker save -o ${IMAGE_NAME}-${IMAGE_TAG}.tar ${IMAGE_NAME}:${IMAGE_TAG}
        echo ""
        echo "✅ 导出成功: ${IMAGE_NAME}-${IMAGE_TAG}.tar"
        echo ""
        echo "导入命令:"
        echo "  docker load -i ${IMAGE_NAME}-${IMAGE_TAG}.tar"
    fi
else
    echo ""
    echo "❌ 镜像构建失败"
    exit 1
fi
