from fastapi import APIRouter, Query, Depends, Header
from datetime import datetime, timedelta
from typing import Optional
from app.database import ch_client, redis_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_admin_token(x_admin_token: str = Header(None)):
    """验证管理员 Token - 演示模式：允许空 Token"""
    if settings.ADMIN_TOKEN and settings.ADMIN_TOKEN != "your-secure-admin-token-change-this":
        if x_admin_token != settings.ADMIN_TOKEN:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Invalid admin token")
    return True


@router.get("/api/v1/stats/dashboard", dependencies=[Depends(verify_admin_token)])
async def get_dashboard_stats(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """获取仪表盘统计数据"""
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    # 使用 ClickHouse 聚合查询
    client = ch_client.client
    
    # 基础统计
    basic_sql = '''
    SELECT 
        count() as total_requests,
        uniqExact(user_id) as unique_users,
        uniqExact(department) as unique_depts,
        sum(total_chars) as total_input_chars,
        sumIf(total_chars, provider = 'openai') as openai_chars,
        sumIf(total_chars, provider = 'claude') as claude_chars
    FROM audit_logs
    WHERE timestamp >= %(start)s AND timestamp <= %(end)s
    '''
    
    basic = client.execute(basic_sql, {
        'start': start_time,
        'end': end_time
    })[0]
    
    # 按供应商统计
    provider_sql = '''
    SELECT provider, count() as cnt
    FROM audit_logs
    WHERE timestamp >= %(start)s AND timestamp <= %(end)s
    GROUP BY provider
    ORDER BY cnt DESC
    '''
    provider_stats = {row[0]: row[1] for row in client.execute(provider_sql, {
        'start': start_time,
        'end': end_time
    })}
    
    # 按部门统计
    dept_sql = '''
    SELECT department, count() as cnt, uniqExact(user_id) as users
    FROM audit_logs
    WHERE timestamp >= %(start)s AND timestamp <= %(end)s
    GROUP BY department
    ORDER BY cnt DESC
    LIMIT 20
    '''
    dept_stats = [
        {'department': row[0], 'requests': row[1], 'users': row[2]}
        for row in client.execute(dept_sql, {'start': start_time, 'end': end_time})
    ]
    
    # 按模型统计
    model_sql = '''
    SELECT model, count() as cnt
    FROM audit_logs
    WHERE timestamp >= %(start)s AND timestamp <= %(end)s
    GROUP BY model
    ORDER BY cnt DESC
    LIMIT 20
    '''
    model_stats = {row[0]: row[1] for row in client.execute(model_sql, {
        'start': start_time,
        'end': end_time
    })}
    
    # 时间序列（按小时）
    time_sql = '''
    SELECT 
        toStartOfHour(timestamp) as hour,
        count() as cnt,
        uniqExact(user_id) as users
    FROM audit_logs
    WHERE timestamp >= %(start)s AND timestamp <= %(end)s
    GROUP BY hour
    ORDER BY hour
    '''
    time_series = [
        {'hour': row[0].isoformat(), 'requests': row[1], 'users': row[2]}
        for row in client.execute(time_sql, {'start': start_time, 'end': end_time})
    ]
    
    # 估算成本
    total_chars = basic[3] or 0
    estimated_tokens = total_chars / 4
    cost_estimate = (estimated_tokens / 1000000) * 20
    
    # 处理 None 值（当没有数据时）
    def safe_int(val):
        return int(val) if val is not None else 0
    
    def safe_float(val):
        return float(val) if val is not None else 0.0
    
    return {
        "period": {
            "start": start_time.isoformat() if start_time else None,
            "end": end_time.isoformat() if end_time else None
        },
        "summary": {
            "total_requests": safe_int(basic[0]),
            "unique_users": safe_int(basic[1]),
            "unique_departments": safe_int(basic[2]),
            "total_input_chars": safe_int(basic[3]),
            "estimated_tokens": int(estimated_tokens),
            "estimated_cost_usd": round(cost_estimate, 2)
        },
        "by_provider": provider_stats,
        "by_model": model_stats,
        "by_department": dept_stats,
        "time_series": time_series
    }


@router.get("/api/v1/stats/users/top", dependencies=[Depends(verify_admin_token)])
async def get_top_users(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """获取活跃用户排行"""
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    sql = '''
    SELECT 
        user_id,
        department,
        count() as request_count,
        sum(total_chars) as total_chars,
        uniqExact(model) as models_used
    FROM audit_logs
    WHERE timestamp >= %(start)s AND timestamp <= %(end)s
    GROUP BY user_id, department
    ORDER BY request_count DESC
    LIMIT %(limit)s
    '''
    
    rows = ch_client.client.execute(sql, {
        'start': start_time,
        'end': end_time,
        'limit': limit
    })
    
    return {
        "users": [
            {
                "user_id": row[0],
                "department": row[1],
                "requests": row[2],
                "input_chars": row[3],
                "models_used": row[4]
            }
            for row in rows
        ]
    }
