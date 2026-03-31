# AI 审计网关系统

企业级 AI 模型调用审计系统，基于网宿边缘函数 + FastAPI 中心网关实现。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户请求                                 │
│  (Cursor/VSCode/Python/ChatGPT-Next-Web)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  【网宿边缘节点 - EdgeScript】                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  提取身份   │→│  解析Content │→│  异步上报中心网关        │ │
│  │  (Header)   │  │ (JSON Body) │  │  (fire-and-forget)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              透传/转发到上游大模型域名                      │ │
│  │   (api.openai.com / api.anthropic.com / dashscope...)    │ │
│  └───────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────┐      ┌─────────────────────┐
│   中心网关 (你的平台)  │      │   大模型供应商       │
│  ┌───────────────┐  │      │  - OpenAI           │
│  │  审计日志存储  │←─┘      │  - Claude           │
│  │  统计分析      │         │  - 文心/通义等       │
│  │  管理控制台    │         │                     │
│  └───────────────┘         └─────────────────────┘
```

---

## 快速开始

### 1. 部署中心网关

```bash
cd audit-gateway

# 修改配置
cp .env.example .env
vim .env

# 一键启动
docker-compose up -d

# 验证
curl http://localhost:8000/health
```

### 2. 配置网宿边缘函数

将下面的 `wangsu-edge-script.js` 代码复制到网宿 CDN 控制台 → EdgeScript。

### 3. 用户接入

```bash
# 用户只需要修改两个环境变量
export OPENAI_API_BASE="https://your-wangsu-cdn.com/v1/openai"
export OPENAI_API_KEY="company-key.user-id"
```

---

## 网宿 EdgeScript 完整代码

**文件：`wangsu-edge-script.js`**

```javascript
/**
 * AI Gateway - 网宿 EdgeScript
 * 功能：请求转发 + Content提取 + 审计上报
 * 版本：v1.1.0
 */

// ==================== 全局配置 ====================
var CONFIG = {
    // 中心网关地址（必须修改为实际地址）
    AUDIT_ENDPOINT: 'https://audit-gateway.yourcompany.com/api/v1/log',
    
    // 审计采样率 (1.0 = 100%，0.1 = 10%)
    SAMPLING_RATE: 1.0,
    
    // 最大 body 大小 (1MB)
    MAX_BODY_SIZE: 1024 * 1024,
    
    // 上游模型配置
    UPSTREAM: {
        'openai': {
            origin: 'api.openai.com',
            protocol: 'https',
            headerName: 'Authorization'
        },
        'azure': {
            origin: 'your-resource.openai.azure.com',
            protocol: 'https',
            pathPrefix: '/openai/deployments/{deployment}',
            apiVersion: '2024-02-01'
        },
        'claude': {
            origin: 'api.anthropic.com',
            protocol: 'https'
        },
        'qwen': {
            origin: 'dashscope.aliyuncs.com',
            protocol: 'https',
            pathRewrite: {'/v1/qwen': '/api/v1/services/aigc/text-generation/generation'}
        },
        'baidu': {
            origin: 'aip.baidubce.com',
            protocol: 'https'
        }
    },
    
    // 路由映射：/v1/openai/xxx -> 转发到 OpenAI
    ROUTE_MAP: {
        '/v1/openai': 'openai',
        '/v1/azure': 'azure',
        '/v1/claude': 'claude',
        '/v1/qwen': 'qwen',
        '/v1/baidu': 'baidu'
    }
};

// ==================== 工具函数 ====================

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0;
        var v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function safeJSONParse(str) {
    try {
        return JSON.parse(str);
    } catch (e) {
        return null;
    }
}

/**
 * 提取用户输入内容（支持多格式）
 */
function extractContents(body) {
    if (!body) return [];
    
    var data = safeJSONParse(body);
    if (!data) return [];
    
    var contents = [];
    
    // OpenAI / Azure / Qwen 兼容格式 (messages)
    if (data.messages && Array.isArray(data.messages)) {
        for (var i = 0; i < data.messages.length; i++) {
            var msg = data.messages[i];
            if (!msg || !msg.content) continue;
            
            var role = msg.role || 'unknown';
            var text = '';
            
            if (typeof msg.content === 'string') {
                text = msg.content;
            } else if (Array.isArray(msg.content)) {
                // 多模态格式提取
                var texts = [];
                for (var j = 0; j < msg.content.length; j++) {
                    var part = msg.content[j];
                    if (part && part.type === 'text' && part.text) {
                        texts.push(part.text);
                    } else if (part && part.type) {
                        texts.push('[' + part.type + ']');
                    }
                }
                text = texts.join(' ');
            }
            
            if (text) {
                contents.push({
                    role: role,
                    content: text,
                    length: text.length
                });
            }
        }
    }
    
    // Claude 格式 (system + messages)
    if (data.system && typeof data.system === 'string') {
        contents.unshift({
            role: 'system',
            content: data.system,
            length: data.system.length
        });
    }
    
    // 百度文心格式 (prompt)
    if (data.prompt && typeof data.prompt === 'string') {
        contents.push({
            role: 'user',
            content: data.prompt,
            length: data.prompt.length
        });
    }
    
    return contents;
}

