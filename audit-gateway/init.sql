-- ClickHouse 初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_audit;

-- 主审计日志表
CREATE TABLE IF NOT EXISTS ai_audit.audit_logs (
    request_id String,
    timestamp DateTime64(3),
    received_at DateTime64(3),
    provider LowCardinality(String),
    model LowCardinality(String),
    stream Bool,
    
    user_id String,
    department LowCardinality(String),
    project LowCardinality(String),
    client_ip String,
    user_agent String,
    key_type LowCardinality(String),
    
    method LowCardinality(String),
    path String,
    message_count UInt8,
    total_chars UInt32,
    has_image Bool,
    body_truncated Bool,
    contents String,
    
    edge_node LowCardinality(String),
    edge_start_time UInt64,
    sampling_rate Float32,
    
    risk_level LowCardinality(String),
    sensitive_words Array(String),
    
    INDEX idx_user_id user_id TYPE bloom_filter GRANULARITY 3,
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_department department TYPE bloom_filter GRANULARITY 3
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, user_id, request_id)
TTL timestamp + INTERVAL 1 YEAR
SETTINGS index_granularity = 8192;

-- 敏感词告警表
CREATE TABLE IF NOT EXISTS ai_audit.sensitive_alerts (
    alert_id String,
    request_id String,
    timestamp DateTime64(3),
    user_id String,
    department LowCardinality(String),
    matched_words Array(String),
    content_preview String,
    risk_score UInt8,
    status LowCardinality(String) DEFAULT 'new'
) ENGINE = MergeTree()
ORDER BY (timestamp, risk_score);
