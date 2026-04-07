from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from pydantic import BaseModel

from app.models.database import get_db
from app.models.models import AuditLog, RiskDetection, SensitiveDataHit, ComplianceRule


router = APIRouter(prefix="/api/compliance", tags=["compliance"])


# Pydantic Models
class ComplianceReportResponse(BaseModel):
    report_id: str
    report_type: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summary: dict
    details: dict


class ComplianceRuleResponse(BaseModel):
    id: str
    name: str
    rule_type: str
    description: Optional[str]
    action: str
    enabled: bool
    priority: int
    created_at: datetime


# API Endpoints

@router.get("/reports/overview", response_model=dict)
async def get_compliance_overview(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """获取合规概览报告"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 总请求数
    total_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.request_time >= start_date)
    )
    total_requests = total_result.scalar()
    
    # 被阻断的请求
    blocked_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.request_time >= start_date,
                AuditLog.status == "blocked"
            )
        )
    )
    blocked_requests = blocked_result.scalar()
    
    # 风险事件数
    risk_result = await db.execute(
        select(func.count(RiskDetection.id)).where(
            RiskDetection.created_at >= start_date
        )
    )
    total_risks = risk_result.scalar()
    
    # 敏感数据命中
    sensitive_result = await db.execute(
        select(func.count(SensitiveDataHit.id)).where(
            SensitiveDataHit.created_at >= start_date
        )
    )
    total_sensitive = sensitive_result.scalar()
    
    # GDPR合规率
    gdpr_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.request_time >= start_date,
                AuditLog.gdpr_compliant == True
            )
        )
    )
    gdpr_compliant_count = gdpr_result.scalar()
    
    # 数据驻留合规率
    residency_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.request_time >= start_date,
                AuditLog.data_residency_compliant == True
            )
        )
    )
    residency_compliant_count = residency_result.scalar()
    
    # 按风险类型分布
    risk_type_result = await db.execute(
        select(
            RiskDetection.risk_type,
            func.count(RiskDetection.id)
        ).where(
            RiskDetection.created_at >= start_date
        ).group_by(RiskDetection.risk_type)
    )
    risk_type_dist = {row[0]: row[1] for row in risk_type_result.all()}
    
    # 按敏感数据类型分布
    sensitive_type_result = await db.execute(
        select(
            SensitiveDataHit.data_type,
            func.count(SensitiveDataHit.id)
        ).where(
            SensitiveDataHit.created_at >= start_date
        ).group_by(SensitiveDataHit.data_type)
    )
    sensitive_type_dist = {row[0]: row[1] for row in sensitive_type_result.all()}
    
    return {
        "report_id": f"COMP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "report_type": "compliance_overview",
        "generated_at": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        },
        "summary": {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "block_rate": round(blocked_requests / total_requests * 100, 2) if total_requests > 0 else 0,
            "total_risk_events": total_risks,
            "total_sensitive_data_hits": total_sensitive,
            "gdpr_compliance_rate": round(gdpr_compliant_count / total_requests * 100, 2) if total_requests > 0 else 100,
            "data_residency_compliance_rate": round(residency_compliant_count / total_requests * 100, 2) if total_requests > 0 else 100
        },
        "risk_distribution": risk_type_dist,
        "sensitive_data_distribution": sensitive_type_dist
    }


@router.get("/reports/audit-trail", response_model=dict)
async def get_audit_trail_report(
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取审计追踪报告（满足监管要求）"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    query = select(AuditLog).where(
        and_(
            AuditLog.request_time >= start_date,
            AuditLog.request_time <= end_date
        )
    ).order_by(AuditLog.request_time)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    audit_trail = []
    for log in logs:
        audit_trail.append({
            "timestamp": log.request_time.isoformat(),
            "request_id": log.request_id,
            "user_id": log.user_id,
            "department": log.department,
            "action": "ai_model_call",
            "resource": f"{log.provider}/{log.model}",
            "status": log.status,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "client_ip": log.client_ip,
            "session_id": log.session_id,
            "compliance_flags": {
                "gdpr_compliant": log.gdpr_compliant,
                "data_residency_compliant": log.data_residency_compliant
            }
        })
    
    return {
        "report_id": f"TRAIL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "report_type": "audit_trail",
        "generated_at": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "subject": user_id or "all_users",
        "total_records": len(audit_trail),
        "records": audit_trail
    }


@router.get("/reports/gdpr", response_model=dict)
async def get_gdpr_compliance_report(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """获取GDPR合规报告"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 涉及个人数据的请求
    personal_data_result = await db.execute(
        select(
            AuditLog.id,
            AuditLog.request_id,
            AuditLog.user_id,
            AuditLog.request_time,
            AuditLog.gdpr_compliant,
            SensitiveDataHit.data_type
        ).join(
            SensitiveDataHit, AuditLog.id == SensitiveDataHit.audit_log_id
        ).where(
            and_(
                AuditLog.request_time >= start_date,
                SensitiveDataHit.data_type.in_([
                    "id_card", "phone", "email", "personal_info"
                ])
            )
        )
    )
    personal_data_records = personal_data_result.all()
    
    # 数据处理活动统计
    processing_stats = {}
    for row in personal_data_records:
        data_type = row.data_type
        if data_type not in processing_stats:
            processing_stats[data_type] = {
                "count": 0,
                "compliant_count": 0
            }
        processing_stats[data_type]["count"] += 1
        if row.gdpr_compliant:
            processing_stats[data_type]["compliant_count"] += 1
    
    # 数据主体活动（按用户统计）
    subject_activity_result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id)
        ).where(
            AuditLog.request_time >= start_date
        ).group_by(AuditLog.user_id)
    )
    subject_activity = {row[0]: row[1] for row in subject_activity_result.all()}
    
    return {
        "report_id": f"GDPR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "report_type": "gdpr_compliance",
        "generated_at": datetime.utcnow().isoformat(),
        "period_days": days,
        "personal_data_processing": {
            "total_records_with_personal_data": len(personal_data_records),
            "by_data_type": processing_stats
        },
        "data_subject_activity": {
            "total_subjects": len(subject_activity),
            "activity_by_subject": subject_activity
        },
        "compliance_summary": {
            "records_with_personal_data": len(personal_data_records),
            "compliant_records": sum(1 for r in personal_data_records if r.gdpr_compliant),
            "compliance_rate": round(
                sum(1 for r in personal_data_records if r.gdpr_compliant) / len(personal_data_records) * 100, 2
            ) if personal_data_records else 100
        },
        "recommendations": [
            "Review and update data retention policies regularly",
            "Ensure explicit consent for processing sensitive personal data",
            "Implement data minimization practices in AI prompts",
            "Maintain records of processing activities (ROPA)"
        ]
    }


