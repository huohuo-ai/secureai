#!/bin/bash
# AI 审计平台 - Docker 启动脚本

echo "🚀 AI 审计平台启动脚本"
echo "======================"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 docker compose 是否可用
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 插件未安装"
    exit 1
fi

# 创建数据目录
mkdir -p data

echo ""
echo "1. 构建镜像（使用国内镜像源）..."
docker compose build

echo ""
echo "2. 启动服务..."
docker compose up -d

echo ""
echo "3. 等待服务就绪..."
sleep 5

# 检查服务状态
if docker compose ps | grep -q "Up"; then
    echo ""
    echo "✅ 服务启动成功！"
    echo ""
    echo "访问地址:"
    echo "  • http://localhost:8000"
    echo "  • http://127.0.0.1:8000"
    echo ""
    echo "登录信息:"
    echo "  • 用户名: admin"
    echo "  • 密码: admin"
    echo ""
    echo "常用命令:"
    echo "  • 查看日志: docker compose logs -f"
    echo "  • 停止服务: docker compose down"
    echo "  • 重启服务: docker compose restart"
    echo ""
else
    echo "❌ 服务启动失败，请查看日志:"
    docker compose logs
fi
