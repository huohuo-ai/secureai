import uuid
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import httpx

from app.models.database import get_db
from app.models.models import AuditStatus
from app.services.audit_service import AuditService
from app.core.config import settings


router = APIRouter(prefix="/v1", tags=["proxy"])


# OpenAI Compatible Models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    user: Optional[str] = None
    
    # 自定义审计字段
    x_department: Optional[str] = Field(None, alias="x-department")
    x_project: Optional[str] = Field(None, alias="x-project")
    
    class Config:
        populate_by_name = True


class CompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Dict[str, int]


# Mock AI 响应用于演示
MOCK_RESPONSES = {
    "default": "我是一个AI助手，这是模拟的响应消息。在实际部署中，这里会返回真实AI模型的响应。",
    "code": """```python
def hello_world():
    print("Hello, World!")
    return True
```

这是一个简单的Python函数示例。""",
    "business": "根据您提供的业务数据，我建议：\n\n1. 优化现有流程，提高效率\n2. 加强数据安全措施\n3. 定期审查合规性\n\n具体实施计划需要根据详细情况制定。",
    "blocked": "请求因安全策略被阻断。检测到潜在风险内容，请联系管理员了解更多信息。"
}


def count_tokens(text: str) -> int:
    """简化的Token计数（实际应使用tiktoken）"""
    # 粗略估计：1个token约等于4个字符
    return len(text) // 4


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="x-user-id"),
    x_department: Optional[str] = Header(None, alias="x-department"),
    x_project: Optional[str] = Header(None, alias="x-project"),
    db: AsyncSession = Depends(get_db)
):
    """
    代理AI模型调用，同时记录审计日志
    兼容OpenAI API格式
    """
    start_time = time.time()
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    
    # 获取用户信息
    user_id = x_user_id or f"user_{uuid.uuid4().hex[:8]}"
    department = x_department or "default"
    project = x_project or "default"
    
    # 构建完整输入
    input_content = "\n".join([f"{m.role}: {m.content}" for m in request.messages])
    input_tokens = count_tokens(input_content)
    
    # 创建审计服务
    audit_service = AuditService(db)
    
    # 检查用户配额
    quota_allowed, quota_info = await audit_service.check_quota(user_id, input_tokens + (request.max_tokens or 1000))
    
    if not quota_allowed:
        # 配额不足，记录审计日志并返回错误
        latency_ms = int((time.time() - start_time) * 1000)
        audit_log = await audit_service.create_audit_log(
            request_id=request_id,
            user_id=user_id,
            provider="openai",
            model=request.model,
            input_content=input_content,
            output_content="Quota exceeded",
            input_tokens=input_tokens,
            output_tokens=0,
            latency_ms=latency_ms,
            status=AuditStatus.BLOCKED,
            department=department,
            project=project,
            client_ip=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
            session_id=None,
            metadata={"quota_info": quota_info, "block_reason": "quota_exceeded"}
        )
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Quota exceeded",
                "message": "Daily or monthly token limit exceeded",
                "quota_info": quota_info
            }
        )
    
    # 风险检测（输入）
    should_block, risk_results, sensitive_results = await audit_service.detect_and_record_risks(
        audit_log=None,  # 先检测，后创建日志
        input_content=input_content,
        user_quota=quota_info
    )
    
    # 如果需要阻断
    if should_block:
        latency_ms = int((time.time() - start_time) * 1000)
        audit_log = await audit_service.create_audit_log(
            request_id=request_id,
            user_id=user_id,
            provider="openai",
            model=request.model,
            input_content=input_content,
            output_content="Blocked by security policy",
            input_tokens=input_tokens,
            output_tokens=0,
            latency_ms=latency_ms,
            status=AuditStatus.BLOCKED,
            department=department,
            project=project,
            client_ip=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
            metadata={"block_reason": "risk_detected", "risks": [r.rule_name for r in risk_results]}
        )
        
        # 重新记录风险（这次关联到实际的audit_log）
        await audit_service.detect_and_record_risks(
            audit_log=audit_log,
            input_content=input_content,
            user_quota=quota_info
        )
        
        await db.commit()
        
        # 返回阻断响应
        if request.stream:
            async def blocked_stream():
                data = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": MOCK_RESPONSES["blocked"]},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(blocked_stream(), media_type="text/event-stream")
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "id": request_id,
                    "object": "chat.completion",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": MOCK_RESPONSES["blocked"]
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {"prompt_tokens": input_tokens, "completion_tokens": 20, "total_tokens": input_tokens + 20}
                }
            )
    
    # 模拟调用AI模型（实际应调用真实API）
    # 这里根据输入内容选择不同的模拟响应
    if "code" in input_content.lower() or "python" in input_content.lower() or "def " in input_content:
        output_content = MOCK_RESPONSES["code"]
    elif "business" in input_content.lower() or "战略" in input_content or "数据" in input_content:
        output_content = MOCK_RESPONSES["business"]
    else:
        output_content = MOCK_RESPONSES["default"]
    
    # 模拟延迟
    await __import__('asyncio').sleep(0.5)
    
    latency_ms = int((time.time() - start_time) * 1000)
    output_tokens = count_tokens(output_content)
    
    # 创建审计日志
    audit_log = await audit_service.create_audit_log(
        request_id=request_id,
        user_id=user_id,
        provider="openai",
        model=request.model,
        input_content=input_content,
        output_content=output_content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status=AuditStatus.SUCCESS,
        department=department,
        project=project,
        client_ip=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("user-agent"),
        metadata={"stream": request.stream, "temperature": request.temperature}
    )
    
    # 记录风险检测结果
    await audit_service.detect_and_record_risks(
        audit_log=audit_log,
        input_content=input_content,
        output_content=output_content,
        user_quota=quota_info
    )
    
    # 更新用户配额
    await audit_service.update_user_quota(user_id, input_tokens + output_tokens, audit_log.estimated_cost)
    
    await db.commit()
    
    # 返回响应
    if request.stream:
        async def generate_stream():
            words = output_content.split()
            for i, word in enumerate(words):
                data = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": word + " "},
                        "finish_reason": None if i < len(words) - 1 else "stop"
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
                await __import__('asyncio').sleep(0.05)
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    else:
        return {
            "id": request_id,
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": output_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        }


@router.post("/completions")
async def completions(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """兼容OpenAI的completions API（简化版）"""
    body = await request.json()
    
    # 转换为chat/completions格式处理
    prompt = body.get("prompt", "")
    chat_request = ChatCompletionRequest(
        model=body.get("model", "gpt-3.5-turbo"),
        messages=[ChatMessage(role="user", content=prompt)],
        temperature=body.get("temperature", 0.7),
        max_tokens=body.get("max_tokens"),
        stream=body.get("stream", False),
        user=body.get("user")
    )
    
    return await chat_completions(
        request=chat_request,
        http_request=request,
        authorization=request.headers.get("authorization"),
        x_user_id=request.headers.get("x-user-id"),
        x_department=request.headers.get("x-department"),
        x_project=request.headers.get("x-project"),
        db=db
    )


@router.get("/models")
async def list_models():
    """列出可用的AI模型"""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4-turbo",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai"
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677649963,
                "owned_by": "openai"
            },
            {
                "id": "claude-3-opus",
                "object": "model",
                "created": 1687882411,
                "owned_by": "anthropic"
            },
            {
                "id": "claude-3-sonnet",
                "object": "model",
                "created": 1687882411,
                "owned_by": "anthropic"
            }
        ]
    }
