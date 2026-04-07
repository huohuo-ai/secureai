#!/bin/bash

# AI审计系统启动脚本

set -e

echo "=========================================="
echo "     AI模型调用审计系统启动脚本"
echo "=========================================="
echo ""
echo "📌 已配置国内镜像加速: pip(阿里云) / npm(淘宝) / apt(阿里云)"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 插件未安装"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 启动服务
echo ""
echo "正在启动服务 (首次构建可能需要 3-5 分钟)..."
docker compose up -d --build

# 等待数据库初始化
echo ""
echo "等待数据库初始化..."
sleep 10

# 检查数据库是否就绪
echo "检查数据库连接..."
until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "  等待数据库就绪..."
    sleep 2
done

echo "数据库已就绪"

# 询问是否生成测试数据
echo ""
read -p "是否生成测试数据? (y/n): " generate_data

if [ "$generate_data" = "y" ] || [ "$generate_data" = "Y" ]; then
    echo ""
    echo "正在生成测试数据..."
    docker compose exec backend python generate_test_data.py
    echo "测试数据生成完成"
fi

echo ""
echo "=========================================="
echo "           系统启动完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  前端界面: http://localhost:5173"
echo "  API文档:  http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/health"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose logs -f"
echo "  停止服务: docker compose down"
echo "  重启服务: docker compose restart"
echo ""
echo "=========================================="
