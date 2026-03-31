from fastapi import APIRouter, Query, Depends, Request, HTTPException
from typing import Optional
from datetime import datetime, timedelta
from app.database import ch_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_current_user(request: Request):
    """获取当前登录用户"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/api/v1/admin/logs")
async def query_logs(
    request: Request,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    user_id: Optional[str] = None,
    department: Optional[str] = None,
    provider: Optional[str] = None,
    risk_level: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    查询审计日志（管理后台）
    """
    # 验证登录
    get_current_user(request)
    
    # 默认查询最近24小时
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    query_params = {
        'start_time': start_time,
        'end_time': end_time,
        'user_id': user_id,
        'department': department,
        'provider': provider,
        'risk_level': risk_level,
        'keyword': keyword
    }
    
    # 移除 None 值
    query_params = {k: v for k, v in query_params.items() if v is not None}
    
    offset = (page - 1) * page_size
    result = ch_client.query_audit_logs(query_params, limit=page_size, offset=offset)
    
    return {
        "code": 0,
        "data": result['items'],
        "pagination": {
            "total": result['total'],
            "page": page,
            "page_size": page_size,
            "total_pages": (result['total'] + page_size - 1) // page_size
        }
    }


@router.get("/api/v1/admin/users/{user_id}/history")
async def get_user_history(
    request: Request,
    user_id: str,
    days: int = Query(7, ge=1, le=30)
):
    """获取用户历史记录"""
    get_current_user(request)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    query_params = {
        'start_time': start_time,
        'end_time': end_time,
        'user_id': user_id
    }
    
    result = ch_client.query_audit_logs(query_params, limit=1000, offset=0)
    
    return {
        "user_id": user_id,
        "period_days": days,
        "total": result['total'],
        "history": result['items']
    }


@router.delete("/api/v1/admin/logs/purge")
async def purge_old_logs(
    request: Request,
    before_days: int = Query(365, ge=30)
):
    """
    清理旧日志（ClickHouse TTL 会自动处理，此接口用于紧急清理）
    """
    get_current_user(request)
    
    return {
        "message": "ClickHouse uses TTL for automatic cleanup. Manual purge not recommended.",
        "ttl_days": 365
    }