function getClientIP(request) {
    var xff = request.headers['x-forwarded-for'];
    if (xff) {
        var ips = xff.split(',');
        return ips[0].trim();
    }
    return request.clientIp || 'unknown';
}

function shouldSample() {
    if (CONFIG.SAMPLING_RATE >= 1.0) return true;
    return Math.random() < CONFIG.SAMPLING_RATE;
}

/**
 * 压缩内容（截断长文本）
 */
function compressContent(contents, maxLength) {
    maxLength = maxLength || 2000;
    var result = [];
    var totalLength = 0;
    
    for (var i = 0; i < contents.length; i++) {
        var item = contents[i];
        var content = item.content;
        
        if (totalLength + content.length > maxLength) {
            var remaining = maxLength - totalLength;
            if (remaining > 100) {
                result.push({
                    role: item.role,
                    content: content.substring(0, remaining) + '...[truncated]',
                    truncated: true
                });
            }
            break;
        }
        
        result.push(item);
        totalLength += content.length;
    }
    
    return result;
}

// ==================== 主函数 ====================

function main(request) {
    var reqId = generateUUID();
    var startTime = Date.now();
    
    // 提取基础信息
    var method = request.method || 'GET';
    var path = request.path || '';
    var headers = request.headers || {};
    
    // ========== 1. 路由匹配 ==========
    var targetProvider = null;
    var routePrefix = '';
    var matchedPath = '';
    
    // 按长度降序匹配，避免短路径干扰
    var routes = [];
    for (var p in CONFIG.ROUTE_MAP) {
        routes.push({prefix: p, provider: CONFIG.ROUTE_MAP[p]});
    }
    routes.sort(function(a, b) { return b.prefix.length - a.prefix.length; });
    
    for (var i = 0; i < routes.length; i++) {
        var r = routes[i];
        if (path.indexOf(r.prefix) === 0) {
            targetProvider = r.provider;
            routePrefix = r.prefix;
            matchedPath = r.prefix;
            break;
        }
    }
    
    // 未匹配路由
    if (!targetProvider) {
        return {
            status: 404,
            headers: {'content-type': 'application/json'},
            body: JSON.stringify({
                error: 'route_not_found',
                message: 'Unknown provider path',
                path: path,
                request_id: reqId
            })
        };
    }
    
    var upstream = CONFIG.UPSTREAM[targetProvider];
    if (!upstream) {
        return {
            status: 500,
            headers: {'content-type': 'application/json'},
            body: JSON.stringify({
                error: 'config_error',
                message: 'Provider not configured',
                request_id: reqId
            })
        };
    }
    
    // ========== 2. 提取身份信息 ==========
    var userId = headers['x-user-id'] || 
                 request.query['user_id'] || 
                 'anonymous';
                 
    var department = headers['x-department'] || 
                     request.query['dept'] || 
                     'unknown';
                     
    var project = headers['x-project'] || 
                  request.query['project'] || 
                  'default';
    
    // API Key 处理
    var authHeader = headers['authorization'] || '';
    var apiKey = '';
    var keyType = 'unknown';
    
    if (authHeader.indexOf('Bearer ') === 0) {
        var bearer = authHeader.substring(7);
        // 解析公司密钥格式: pk_xxx.user_id
        var parts = bearer.split('.');
        if (parts.length >= 2) {
            apiKey = parts[0];
            if (userId === 'anonymous') {
                userId = parts[1];
            }
            keyType = 'company';
        } else {
            apiKey = bearer.substring(0, 20) + '...'; // 脱敏
            keyType = 'external';
        }
    } else if (authHeader.indexOf('Api-Key ') === 0) {
        apiKey = authHeader.substring(8, 28) + '...';
        keyType = 'api-key';
    }
    
    // ========== 3. 解析 Body 提取 Content ==========
    var requestBody = request.body || '';
    var isStream = false;
    var modelName = 'unknown';
    var userContents = [];
    var hasImage = false;
    var bodyTooLarge = false;
    
    if ((method === 'POST' || method === 'PUT') && requestBody) {
        // 检查 body 大小
        if (requestBody.length > CONFIG.MAX_BODY_SIZE) {
            bodyTooLarge = true;
        } else {
            var payload = safeJSONParse(requestBody);
            if (payload) {
                // 检查是否流式
                isStream = payload.stream === true;
                modelName = payload.model || 'unknown';
                
                // 提取内容
                userContents = extractContents(requestBody);
                
                // 检测多模态
                for (var j = 0; j < userContents.length; j++) {
                    if (userContents[j].content.indexOf('[image]') >= 0 ||
                        userContents[j].content.indexOf('[image_url]') >= 0) {
                        hasImage = true;
                        break;
                    }
                }
            }
        }
    }
    
    // 压缩内容用于上报
    var compressedContents = compressContent(userContents, 3000);
    var totalInputChars = 0;
    for (var k = 0; k < userContents.length; k++) {
        totalInputChars += userContents[k].length;
    }
    
    // ========== 4. 构建审计日志 ==========
    var auditLog = {
        v: '1.0',
        request_id: reqId,
        timestamp: new Date().toISOString(),
        provider: targetProvider,
        model: modelName,
        stream: isStream,
        
        user: {
            user_id: userId,
            department: department,
            project: project,
            client_ip: getClientIP(request),
            user_agent: headers['user-agent'] || '',
            key_type: keyType
        },
        
        request: {
            method: method,
            path: path,
            query: Object.keys(request.query || {}).length > 0 ? request.query : undefined,
            content_summary: {
                message_count: userContents.length,
                total_chars: totalInputChars,
                has_image: hasImage,
                body_truncated: bodyTooLarge
            },
            contents: compressedContents
        },
        
        edge: {
            node: request.serverName || 'unknown',
            start_time: startTime,
            sampling: CONFIG.SAMPLING_RATE < 1.0 ? CONFIG.SAMPLING_RATE : undefined
        }
    };
    
    // ========== 5. 异步上报审计（采样控制）==========
    if (shouldSample()) {
        try {
            // 使用 fire-and-forget 方式上报
            httpRequest({
                url: CONFIG.AUDIT_ENDPOINT,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Audit-Source': 'wangsu-edge',
                    'X-Request-ID': reqId,
                    'X-Edge-Node': request.serverName || 'unknown'
                },
                body: JSON.stringify(auditLog),
                timeout: 2000  // 2秒超时，不影响主请求
            });
        } catch (e) {
            // 上报失败静默处理，可在响应头中添加标记
            // 生产环境建议开启网宿日志服务作为兜底
        }
    }
    
    // ========== 6. 准备转发到上游 ==========
    
    // 6.1 清理内部 Header
    delete request.headers['x-user-id'];
    delete request.headers['x-department'];
    delete request.headers['x-project'];
    delete request.headers['x-internal-token'];
    
    // 6.2 添加追踪 Header（透传到后端或用于日志）
    request.headers['x-audit-req-id'] = reqId;
    request.headers['x-forwarded-user'] = userId;
    request.headers['x-forwarded-dept'] = department;
    
    // 6.3 重写 Host 指向目标上游
    request.headers['host'] = upstream.origin;
    
    // 6.4 设置转发目标
    request.origin = upstream.origin;
    request.protocol = upstream.protocol || 'https';
    
    // 6.5 路径重写
    var newPath = path;
    
    // 通用前缀移除
    if (routePrefix && newPath.indexOf(routePrefix) === 0) {
        newPath = newPath.substring(routePrefix.length);
    }
    
    // 特殊供应商路径重写
    if (upstream.pathRewrite && upstream.pathRewrite[matchedPath]) {
        newPath = newPath.replace(matchedPath, upstream.pathRewrite[matchedPath]);
    }
    
    // Azure 特殊处理
    if (targetProvider === 'azure' && request.query) {
        request.query['api-version'] = upstream.apiVersion;
    }
    
    // 确保路径以 / 开头
    if (newPath.indexOf('/') !== 0) {
        newPath = '/' + newPath;
    }
    
    request.path = newPath;
    
    // 6.6 API Key 映射（如果用公司统一密钥）
    // 这里需要从配置或 KMS 获取真实密钥
    // request.headers['authorization'] = 'Bearer ' + getRealApiKey(targetProvider);
    
    // 继续执行（透传）
    return request;
}

