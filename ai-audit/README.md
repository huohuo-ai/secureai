# 🛡️ AI 审计平台

企业级 AI 模型调用审计与风险分析平台 MVP。

## 功能特性

- 🔐 **Session 登录** - 默认账号 admin/admin
- 🚦 **4级风险检测** - Low/Medium/High/Critical
- 🏷️ **8种行为标签** - 高频用户、异常消耗、测试行为、批量操作、深夜使用、敏感操作、模型对比、长对话
- 📊 **数据仪表盘** - 统计概览、趋势图、部门排行
- 📝 **审计日志** - 搜索、筛选、分页
- 👥 **用户分析** - 活跃度排行
- ⚠️ **风险分析** - 风险事件列表

## 快速启动（Docker）

### 方法一：使用启动脚本

```bash
chmod +x start.sh
./start.sh
```

### 方法二：手动启动

```bash
# 1. 构建并启动
docker compose up -d --build

# 2. 查看日志
docker compose logs -f

# 3. 访问 http://localhost:8000
```

### 方法三：本地运行（无需 Docker）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python main.py

# 3. 自动打开浏览器
```

## 登录信息

- **用户名**: admin
- **密码**: admin

## 数据结构

自动生成 **30 天** 演示数据，约 **10,000** 条记录：

| 场景 | 占比 | 说明 |
|-----|------|------|
| 正常使用 | 70% | 代码编写、文档生成等 |
| 含敏感词 | 15% | 身份证、银行卡等 |
| 高频调用 | 8% | 测试/调试行为 |
| 深夜使用 | 5% | 22:00-06:00 |
| 超大 Token | 2% | >8K Token |

## 目录结构

```
ai-audit/
├── main.py              # FastAPI 主程序
├── database.py          # SQLite 数据库
├── risk_detector.py     # 风险检测
├── behavior_tagger.py   # 行为标签
├── generate_data.py     # 演示数据
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose
├── start.sh             # 启动脚本
├── requirements.txt     # Python 依赖
└── static/              # 前端文件
    ├── index.html
    ├── style.css
    └── app.js
```

## 常用命令

```bash
# 启动
docker compose up -d

# 停止
docker compose down

# 重启
docker compose restart

# 查看日志
docker compose logs -f

# 重新构建
docker compose up -d --build

# 删除数据（重置）
rm -rf data/
docker compose down
```

## 数据持久化

数据保存在 `./data/audit.db`，通过 Docker volume 挂载到容器内。

删除 `data/` 目录即可重置所有数据。

## 访问地址

- 本地: http://localhost:8000
- 局域网: http://服务器IP:8000

## 演示截图

仪表盘展示：
- 总调用次数、总成本、活跃用户、Token 消耗
- 风险等级分布
- 供应商使用占比
- 30 天调用趋势图
- 热门行为标签云
- 部门使用排行

## License

MIT
