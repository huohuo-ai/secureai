from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class RoleType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ContentItem(BaseModel):
    role: str
    content: str
    length: int


class UserInfo(BaseModel):
    user_id: str
    department: str = "unknown"
    project: str = "default"
    client_ip: str
    user_agent: Optional[str] = None
    key_type: str = "unknown"


class ContentSummary(BaseModel):
    message_count: int
    total_chars: int
    has_image: bool = False
    body_truncated: bool = False


class RequestDetail(BaseModel):
    method: str
    path: str
    query: Optional[Dict] = None
    content_summary: ContentSummary
    contents: List[ContentItem]


class EdgeInfo(BaseModel):
    node: str
    start_time: int
    sampling: Optional[float] = None


class AuditLog(BaseModel):
    v: str = "1.0"
    request_id: str
    timestamp: datetime
    provider: str
    model: str
    stream: bool = False
    user: UserInfo
    request: RequestDetail
    edge: EdgeInfo
    
    # 中心网关补充字段
    received_at: Optional[datetime] = None
    risk_level: Optional[str] = "low"  # low, medium, high
    sensitive_words: Optional[List[str]] = None


# 查询参数模型
class AuditQuery(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[str] = None
    department: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    risk_level: Optional[str] = None
    keyword: Optional[str] = None
    page: int = 1
    page_size: int = 20


# 统计响应模型
class UsageStats(BaseModel):
    total_requests: int
    total_users: int
    total_departments: int
    total_input_chars: int
    total_cost_estimate: float  # 估算成本
    by_provider: Dict[str, int]
    by_model: Dict[str, int]
    by_department: Dict[str, int]
    time_series: List[Dict[str, Any]]  # 时间序列数据