/**
 * 响应处理 - 添加追踪 Header
 */
function onResponse(response, request) {
    // 透传审计 ID，便于问题排查
    var reqId = request.headers['x-audit-req-id'] || '';
    if (reqId) {
        response.headers['x-audit-req-id'] = reqId;
    }
    response.headers['x-gateway'] = 'wangsu-edge-v1';
    
    // 可选：记录响应状态码（需要开启日志服务）
    return response;
}
```

---

## 网宿 EdgeScript 配置说明

### 关键配置项

| 配置项 | 说明 | 示例值 |
|-------|------|--------|
| `AUDIT_ENDPOINT` | 你的中心网关接收地址 | `https://audit.yourcompany.com/api/v1/log` |
| `SAMPLING_RATE` | 审计采样率 | `1.0` (100%), `0.1` (10%) |
| `MAX_BODY_SIZE` | 最大解析 body 大小 | `1048576` (1MB) |

### 上游模型配置

```javascript
UPSTREAM: {
    'openai': {
        origin: 'api.openai.com',
        protocol: 'https'
    },
    'azure': {
        origin: 'your-resource.openai.azure.com',
        protocol: 'https',
        apiVersion: '2024-02-01'
    }
    // ... 其他供应商
}
```

### 路由映射规则

```javascript
ROUTE_MAP: {
    '/v1/openai': 'openai',    // /v1/openai/chat/completions -> api.openai.com/v1/chat/completions
    '/v1/claude': 'claude',    // /v1/claude/messages -> api.anthropic.com/v1/messages
    '/v1/qwen': 'qwen'         // /v1/qwen/chat/completions -> dashscope.aliyuncs.com/...
}
```

