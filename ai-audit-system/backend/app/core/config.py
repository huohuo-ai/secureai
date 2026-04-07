from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Audit System"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_audit"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # AI Provider Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    
    # Encryption
    ENCRYPTION_KEY: str = "your-encryption-key-32-chars-long!"
    
    # Audit Settings
    AUDIT_LOG_RETENTION_DAYS: int = 365
    MAX_INPUT_LENGTH: int = 100000
    MAX_OUTPUT_LENGTH: int = 100000
    
    # Risk Detection
    ENABLE_SENSITIVE_DATA_DETECTION: bool = True
    ENABLE_PROMPT_INJECTION_DETECTION: bool = True
    AUTO_BLOCK_HIGH_RISK: bool = True
    
    # Cost Control
    DEFAULT_DAILY_TOKEN_LIMIT: int = 100000
    DEFAULT_MONTHLY_TOKEN_LIMIT: int = 2000000
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
