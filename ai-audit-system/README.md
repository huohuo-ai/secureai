# AI模型调用审计系统

一个全面的AI模型调用审计Demo系统，提供合规审计、风险检测和成本管控功能。

## 功能特性

### 1. 合规与监管
- ✅ 完整的AI使用记录审计
- ✅ GDPR合规性检查
- ✅ 数据驻留合规监控
- ✅ 审计日志防篡改（哈希链）
- ✅ 合规报告导出（JSON/CSV）

### 2. 风险安全防控
- ✅ 敏感数据检测（身份证、手机号、银行卡、API密钥等）
- ✅ Prompt注入攻击检测
- ✅ 越狱攻击检测
- ✅ 异常行为监控
- ✅ 自动阻断高风险请求
- ✅ 实时告警通知

### 3. 成本管控
- ✅ Token用量统计
- ✅ 按部门/用户/项目成本分析
- ✅ 配额管理和限制
- ✅ 预算告警
- ✅ 成本趋势分析

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL
- **前端**: Vue 3 + Element Plus + ECharts
- **数据存储**: PostgreSQL + Redis
- **部署**: Docker + Docker Compose

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目
cd ai-audit-system

# 启动所有服务
docker compose up -d

# 等待数据库初始化完成（约30秒）

# 生成测试数据
docker compose exec backend python generate_test_data.py

# 访问系统
# 前端: http://localhost:5173
# 后端API: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 方式二：本地开发

#### 后端

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动PostgreSQL和Redis（需要本地安装或使用Docker）
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15

# 启动后端服务
uvicorn app.main:app --reload
```

#### 前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:5173
```

#### 生成测试数据

```bash
cd backend
python generate_test_data.py
```

## API 接口

### AI代理接口（兼容OpenAI）

```
POST /v1/chat/completions    # 聊天补全
GET  /v1/models              # 模型列表
```

### 审计接口

```
GET  /api/audit/logs         # 审计日志查询
GET  /api/audit/stats/summary    # 统计摘要
GET  /api/audit/risk/events      # 风险事件
GET  /api/audit/sensitive-data   # 敏感数据命中
```

### 成本管控接口

```
GET  /api/cost/quotas        # 用户配额
PUT  /api/cost/quotas/{id}   # 更新配额
GET  /api/cost/usage         # 用量统计
GET  /api/cost/billing       # 账单信息
```

### 合规接口

```
GET  /api/compliance/reports/overview    # 合规概览
GET  /api/compliance/reports/audit-trail # 审计追踪
GET  /api/compliance/reports/export      # 导出数据
GET  /api/compliance/rules               # 合规规则
```

完整API文档请访问: http://localhost:8000/docs

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PostgreSQL │
│  (Vue3)     │     │  (FastAPI)  │     │  (Data)     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │   (Cache)   │
                    └─────────────┘
```

## 风险检测能力

### 敏感数据类型
- 中国大陆身份证号
- 手机号
- 银行卡号
- 邮箱地址
- IP地址
- API密钥
- 源代码
- 商业机密

### 安全威胁检测
- Prompt注入攻击
- 越狱攻击（Jailbreak）
- 数据外泄尝试
- 异常大输入
- 成本飙升检测

## 成本计算模型

| 模型 | Input ($/1K tokens) | Output ($/1K tokens) |
|------|---------------------|----------------------|
| GPT-4 | $0.03 | $0.06 |
| GPT-4 Turbo | $0.01 | $0.03 |
| GPT-3.5 Turbo | $0.0015 | $0.002 |
| Claude 3 Opus | $0.015 | $0.075 |
| Claude 3 Sonnet | $0.003 | $0.015 |
| Claude 3 Haiku | $0.00025 | $0.00125 |

## 项目结构

```
ai-audit-system/
├── backend/
│   ├── app/
│   │   ├── core/          # 配置
│   │   ├── models/        # 数据模型
│   │   ├── routers/       # API路由
│   │   ├── services/      # 业务逻辑
│   │   └── main.py        # 应用入口
│   ├── generate_test_data.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── components/    # 公共组件
│   │   ├── utils/         # 工具函数
│   │   └── router/        # 路由配置
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 演示场景

1. **正常请求**: 普通AI对话，记录审计日志
2. **敏感数据检测**: 输入包含身份证号/手机号等敏感信息
3. **Prompt注入检测**: 尝试绕过系统安全限制
4. **越狱攻击检测**: 使用DAN等越狱技巧
5. **源代码检测**: 输入包含源代码片段
6. **配额超限**: 超出用户配额限制

## 合规性说明

本系统帮助满足以下合规要求：

- **中国《生成式人工智能服务管理暂行办法》**
  - 提供完整的使用记录
  - 敏感数据检测和处理
  - 算法透明度

- **欧盟GDPR**
  - 数据处理活动记录
  - 个人数据保护
  - 数据主体权利支持

- **企业内控**
  - 操作审计追踪
  - 数据安全监控
  - 成本控制

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交Issue。
