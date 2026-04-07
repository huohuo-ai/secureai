import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, cast, Date
from sqlalchemy.dialects.postgresql import insert

from app.models.models import (
    AuditLog, RiskDetection, SensitiveDataHit, AuditHash, UserQuota,
    AuditStatus, RiskType, RiskLevel, ActionTaken, SensitiveDataType,
    DetectionMethod
)
from app.services.risk_detector import (
    RiskDetectionService, RiskDetectionResult, SensitiveDataResult
)
from app.core.config import settings


class AuditService:
    """审计服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_service = RiskDetectionService()
    
    async def create_audit_log(
        self,
        request_id: str,
        user_id: str,
        provider: str,
        model: str,
        input_content: str,
        output_content: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        status: AuditStatus = AuditStatus.SUCCESS,
        department: str = None,
        project: str = None,
        client_ip: str = None,
        user_agent: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> AuditLog:
        """创建审计日志"""
        
        # 计算预估成本 (简化计算)
        estimated_cost = self._calculate_cost(provider, model, input_tokens, output_tokens)
        
        # 脱敏处理
        input_preview = self._create_preview(input_content)
        output_preview = self._create_preview(output_content) if output_content else ""
        
        # 加密完整内容
        encrypted_input = self._encrypt_content(input_content)
        encrypted_output = self._encrypt_content(output_content) if output_content else ""
        
        # 创建审计日志
        audit_log = AuditLog(
            id=uuid.uuid4(),
            request_id=request_id,
            user_id=user_id,
            department=department,
            project=project,
            provider=provider,
            model=model,
            request_time=datetime.utcnow() - timedelta(milliseconds=latency_ms),
            response_time=datetime.utcnow(),
            latency_ms=latency_ms,
            status=status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            input_preview=input_preview,
            output_preview=output_preview,
            full_input=encrypted_input,
            full_output=encrypted_output,
            client_ip=client_ip,
            user_agent=user_agent,
            session_id=session_id,
            log_metadata=metadata or {},
            data_residency_compliant=self._check_data_residency(provider),
            gdpr_compliant=True
        )
        
        self.db.add(audit_log)
        await self.db.flush()
        
        # 创建哈希链
        await self._create_hash_chain(audit_log)
        
        return audit_log
    
    async def detect_and_record_risks(
        self,
        audit_log: AuditLog,
        input_content: str,
        output_content: str = "",
        user_quota: Dict[str, Any] = None
    ) -> tuple[bool, List[RiskDetectionResult], List[SensitiveDataResult]]:
        """检测并记录风险"""
        
        metadata = {"user_quota": user_quota} if user_quota else {}
        risk_results, sensitive_results = self.risk_service.detect_all(
            input_content, output_content, metadata
        )
        
        # 记录风险检测
        for result in risk_results:
            risk_detection = RiskDetection(
                id=uuid.uuid4(),
                audit_log_id=audit_log.id,
                risk_type=result.risk_type,
                risk_level=result.risk_level,
                detection_rule=result.rule_name,
                detected_content=result.detected_content[:1000],  # 限制长度
                confidence_score=result.confidence,
                action_taken=result.action,
                blocked=result.action == ActionTaken.BLOCK
            )
            self.db.add(risk_detection)
        
        # 记录敏感数据命中
        for result in sensitive_results:
            sensitive_hit = SensitiveDataHit(
                id=uuid.uuid4(),
                audit_log_id=audit_log.id,
                data_type=result.data_type,
                detection_method=result.detection_method,
                matched_pattern=result.pattern,
                masked_content=result.masked_content,
                position=result.position
            )
            self.db.add(sensitive_hit)
        
        await self.db.flush()
        
        # 判断是否阻断
        should_block = self.risk_service.should_block(risk_results)
        
        return should_block, risk_results, sensitive_results
    
    async def update_user_quota(self, user_id: str, tokens_used: int, cost: Decimal):
        """更新用户配额"""
        
        # 获取或创建用户配额记录
        result = await self.db.execute(
            select(UserQuota).where(UserQuota.user_id == user_id)
        )
        quota = result.scalar_one_or_none()
        
        if not quota:
            quota = UserQuota(
                id=uuid.uuid4(),
                user_id=user_id,
                daily_limit=settings.DEFAULT_DAILY_TOKEN_LIMIT,
                monthly_limit=settings.DEFAULT_MONTHLY_TOKEN_LIMIT,
                daily_used=0,
                monthly_used=0,
                cost_used=Decimal("0.00")
            )
            self.db.add(quota)
        
        # 检查是否需要重置
        now = datetime.utcnow()
        if quota.reset_date and quota.reset_date.date() < now.date():
            quota.daily_used = 0
            quota.reset_date = now
        
        quota.daily_used += tokens_used
        quota.monthly_used += tokens_used
        quota.cost_used += cost
        
        await self.db.flush()
        
        return quota
    
    async def check_quota(self, user_id: str, requested_tokens: int) -> tuple[bool, Dict[str, Any]]:
        """检查用户配额是否足够"""
        
        result = await self.db.execute(
            select(UserQuota).where(UserQuota.user_id == user_id)
        )
        quota = result.scalar_one_or_none()
        
        if not quota:
            # 默认允许，会创建默认配额
            return True, {
                "daily_limit": settings.DEFAULT_DAILY_TOKEN_LIMIT,
                "daily_used": 0,
                "monthly_limit": settings.DEFAULT_MONTHLY_TOKEN_LIMIT,
                "monthly_used": 0
            }
        
        # 检查日限额
        daily_remaining = quota.daily_limit - quota.daily_used
        monthly_remaining = quota.monthly_limit - quota.monthly_used
        
        allowed = (requested_tokens <= daily_remaining and 
                  requested_tokens <= monthly_remaining)
        
        return allowed, {
            "daily_limit": quota.daily_limit,
            "daily_used": quota.daily_used,
            "daily_remaining": daily_remaining,
            "monthly_limit": quota.monthly_limit,
            "monthly_used": quota.monthly_used,
            "monthly_remaining": monthly_remaining,
            "cost_budget": quota.cost_budget,
            "cost_used": quota.cost_used
        }
    
    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: str = None,
        department: str = None,
        provider: str = None,
        status: AuditStatus = None,
        start_date: datetime = None,
        end_date: datetime = None,
        risk_level: RiskLevel = None
    ) -> tuple[List[AuditLog], int]:
        """查询审计日志"""
        
        query = select(AuditLog)
        
        # 应用过滤条件
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if department:
            query = query.where(AuditLog.department == department)
        if provider:
            query = query.where(AuditLog.provider == provider)
        if status:
            query = query.where(AuditLog.status == status)
        if start_date:
            query = query.where(AuditLog.request_time >= start_date)
        if end_date:
            query = query.where(AuditLog.request_time <= end_date)
        
        # 风险等级过滤需要关联查询
        if risk_level:
            query = query.join(RiskDetection).where(RiskDetection.risk_level == risk_level)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(desc(AuditLog.request_time)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return logs, total
    
    async def get_audit_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取审计统计"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 总请求数
        total_query = select(func.count(AuditLog.id)).where(AuditLog.request_time >= start_date)
        total_result = await self.db.execute(total_query)
        total_requests = total_result.scalar()
        
        # Token使用统计
        token_query = select(
            func.sum(AuditLog.input_tokens),
            func.sum(AuditLog.output_tokens),
            func.sum(AuditLog.estimated_cost)
        ).where(AuditLog.request_time >= start_date)
        token_result = await self.db.execute(token_query)
        input_tokens, output_tokens, total_cost = token_result.first()
        
        # 状态分布
        status_query = select(
            AuditLog.status,
            func.count(AuditLog.id)
        ).where(AuditLog.request_time >= start_date).group_by(AuditLog.status)
        status_result = await self.db.execute(status_query)
        status_distribution = {row[0]: row[1] for row in status_result.all()}
        
        # 风险事件统计
        risk_query = select(
            RiskDetection.risk_type,
            func.count(RiskDetection.id)
        ).where(RiskDetection.created_at >= start_date).group_by(RiskDetection.risk_type)
        risk_result = await self.db.execute(risk_query)
        risk_distribution = {row[0]: row[1] for row in risk_result.all()}
        
        # 敏感数据类型统计
        sensitive_query = select(
            SensitiveDataHit.data_type,
            func.count(SensitiveDataHit.id)
        ).where(SensitiveDataHit.created_at >= start_date).group_by(SensitiveDataHit.data_type)
        sensitive_result = await self.db.execute(sensitive_query)
        sensitive_distribution = {row[0]: row[1] for row in sensitive_result.all()}
        
        return {
            "total_requests": total_requests or 0,
            "input_tokens": input_tokens or 0,
            "output_tokens": output_tokens or 0,
            "total_cost": float(total_cost) if total_cost else 0,
            "status_distribution": status_distribution,
            "risk_distribution": risk_distribution,
            "sensitive_data_distribution": sensitive_distribution,
            "period_days": days
        }
    
    async def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取每日统计"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            cast(AuditLog.request_time, Date).label("date"),
            func.count(AuditLog.id).label("requests"),
            func.sum(AuditLog.input_tokens).label("input_tokens"),
            func.sum(AuditLog.output_tokens).label("output_tokens"),
            func.sum(AuditLog.estimated_cost).label("cost")
        ).where(
            AuditLog.request_time >= start_date
        ).group_by(
            cast(AuditLog.request_time, Date)
        ).order_by(
            cast(AuditLog.request_time, Date)
        )
        
        result = await self.db.execute(query)
        
        daily_stats = []
        for row in result.all():
            daily_stats.append({
                "date": row.date.isoformat(),
                "requests": row.requests,
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "cost": float(row.cost) if row.cost else 0
            })
        
        return daily_stats
    
    def _calculate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """计算预估成本 (USD)"""
        # 简化的成本计算模型
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        }
        
        # 查找匹配的定价
        model_key = None
        for key in pricing.keys():
            if key in model.lower():
                model_key = key
                break
        
        if not model_key:
            # 默认价格
            model_key = "gpt-3.5-turbo"
        
        cost_per_1k = pricing[model_key]
        input_cost = (input_tokens / 1000) * cost_per_1k["input"]
        output_cost = (output_tokens / 1000) * cost_per_1k["output"]
        
        return Decimal(str(input_cost + output_cost))
    
    def _create_preview(self, content: str, max_length: int = 500) -> str:
        """创建内容预览"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."
    
    def _encrypt_content(self, content: str) -> str:
        """加密内容 (简化实现，实际应使用AES等加密算法)"""
        # 这里使用简单的base64编码作为演示
        # 实际生产环境应使用适当的加密方法
        import base64
        return base64.b64encode(content.encode()).decode()
    
    def _decrypt_content(self, encrypted: str) -> str:
        """解密内容"""
        import base64
        return base64.b64decode(encrypted.encode()).decode()
    
    def _check_data_residency(self, provider: str) -> bool:
        """检查数据驻留合规性"""
        # 简化的合规性检查
        non_compliant_providers = ["openai"]  # 假设OpenAI数据可能出境
        return provider.lower() not in non_compliant_providers
    
    async def _create_hash_chain(self, audit_log: AuditLog):
        """创建哈希链"""
        # 获取上一条记录的哈希
        result = await self.db.execute(
            select(AuditHash).order_by(desc(AuditHash.created_at)).limit(1)
        )
        last_hash = result.scalar_one_or_none()
        previous_hash = last_hash.log_hash if last_hash else None
        
        # 计算当前记录的哈希
        data = f"{audit_log.id}{audit_log.request_id}{audit_log.user_id}{audit_log.request_time.isoformat()}"
        if previous_hash:
            data += previous_hash
        
        log_hash = hashlib.sha256(data.encode()).hexdigest()
        
        # 保存哈希
        audit_hash = AuditHash(
            id=uuid.uuid4(),
            audit_log_id=audit_log.id,
            log_hash=log_hash,
            previous_hash=previous_hash
        )
        self.db.add(audit_hash)
        await self.db.flush()