---

## 中心网关 API 文档

### 审计日志接收

```http
POST /api/v1/log
X-Audit-Source: wangsu-edge
X-Request-ID: xxx
Content-Type: application/json

{
    "v": "1.0",
    "request_id": "uuid",
    "timestamp": "2024-01-15T09:30:00.123Z",
    "provider": "openai",
    "model": "gpt-4",
    "stream": false,
    "user": {
        "user_id": "zhangsan",
        "department": "研发部",
        "client_ip": "10.0.1.100"
    },
    "request": {
        "method": "POST",
        "path": "/v1/chat/completions",
        "content_summary": {...},
        "contents": [...]
    }
}
```

### 管理后台 API

```http
# 查询审计日志
GET /api/v1/admin/logs?user_id=xxx&department=xxx&page=1
X-Admin-Token: your-token

# 获取用户历史
GET /api/v1/admin/users/{user_id}/history?days=7
X-Admin-Token: your-token

# 获取统计仪表盘
GET /api/v1/stats/dashboard
X-Admin-Token: your-token

# 获取活跃用户排行
GET /api/v1/stats/users/top?limit=20
X-Admin-Token: your-token
```

---

## 用户接入指南

### 环境变量方式（推荐）

```bash
# 修改 API Base URL
export OPENAI_API_BASE="https://your-wangsu-cdn.com/v1/openai"
export OPENAI_API_KEY="pk-12345.user-id"

# 代码完全兼容标准 OpenAI SDK
python your_script.py
```

### Cursor / VSCode 配置

在 Cursor 设置中修改：
```
OpenAI API Base URL: https://your-wangsu-cdn.com/v1/openai
OpenAI API Key: pk-12345.user-id
```

### Python 代码示例

```python
import openai

# 修改 base URL 和 key
openai.api_base = "https://your-wangsu-cdn.com/v1/openai"
openai.api_key = "pk-12345.user-id"

# 其余代码完全不变
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## 常见问题

### Q1: 审计日志上报失败怎么办？

网宿边缘函数是 **fire-and-forget** 模式，上报失败不会重试。建议：

1. 开启网宿日志服务（CLS）作为兜底
2. 中心网关做补全：通过上游 API Key 的调用记录对账

### Q2: 流式响应（SSE）能审计吗？

- **输入内容**：可以完整审计（在请求时解析）
- **输出内容**：网宿边缘函数不支持拦截 SSE 流，如需审计输出，需要在中心网关反向代理层实现

### Q3: 如何添加新的模型供应商？

1. 在 `UPSTREAM` 中添加配置
2. 在 `ROUTE_MAP` 中添加路由映射
3. 如有需要，在 `extractContents` 中处理特殊格式

### Q4: 敏感词检测不生效？

敏感词检测在中心网关进行，检查：
- `ENABLE_SENSITIVE_CHECK` 是否设置为 `true`
- `sensitive_check.py` 中的词库是否符合需求

---

## 目录结构

```
secureAI/
├── wangsu-edge-script.js          # 网宿边缘函数代码
├── README.md                       # 本文档
└── audit-gateway/                  # 中心网关
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    ├── init.sql                    # ClickHouse 初始化
    ├── static/
    │   └── index.html              # 管理后台前端
    └── app/
        ├── main.py                 # FastAPI 入口
        ├── config.py               # 配置
        ├── models.py               # 数据模型
        ├── database.py             # 数据库连接
        ├── routers/                # API 路由
        │   ├── audit.py
        │   ├── admin.py
        │   └── stats.py
        └── services/               # 业务服务
            ├── audit_writer.py
            ├── sensitive_check.py
            └── alert_service.py
```

---

## License

MIT License
