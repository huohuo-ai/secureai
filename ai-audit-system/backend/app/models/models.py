import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Enum, ForeignKey, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base


class AuditStatus(str, PyEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


class RiskType(str, PyEnum):
    SENSITIVE_DATA = "sensitive_data"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_EXFILTRATION = "data_exfiltration"
    POLICY_VIOLATION = "policy_violation"
    ANOMALY = "anomaly"
    COST_SPIKE = "cost_spike"


class RiskLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionTaken(str, PyEnum):
    LOG = "log"
    WARN = "warn"
    BLOCK = "block"
    MASK = "mask"
    NOTIFY = "notify"


class SensitiveDataType(str, PyEnum):
    ID_CARD = "id_card"
    PHONE = "phone"
    BANK_CARD = "bank_card"
    EMAIL = "email"
    IP_ADDRESS = "ip_address"
    SOURCE_CODE = "source_code"
    API_KEY = "api_key"
    PASSWORD = "password"
    BUSINESS_SECRET = "business_secret"
    PERSONAL_INFO = "personal_info"


class DetectionMethod(str, PyEnum):
    REGEX = "regex"
    ML = "ml"
    KEYWORD = "keyword"
    PATTERN = "pattern"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    department = Column(String(64), nullable=True, index=True)
    project = Column(String(128), nullable=True, index=True)
    provider = Column(String(32), nullable=False, index=True)
    model = Column(String(64), nullable=False, index=True)
    
    request_time = Column(DateTime, nullable=False, index=True)
    response_time = Column(DateTime, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status = Column(Enum(AuditStatus), nullable=False, index=True)
    
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Numeric(12, 6), default=0)
    
    input_preview = Column(Text, nullable=True)
    output_preview = Column(Text, nullable=True)
    full_input = Column(Text, nullable=True)  # 加密存储
    full_output = Column(Text, nullable=True)  # 加密存储
    
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    session_id = Column(String(128), nullable=True)
    
    # 合规相关
    data_residency_compliant = Column(Boolean, default=True)
    gdpr_compliant = Column(Boolean, default=True)
    
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    risk_detections = relationship("RiskDetection", back_populates="audit_log", cascade="all, delete-orphan")
    sensitive_data_hits = relationship("SensitiveDataHit", back_populates="audit_log", cascade="all, delete-orphan")


class RiskDetection(Base):
    __tablename__ = "risk_detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=False)
    risk_type = Column(Enum(RiskType), nullable=False, index=True)
    risk_level = Column(Enum(RiskLevel), nullable=False, index=True)
    detection_rule = Column(String(128), nullable=False)
    detected_content = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    action_taken = Column(Enum(ActionTaken), default=ActionTaken.LOG)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    audit_log = relationship("AuditLog", back_populates="risk_detections")


class SensitiveDataHit(Base):
    __tablename__ = "sensitive_data_hits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=False)
    data_type = Column(Enum(SensitiveDataType), nullable=False, index=True)
    detection_method = Column(Enum(DetectionMethod), nullable=False)
    matched_pattern = Column(String(256), nullable=True)
    masked_content = Column(Text, nullable=True)
    position = Column(String(16), nullable=False)  # input/output
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    audit_log = relationship("AuditLog", back_populates="sensitive_data_hits")


class UserQuota(Base):
    __tablename__ = "user_quotas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), unique=True, nullable=False, index=True)
    department = Column(String(64), nullable=True, index=True)
    
    # Token限制
    daily_limit = Column(Integer, default=100000)
    monthly_limit = Column(Integer, default=2000000)
    daily_used = Column(Integer, default=0)
    monthly_used = Column(Integer, default=0)
    
    # 成本预算
    cost_budget = Column(Numeric(12, 2), default=1000.00)
    cost_used = Column(Numeric(12, 2), default=0.00)
    
    reset_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), unique=True, nullable=False)
    rule_type = Column(String(32), nullable=False, index=True)
    description = Column(Text, nullable=True)
    conditions = Column(JSON, default=dict)
    action = Column(String(16), default="allow")  # allow/block/mask/notify
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemConfig(Base):
    __tablename__ = "system_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(128), unique=True, nullable=False)
    config_value = Column(JSON, default=dict)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditHash(Base):
    """审计日志哈希链，用于防篡改验证"""
    __tablename__ = "audit_hashes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), unique=True, nullable=False)
    log_hash = Column(String(128), nullable=False)
    previous_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
