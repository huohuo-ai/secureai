from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.models.models import AuditLog, RiskDetection, SensitiveDataHit, AuditStatus, RiskLevel
from app.services.audit_service import AuditService


router = APIRouter(prefix="/api/audit", tags=["audit"])


# Pydantic Models
class AuditLogResponse(BaseModel):
    id: str
    request_id: str
    user_id: str
    department: Optional[str]
    project: Optional[str]
    provider: str
    model: str
    request_time: datetime
    response_time: Optional[datetime]
    latency_ms: Optional[int]
    status: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    input_preview: Optional[str]
    output_preview: Optional[str]
    client_ip: Optional[str]
    risk_count: int = 0
    
    class Config:
        from_attributes = True


class AuditLogDetailResponse(AuditLogResponse):
    full_input: Optional[str]
    full_output: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    metadata: dict
    data_residency_compliant: bool
    gdpr_compliant: bool
    risk_detections: list = []
    sensitive_data_hits: list = []


class RiskDetectionResponse(BaseModel):
    id: str
    risk_type: str
    risk_level: str
    detection_rule: str
    detected_content: Optional[str]
    confidence_score: float
    action_taken: str
    blocked: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SensitiveDataHitResponse(BaseModel):
    id: str
    data_type: str
    detection_method: str
    matched_pattern: Optional[str]
    masked_content: Optional[str]
    position: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    total_requests: int
    input_tokens: int
    output_tokens: int
    total_cost: float
    status_distribution: dict
    risk_distribution: dict
    sensitive_data_distribution: dict
    period_days: int


class DailyStatsResponse(BaseModel):
    date: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost: float


# API Endpoints

@router.get("/logs", response_model=dict)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    department: Optional[str] = None,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    risk_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取审计日志列表"""
    service = AuditService(db)
    
    # 转换枚举
    status_enum = AuditStatus(status) if status else None
    risk_enum = RiskLevel(risk_level) if risk_level else None
    
    logs, total = await service.get_audit_logs(
        skip=skip,
        limit=limit,
        user_id=user_id,
        department=department,
        provider=provider,
        status=status_enum,
        start_date=start_date,
        end_date=end_date,
        risk_level=risk_enum
    )
    
    # 构建响应
    result = []
    for log in logs:
        result.append({
            "id": str(log.id),
            "request_id": log.request_id,
            "user_id": log.user_id,
            "department": log.department,
            "project": log.project,
            "provider": log.provider,
            "model": log.model,
            "request_time": log.request_time,
            "response_time": log.response_time,
            "latency_ms": log.latency_ms,
            "status": log.status.value,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "estimated_cost": float(log.estimated_cost),
            "input_preview": log.input_preview,
            "output_preview": log.output_preview,
            "client_ip": log.client_ip,
            "risk_count": len(log.risk_detections)
        })
    
    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/logs/{log_id}", response_model=dict)
async def get_audit_log_detail(
    log_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取审计日志详情"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # 解密内容
    service = AuditService(db)
    full_input = service._decrypt_content(log.full_input) if log.full_input else None
    full_output = service._decrypt_content(log.full_output) if log.full_output else None
    
    return {
        "id": str(log.id),
        "request_id": log.request_id,
        "user_id": log.user_id,
        "department": log.department,
        "project": log.project,
        "provider": log.provider,
        "model": log.model,
        "request_time": log.request_time,
        "response_time": log.response_time,
        "latency_ms": log.latency_ms,
        "status": log.status.value,
        "input_tokens": log.input_tokens,
        "output_tokens": log.output_tokens,
        "estimated_cost": float(log.estimated_cost),
        "input_preview": log.input_preview,
        "output_preview": log.output_preview,
        "full_input": full_input,
        "full_output": full_output,
        "client_ip": log.client_ip,
        "user_agent": log.user_agent,
        "session_id": log.session_id,
        "metadata": log.log_metadata,
        "data_residency_compliant": log.data_residency_compliant,
        "gdpr_compliant": log.gdpr_compliant,
        "risk_detections": [
            {
                "id": str(r.id),
                "risk_type": r.risk_type.value,
                "risk_level": r.risk_level.value,
                "detection_rule": r.detection_rule,
                "detected_content": r.detected_content,
                "confidence_score": r.confidence_score,
                "action_taken": r.action_taken.value,
                "blocked": r.blocked,
                "created_at": r.created_at
            }
            for r in log.risk_detections
        ],
        "sensitive_data_hits": [
            {
                "id": str(s.id),
                "data_type": s.data_type.value,
                "detection_method": s.detection_method.value,
                "matched_pattern": s.matched_pattern,
                "masked_content": s.masked_content,
                "position": s.position,
                "created_at": s.created_at
            }
            for s in log.sensitive_data_hits
        ]
    }


@router.get("/stats/summary", response_model=AuditStatsResponse)
async def get_audit_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """获取审计统计摘要"""
    service = AuditService(db)
    stats = await service.get_audit_stats(days)
    return AuditStatsResponse(**stats)


@router.get("/stats/trends", response_model=List[DailyStatsResponse])
async def get_daily_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """获取每日趋势统计"""
    service = AuditService(db)
    stats = await service.get_daily_stats(days)
    return [DailyStatsResponse(**s) for s in stats]


@router.get("/risk/events", response_model=dict)
async def get_risk_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    risk_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取风险事件列表"""
    from sqlalchemy import select
    
    query = select(RiskDetection).order_by(RiskDetection.created_at.desc())
    
    if risk_type:
        query = query.where(RiskDetection.risk_type == risk_type)
    if risk_level:
        query = query.where(RiskDetection.risk_level == risk_level)
    if start_date:
        query = query.where(RiskDetection.created_at >= start_date)
    if end_date:
        query = query.where(RiskDetection.created_at <= end_date)
    
    # 获取总数
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(e.id),
                "audit_log_id": str(e.audit_log_id),
                "risk_type": e.risk_type.value,
                "risk_level": e.risk_level.value,
                "detection_rule": e.detection_rule,
                "detected_content": e.detected_content,
                "confidence_score": e.confidence_score,
                "action_taken": e.action_taken.value,
                "blocked": e.blocked,
                "created_at": e.created_at
            }
            for e in events
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/sensitive-data/hits", response_model=dict)
async def get_sensitive_data_hits(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    data_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取敏感数据命中记录"""
    from sqlalchemy import select, func
    
    query = select(SensitiveDataHit).order_by(SensitiveDataHit.created_at.desc())
    
    if data_type:
        query = query.where(SensitiveDataHit.data_type == data_type)
    if start_date:
        query = query.where(SensitiveDataHit.created_at >= start_date)
    if end_date:
        query = query.where(SensitiveDataHit.created_at <= end_date)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    hits = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(h.id),
                "audit_log_id": str(h.audit_log_id),
                "data_type": h.data_type.value,
                "detection_method": h.detection_method.value,
                "matched_pattern": h.matched_pattern,
                "masked_content": h.masked_content,
                "position": h.position,
                "created_at": h.created_at
            }
            for h in hits
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }
