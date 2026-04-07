# AI模型调用审计系统 - 设计文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Audit System                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────┐  │
│  │   Frontend   │◄──►│   Backend API    │◄──►│   Database (PostgreSQL)  │  │
│  │   (Vue3)     │    │   (FastAPI)      │    │                          │  │
│  └──────────────┘    └──────────────────┘    └──────────────────────────┘  │
│                             │                                               │
│                             ▼                                               │
│                    ┌──────────────────┐                                    │
│                    │  AI Provider     │                                    │
│                    │  (OpenAI/Claude) │                                    │
│                    └──────────────────┘                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 核心功能模块

### 2.1 审计核心模块 (Audit Core)
- **请求拦截**: 代理所有AI模型调用请求
- **日志记录**: 记录完整的请求/响应数据
- **敏感信息检测**: 实时检测PII、商业机密等
- **合规检查**: GDPR、数据出境等合规规则

### 2.2 风险检测模块 (Risk Detection)
- **敏感数据类型**: 身份证号、手机号、银行卡、邮箱、IP地址、源代码等
- **攻击检测**: Prompt注入、越狱攻击识别
- **内容安全**: 有害内容输出检测
- **异常行为**: 高频调用、大流量请求等

### 2.3 成本管控模块 (Cost Control)
- **用量统计**: Token使用量、API调用次数
- **配额管理**: 部门/用户级别的配额限制
- **成本分析**: 按项目/部门/时间维度的成本分析
- **告警机制**: 预算超支预警

### 2.4 报表分析模块 (Analytics)
- **合规报表**: 满足监管要求的审计报告
- **风险报表**: 风险事件统计与趋势分析
- **成本报表**: 多维度成本分析可视化
- **用户行为**: 使用模式与行为分析

## 3. 数据模型设计

### 3.1 核心表结构

```sql
-- 审计日志表 (audit_logs)
- id: UUID (PK)
- request_id: String (唯一请求ID)
- user_id: String (用户标识)
- department: String (部门)
- project: String (项目)
- provider: String (AI提供商: openai/anthropic/etc)
- model: String (模型名称)
- request_time: Timestamp (请求时间)
- response_time: Timestamp (响应时间)
- latency_ms: Integer (延迟毫秒)
- status: Enum (success/failure/blocked)
- input_tokens: Integer (输入Token数)
- output_tokens: Integer (输出Token数)
- estimated_cost: Decimal (预估成本)
- input_preview: Text (输入内容摘要)
- output_preview: Text (输出内容摘要)
- full_input: Text (完整输入，加密存储)
- full_output: Text (完整输出，加密存储)
- client_ip: String (客户端IP)
- user_agent: String (浏览器标识)
- session_id: String (会话ID)
- metadata: JSON (扩展元数据)
- created_at: Timestamp

-- 风险检测记录表 (risk_detections)
- id: UUID (PK)
- audit_log_id: UUID (FK)
- risk_type: Enum (sensitive_data/prompt_injection/jailbreak/data_exfiltration/policy_violation)
- risk_level: Enum (low/medium/high/critical)
- detection_rule: String (触发的规则名称)
- detected_content: Text (检测到的内容片段)
- confidence_score: Float (置信度 0-1)
- action_taken: Enum (log/warn/block/mask)
- blocked: Boolean (是否被阻断)
- created_at: Timestamp

-- 敏感数据命中记录 (sensitive_data_hits)
- id: UUID (PK)
- audit_log_id: UUID (FK)
- data_type: Enum (id_card/phone/bank_card/email/ip_address/source_code/business_secret)
- detection_method: Enum (regex/ml/keyword)
- matched_pattern: String (匹配的模式)
- masked_content: Text (脱敏后的内容)
- position: String (位置: input/output)
- created_at: Timestamp

-- 用户配额表 (user_quotas)
- id: UUID (PK)
- user_id: String (用户标识)
- department: String (部门)
- daily_limit: Integer (每日Token上限)
- monthly_limit: Integer (每月Token上限)
- daily_used: Integer (当日已用)
- monthly_used: Integer (当月已用)
- cost_budget: Decimal (预算金额)
- cost_used: Decimal (已用金额)
- reset_date: Date (重置日期)
- created_at: Timestamp

-- 合规规则表 (compliance_rules)
- id: UUID (PK)
- name: String (规则名称)
- rule_type: Enum (data_residency/sensitive_data/prompt_check/output_filter)
- description: Text (规则描述)
- conditions: JSON (规则条件)
- action: Enum (allow/block/mask/notify)
- enabled: Boolean (是否启用)
- priority: Integer (优先级)
- created_at: Timestamp

-- 系统配置表 (system_configs)
- id: UUID (PK)
- config_key: String (配置键)
- config_value: JSON (配置值)
- description: Text (描述)
- updated_at: Timestamp
```

## 4. API 设计

### 4.1 核心API

```
# 代理API (代理到实际AI服务)
POST /v1/chat/completions          -> 代理到OpenAI
POST /v1/messages                  -> 代理到Claude

# 审计查询API
GET /api/audit/logs                # 查询审计日志
GET /api/audit/logs/{id}           # 获取单条日志详情
GET /api/audit/stats/summary       # 审计统计摘要
GET /api/audit/stats/trends        # 趋势分析
GET /api/audit/risk/events         # 风险事件查询

# 风险检测API
GET /api/risk/detections           # 风险检测记录
GET /api/risk/sensitive-data       # 敏感数据命中记录
GET /api/risk/stats                # 风险统计

# 成本管控API
GET /api/cost/usage                # 用量查询
GET /api/cost/billing              # 成本账单
GET /api/cost/quotas               # 配额管理
POST /api/cost/quotas              # 设置配额

# 合规报表API
GET /api/compliance/reports        # 合规报表
GET /api/compliance/export         # 导出审计数据

# 管理API
GET /api/admin/rules               # 规则管理
POST /api/admin/rules              # 创建规则
PUT /api/admin/rules/{id}          # 更新规则
DELETE /api/admin/rules/{id}       # 删除规则
GET /api/admin/configs             # 系统配置
PUT /api/admin/configs             # 更新配置
```

## 5. 技术栈

- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: Vue3 + Element Plus + ECharts
- **AI Provider**: OpenAI API Compatible
- **Deployment**: Docker + Docker Compose

## 6. 安全特性

1. **数据加密**: 敏感字段AES-256加密存储
2. **访问控制**: JWT认证 + RBAC权限管理
3. **审计日志防篡改**: 哈希链 + 数字签名
4. **数据脱敏**: 自动敏感信息脱敏展示
