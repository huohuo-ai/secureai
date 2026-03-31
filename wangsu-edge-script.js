/**
 * AI Gateway - 网宿 EdgeScript
 * 功能：请求转发 + Content提取 + 审计上报
 * 版本：v1.1.0
 */

// ==================== 全局配置 ====================
var CONFIG = {
    // 中心网关地址（需替换为你的实际域名）
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
    
    // 路由映射
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
    
    // 按长度降序匹配
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
        var parts = bearer.split('.');
        if (parts.length >= 2) {
            apiKey = parts[0];
            if (userId === 'anonymous') {
                userId = parts[1];
            }
            keyType = 'company';
        } else {
            apiKey = bearer.substring(0, 20) + '...';
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
        if (requestBody.length > CONFIG.MAX_BODY_SIZE) {
            bodyTooLarge = true;
        } else {
            var payload = safeJSONParse(requestBody);
            if (payload) {
                isStream = payload.stream === true;
                modelName = payload.model || 'unknown';
                userContents = extractContents(requestBody);
                
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
    
    // ========== 5. 异步上报审计 ==========
    if (shouldSample()) {
        try {
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
                timeout: 2000
            });
        } catch (e) {
            // 上报失败静默处理
        }
    }
    
    // ========== 6. 准备转发到上游 ==========
    
    // 6.1 清理内部 Header
    delete request.headers['x-user-id'];
    delete request.headers['x-department'];
    delete request.headers['x-project'];
    delete request.headers['x-internal-token'];
    
    // 6.2 添加追踪 Header
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
    
    if (routePrefix && newPath.indexOf(routePrefix) === 0) {
        newPath = newPath.substring(routePrefix.length);
    }
    
    if (upstream.pathRewrite && upstream.pathRewrite[matchedPath]) {
        newPath = newPath.replace(matchedPath, upstream.pathRewrite[matchedPath]);
    }
    
    if (targetProvider === 'azure' && request.query) {
        request.query['api-version'] = upstream.apiVersion;
    }
    
    if (newPath.indexOf('/') !== 0) {
        newPath = '/' + newPath;
    }
    
    request.path = newPath;
    
    // 继续执行
    return request;
}

/**
 * 响应处理 - 添加追踪 Header
 */
function onResponse(response, request) {
    var reqId = request.headers['x-audit-req-id'] || '';
    if (reqId) {
        response.headers['x-audit-req-id'] = reqId;
    }
    response.headers['x-gateway'] = 'wangsu-edge-v1';
    
    return response;
}
