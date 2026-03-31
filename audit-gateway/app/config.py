from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "AI Audit Gateway"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # ClickHouse 配置
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_DATABASE: str = "ai_audit"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    
    # Redis 配置（用于限流和缓存）
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 审计配置
    AUDIT_BATCH_SIZE: int = 1000  # 批量写入大小
    AUDIT_FLUSH_INTERVAL: int = 5  # 批量写入间隔（秒）
    
    # 敏感词检测
    SENSITIVE_WORDS_FILE: Optional[str] = "sensitive_words.txt"
    ENABLE_SENSITIVE_CHECK: bool = True
    
    # 告警配置
    ALERT_WEBHOOK_URL: Optional[str] = None  # 钉钉/企微 webhook
    ALERT_THRESHOLD_HIGH: int = 10  # 高风险阈值（每小时）
    
    # 安全
    API_SECRET_KEY: str = "your-secret-key-change-this"
    ADMIN_TOKEN: str = "admin-token-change-this"
    
    class Config:
        env_file = ".env"


settings = Settings()
