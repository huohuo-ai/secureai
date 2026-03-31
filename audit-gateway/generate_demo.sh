#!/bin/bash
# AI 审计网关 - 一键生成 Demo 数据

set -e

echo "🚀 AI 审计网关 - Demo 数据生成器"
echo "===================================="

# 检查 ClickHouse 是否运行
echo ""
echo "1. 检查 ClickHouse 服务状态..."
if ! docker-compose ps | grep -q "clickhouse.*Up"; then
    echo "   ⚠️  ClickHouse 未运行，正在启动..."
    docker-compose up -d clickhouse
    echo "   ⏳ 等待 ClickHouse 就绪..."
    sleep 10
fi

echo "   ✅ ClickHouse 已就绪"

# 运行数据生成脚本
echo ""
echo "2. 生成测试数据..."
docker-compose exec -T audit-gateway python -c "
$(cat generate_demo_data.py)
"

echo ""
echo "===================================="
echo "✅ Demo 数据生成完成！"
echo ""
echo "现在你可以:"
echo "  • 访问 http://localhost:8000/admin"
echo "  • 输入 API: http://localhost:8000"
echo "  • 输入你的 Admin Token"
echo "  • 查看丰富的演示数据 🎉"
echo ""