@router.get("/reports/export")
async def export_compliance_data(
    format: str = Query("json", enum=["json", "csv"]),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """导出合规数据用于外部审计"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    query = select(AuditLog).where(
        and_(
            AuditLog.request_time >= start_date,
            AuditLog.request_time <= end_date
        )
    ).order_by(AuditLog.request_time)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if format == "json":
        export_data = []
        for log in logs:
            export_data.append({
                "request_id": log.request_id,
                "timestamp": log.request_time.isoformat(),
                "user_id": log.user_id,
                "department": log.department,
                "provider": log.provider,
                "model": log.model,
                "status": log.status,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "estimated_cost_usd": float(log.estimated_cost),
                "client_ip": log.client_ip,
                "gdpr_compliant": log.gdpr_compliant,
                "data_residency_compliant": log.data_residency_compliant
            })
        
        return JSONResponse(
            content={
                "export_date": datetime.utcnow().isoformat(),
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_records": len(export_data),
                "data": export_data
            }
        )
    
    else:  # CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            "request_id", "timestamp", "user_id", "department", 
            "provider", "model", "status", "input_tokens", 
            "output_tokens", "estimated_cost_usd", "client_ip",
            "gdpr_compliant", "data_residency_compliant"
        ])
        
        # 写入数据
        for log in logs:
            writer.writerow([
                log.request_id,
                log.request_time.isoformat(),
                log.user_id,
                log.department,
                log.provider,
                log.model,
                log.status,
                log.input_tokens,
                log.output_tokens,
                float(log.estimated_cost),
                log.client_ip,
                log.gdpr_compliant,
                log.data_residency_compliant
            ])
        
        content = output.getvalue()
        output.close()
        
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            }
        )


@router.get("/rules", response_model=dict)
async def get_compliance_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    rule_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取合规规则列表"""
    
    query = select(ComplianceRule).order_by(ComplianceRule.priority)
    
    if rule_type:
        query = query.where(ComplianceRule.rule_type == rule_type)
    if enabled is not None:
        query = query.where(ComplianceRule.enabled == enabled)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "rule_type": r.rule_type,
                "description": r.description,
                "action": r.action,
                "enabled": r.enabled,
                "priority": r.priority,
                "conditions": r.conditions,
                "created_at": r.created_at.isoformat()
            }
            for r in rules
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }
