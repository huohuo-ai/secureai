from clickhouse_driver import Client
from redis import Redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ClickHouseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = Client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                database=settings.CLICKHOUSE_DATABASE,
                user=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                settings={
                    'max_execution_time': 30,
                    'max_block_size': 100000
                }
            )
            cls._instance.init_tables()
        return cls._instance
    
    def init_tables(self):
        """初始化审计表"""
        # 主审计日志表
        self.client.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
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
        SETTINGS index_granularity = 8192
        ''')
        
        # 敏感词告警表
        self.client.execute('''
        CREATE TABLE IF NOT EXISTS sensitive_alerts (
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
        ORDER BY (timestamp, risk_score)
        ''')
        
        logger.info("ClickHouse tables initialized")
    
    def insert_audit_logs(self, logs: list):
        """批量插入审计日志"""
        if not logs:
            return
            
        data = []
        for log in logs:
            data.append((
                log['request_id'],
                log['timestamp'],
                log.get('received_at'),
                log['provider'],
                log['model'],
                log.get('stream', False),
                log['user']['user_id'],
                log['user'].get('department', 'unknown'),
                log['user'].get('project', 'default'),
                log['user']['client_ip'],
                log['user'].get('user_agent', ''),
                log['user'].get('key_type', 'unknown'),
                log['request']['method'],
                log['request']['path'],
                log['request']['content_summary']['message_count'],
                log['request']['content_summary']['total_chars'],
                log['request']['content_summary'].get('has_image', False),
                log['request']['content_summary'].get('body_truncated', False),
                str(log['request'].get('contents', [])),
                log['edge']['node'],
                log['edge']['start_time'],
                log['edge'].get('sampling', 1.0),
                log.get('risk_level', 'low'),
                log.get('sensitive_words', [])
            ))
        
        self.client.execute(
            'INSERT INTO audit_logs VALUES',
            data
        )
    
    def query_audit_logs(self, query_params: dict, limit: int = 100, offset: int = 0):
        """查询审计日志"""
        conditions = ["1=1"]
        params = {}
        
        if query_params.get('start_time'):
            conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = query_params['start_time']
        
        if query_params.get('end_time'):
            conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = query_params['end_time']
        
        if query_params.get('user_id'):
            conditions.append("user_id = %(user_id)s")
            params['user_id'] = query_params['user_id']
        
        if query_params.get('department'):
            conditions.append("department = %(department)s")
            params['department'] = query_params['department']
        
        if query_params.get('provider'):
            conditions.append("provider = %(provider)s")
            params['provider'] = query_params['provider']
        
        if query_params.get('risk_level'):
            conditions.append("risk_level = %(risk_level)s")
            params['risk_level'] = query_params['risk_level']
        
        if query_params.get('keyword'):
            conditions.append("contents ILIKE %(keyword)s")
            params['keyword'] = f"%{query_params['keyword']}%"
        
        where_clause = " AND ".join(conditions)
        
        # 先查询总数
        count_sql = f"SELECT count() FROM audit_logs WHERE {where_clause}"
        total = self.client.execute(count_sql, params)[0][0]
        
        # 查询数据
        sql = f'''
        SELECT 
            request_id, timestamp, provider, model,
            user_id, department, client_ip,
            message_count, total_chars, risk_level,
            contents
        FROM audit_logs
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT {limit} OFFSET {offset}
        '''
        
        rows = self.client.execute(sql, params)
        
        results = []
        for row in rows:
            results.append({
                'request_id': row[0],
                'timestamp': row[1],
                'provider': row[2],
                'model': row[3],
                'user_id': row[4],
                'department': row[5],
                'client_ip': row[6],
                'message_count': row[7],
                'total_chars': row[8],
                'risk_level': row[9],
                'contents_preview': str(row[10])[:500] if row[10] else ''
            })
        
        return {'total': total, 'items': results, 'limit': limit, 'offset': offset}


# Redis 客户端
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# ClickHouse 客户端
ch_client = ClickHouseClient()
