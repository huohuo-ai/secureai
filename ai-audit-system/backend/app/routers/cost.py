from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, cast, Date
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.models.models import UserQuota, AuditLog


router = APIRouter(prefix="/api/cost", tags=["cost"])


# Pydantic Models
class UserQuotaResponse(BaseModel):
    id: str
    user_id: str
    department: Optional[str]
    daily_limit: int
    monthly_limit: int
    daily_used: int
    monthly_used: int
    cost_budget: float
    cost_used: float
    reset_date: Optional[datetime]
    created_at: datetime


class UserQuotaUpdate(BaseModel):
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    cost_budget: Optional[float] = None


class UsageResponse(BaseModel):
    user_id: str
    department: Optional[str]
    period: str
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float


class DepartmentCostResponse(BaseModel):
    department: str
    total_requests: int
    total_tokens: int
    total_cost: float
    user_count: int


class BillingResponse(BaseModel):
    period: str
    total_cost: float
    total_requests: int
    total_tokens: int
    breakdown: List[dict]


# API Endpoints

@router.get("/quotas", response_model=dict)
async def get_user_quotas(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取用户配额列表"""
    query = select(UserQuota).order_by(UserQuota.created_at.desc())
    
    if department:
        query = query.where(UserQuota.department == department)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    quotas = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(q.id),
                "user_id": q.user_id,
                "department": q.department,
                "daily_limit": q.daily_limit,
                "monthly_limit": q.monthly_limit,
                "daily_used": q.daily_used,
                "monthly_used": q.monthly_used,
                "cost_budget": float(q.cost_budget),
                "cost_used": float(q.cost_used),
                "reset_date": q.reset_date,
                "created_at": q.created_at
            }
            for q in quotas
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/quotas/{user_id}", response_model=UserQuotaResponse)
async def get_user_quota(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取特定用户的配额"""
    result = await db.execute(
        select(UserQuota).where(UserQuota.user_id == user_id)
    )
    quota = result.scalar_one_or_none()
    
    if not quota:
        raise HTTPException(status_code=404, detail="User quota not found")
    
    return UserQuotaResponse(
        id=str(quota.id),
        user_id=quota.user_id,
        department=quota.department,
        daily_limit=quota.daily_limit,
        monthly_limit=quota.monthly_limit,
        daily_used=quota.daily_used,
        monthly_used=quota.monthly_used,
        cost_budget=float(quota.cost_budget),
        cost_used=float(quota.cost_used),
        reset_date=quota.reset_date,
        created_at=quota.created_at
    )


@router.put("/quotas/{user_id}", response_model=UserQuotaResponse)
async def update_user_quota(
    user_id: str,
    update: UserQuotaUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新用户配额"""
    result = await db.execute(
        select(UserQuota).where(UserQuota.user_id == user_id)
    )
    quota = result.scalar_one_or_none()
    
    if not quota:
        raise HTTPException(status_code=404, detail="User quota not found")
    
    if update.daily_limit is not None:
        quota.daily_limit = update.daily_limit
    if update.monthly_limit is not None:
        quota.monthly_limit = update.monthly_limit
    if update.cost_budget is not None:
        quota.cost_budget = Decimal(str(update.cost_budget))
    
    await db.commit()
    await db.refresh(quota)
    
    return UserQuotaResponse(
        id=str(quota.id),
        user_id=quota.user_id,
        department=quota.department,
        daily_limit=quota.daily_limit,
        monthly_limit=quota.monthly_limit,
        daily_used=quota.daily_used,
        monthly_used=quota.monthly_used,
        cost_budget=float(quota.cost_budget),
        cost_used=float(quota.cost_used),
        reset_date=quota.reset_date,
        created_at=quota.created_at
    )


@router.get("/usage", response_model=dict)
async def get_usage(
    user_id: Optional[str] = None,
    department: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_by: str = Query("user", enum=["user", "department", "day"]),
    db: AsyncSession = Depends(get_db)
):
    """获取用量统计"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    query = select(AuditLog).where(
        and_(
            AuditLog.request_time >= start_date,
            AuditLog.request_time <= end_date
        )
    )
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if department:
        query = query.where(AuditLog.department == department)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # 按指定维度分组
    if group_by == "user":
        grouped = {}
        for log in logs:
            key = log.user_id
            if key not in grouped:
                grouped[key] = {
                    "user_id": key,
                    "department": log.department,
                    "total_requests": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost": 0.0
                }
            grouped[key]["total_requests"] += 1
            grouped[key]["total_input_tokens"] += log.input_tokens
            grouped[key]["total_output_tokens"] += log.output_tokens
            grouped[key]["total_cost"] += float(log.estimated_cost)
        return {"items": list(grouped.values())}
    
    elif group_by == "department":
        grouped = {}
        for log in logs:
            key = log.department or "unknown"
            if key not in grouped:
                grouped[key] = {
                    "department": key,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "users": set()
                }
            grouped[key]["total_requests"] += 1
            grouped[key]["total_tokens"] += log.input_tokens + log.output_tokens
            grouped[key]["total_cost"] += float(log.estimated_cost)
            grouped[key]["users"].add(log.user_id)
        
        result = []
        for key, value in grouped.items():
            result.append({
                "department": key,
                "total_requests": value["total_requests"],
                "total_tokens": value["total_tokens"],
                "total_cost": value["total_cost"],
                "user_count": len(value["users"])
            })
        return {"items": result}
    
    else:  # day
        grouped = {}
        for log in logs:
            key = log.request_time.date().isoformat()
            if key not in grouped:
                grouped[key] = {
                    "date": key,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                }
            grouped[key]["total_requests"] += 1
            grouped[key]["total_tokens"] += log.input_tokens + log.output_tokens
            grouped[key]["total_cost"] += float(log.estimated_cost)
        
        # 填充缺失的日期
        from datetime import date
        current = start_date.date()
        end = end_date.date()
        while current <= end:
            key = current.isoformat()
            if key not in grouped:
                grouped[key] = {
                    "date": key,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                }
            current += timedelta(days=1)
        
        return {"items": sorted(list(grouped.values()), key=lambda x: x["date"])}


@router.get("/billing", response_model=dict)
async def get_billing(
    period: str = Query("current_month", enum=["current_month", "last_month", "last_3_months"]),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取账单信息"""
    
    now = datetime.utcnow()
    
    if period == "current_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "last_month":
        if now.month == 1:
            start_date = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date.replace(day=28) + timedelta(days=4)
        end_date = end_date.replace(day=1) - timedelta(days=1)
    else:  # last_3_months
        start_date = (now.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = now
    
    query = select(AuditLog).where(
        and_(
            AuditLog.request_time >= start_date,
            AuditLog.request_time <= end_date
        )
    )
    
    if department:
        query = query.where(AuditLog.department == department)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # 按部门分组
    breakdown = {}
    for log in logs:
        dept = log.department or "unknown"
        if dept not in breakdown:
            breakdown[dept] = {
                "department": dept,
                "requests": 0,
                "tokens": 0,
                "cost": 0.0
            }
        breakdown[dept]["requests"] += 1
        breakdown[dept]["tokens"] += log.input_tokens + log.output_tokens
        breakdown[dept]["cost"] += float(log.estimated_cost)
    
    return {
        "period": period,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_cost": sum(float(log.estimated_cost) for log in logs),
        "total_requests": len(logs),
        "total_tokens": sum(log.input_tokens + log.output_tokens for log in logs),
        "breakdown": list(breakdown.values())
    }


@router.get("/dashboard", response_model=dict)
async def get_cost_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """获取成本管控仪表板数据"""
    
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 今日统计
    today_result = await db.execute(
        select(
            func.count(AuditLog.id),
            func.sum(AuditLog.estimated_cost),
            func.sum(AuditLog.input_tokens + AuditLog.output_tokens)
        ).where(AuditLog.request_time >= today)
    )
    today_stats = today_result.first()
    
    # 本月统计
    month_result = await db.execute(
        select(
            func.count(AuditLog.id),
            func.sum(AuditLog.estimated_cost),
            func.sum(AuditLog.input_tokens + AuditLog.output_tokens)
        ).where(AuditLog.request_time >= this_month)
    )
    month_stats = month_result.first()
    
    # 部门统计
    dept_result = await db.execute(
        select(
            AuditLog.department,
            func.count(AuditLog.id),
            func.sum(AuditLog.estimated_cost)
        ).where(
            AuditLog.request_time >= this_month
        ).group_by(AuditLog.department).order_by(desc(func.sum(AuditLog.estimated_cost)))
    )
    dept_stats = dept_result.all()
    
    # 告警列表（超预算的用户）
    alert_result = await db.execute(
        select(UserQuota).where(
            UserQuota.cost_used > UserQuota.cost_budget * Decimal("0.9")
        )
    )
    alerts = alert_result.scalars().all()
    
    return {
        "today": {
            "requests": today_stats[0] or 0,
            "cost": float(today_stats[1]) if today_stats[1] else 0,
            "tokens": today_stats[2] or 0
        },
        "this_month": {
            "requests": month_stats[0] or 0,
            "cost": float(month_stats[1]) if month_stats[1] else 0,
            "tokens": month_stats[2] or 0
        },
        "department_breakdown": [
            {
                "department": row[0] or "unknown",
                "requests": row[1],
                "cost": float(row[2]) if row[2] else 0
            }
            for row in dept_stats
        ],
        "alerts": [
            {
                "user_id": a.user_id,
                "department": a.department,
                "cost_used": float(a.cost_used),
                "cost_budget": float(a.cost_budget),
                "percentage": float(a.cost_used / a.cost_budget * 100) if a.cost_budget > 0 else 0
            }
            for a in alerts
        ]
    }
