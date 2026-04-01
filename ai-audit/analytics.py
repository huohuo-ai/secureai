"""
高级分析模块
提供深度数据分析和洞察
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
import statistics

from database import aiosqlite, DB_PATH


class AnalyticsEngine:
    """分析引擎"""
    
    async def get_usage_patterns(self, days: int = 30) -> Dict:
        """使用模式分析"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            start_time = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 工作日 vs 周末
            cursor = await db.execute("""
                SELECT 
                    CASE WHEN CAST(strftime('%w', timestamp) AS INTEGER) IN (0, 6) 
                        THEN 'weekend' ELSE 'weekday' END as day_type,
                    COUNT(*) as calls,
                    AVG(cost_usd) as avg_cost
                FROM audit_logs
                WHERE timestamp >= ?
                GROUP BY day_type
            """, (start_time,))
            weekday_vs_weekend = {row['day_type']: dict(row) for row in await cursor.fetchall()}
            
            # 时段偏好分析
            cursor = await db.execute("""
                SELECT 
                    CASE 
                        WHEN CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 9 AND 18 THEN 'work_hours'
                        WHEN CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 19 AND 22 THEN 'evening'
                        WHEN CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 23 AND 5 THEN 'night'
                        ELSE 'morning'
                    END as time_slot,
                    COUNT(*) as calls,
                    COUNT(DISTINCT user_id) as users
                FROM audit_logs
                WHERE timestamp >= ?
                GROUP BY time_slot
            """, (start_time,))
            time_slots = {row['time_slot']: dict(row) for row in await cursor.fetchall()}
            
            # 部门使用偏好
            cursor = await db.execute("""
                SELECT 
                    department,
                    provider,
                    COUNT(*) as calls,
                    SUM(cost_usd) as cost
                FROM audit_logs
                WHERE timestamp >= ?
                GROUP BY department, provider
                ORDER BY department, calls DESC
            """, (start_time,))
            dept_preferences = defaultdict(dict)
            for row in await cursor.fetchall():
                dept_preferences[row['department']][row['provider']] = {
                    'calls': row['calls'],
                    'cost': row['cost']
                }
            
            return {
                'weekday_vs_weekend': weekday_vs_weekend,
                'time_slots': time_slots,
                'department_preferences': dict(dept_preferences)
            }
    
    async def get_efficiency_metrics(self) -> Dict:
        """效率指标分析"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Token 利用率
            cursor = await db.execute("""
                SELECT 
                    provider,
                    AVG(tokens_input) as avg_input,
                    AVG(tokens_output) as avg_output,
                    AVG(cost_usd * 1000 / (tokens_input + tokens_output)) as cost_per_1k_tokens
                FROM audit_logs
                GROUP BY provider
            """)
            token_efficiency = [dict(row) for row in await cursor.fetchall()]
            
            # 成本效率最高的用户
            cursor = await db.execute("""
                SELECT 
                    user_id,
                    department,
                    COUNT(*) as calls,
                    SUM(cost_usd) / SUM(tokens_input + tokens_output) * 1000 as efficiency_score
                FROM audit_logs
                GROUP BY user_id, department
                HAVING calls > 10
                ORDER BY efficiency_score ASC
                LIMIT 20
            """)
            efficient_users = [dict(row) for row in await cursor.fetchall()]
            
            return {
                'token_efficiency_by_provider': token_efficiency,
                'most_efficient_users': efficient_users
            }
    
    async def get_anomaly_detection(self, days: int = 7) -> List[Dict]:
        """异常检测"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            start_time = (datetime.now() - timedelta(days=days)).isoformat()
            
            anomalies = []
            
            # 1. 异常高频用户（超过平均值 3 个标准差）
            cursor = await db.execute("""
                WITH user_daily AS (
                    SELECT 
                        user_id,
                        date(timestamp) as day,
                        COUNT(*) as daily_calls
                    FROM audit_logs
                    WHERE timestamp >= ?
                    GROUP BY user_id, day
                ),
                stats AS (
                    SELECT 
                        AVG(daily_calls) as avg_calls,
                        STDDEV(daily_calls) as std_calls
                    FROM user_daily
                )
                SELECT 
                    u.user_id,
                    u.day,
                    u.daily_calls,
                    s.avg_calls,
                    s.std_calls
                FROM user_daily u, stats s
                WHERE u.daily_calls > s.avg_calls + 3 * s.std_calls
                ORDER BY u.daily_calls DESC
                LIMIT 10
            """, (start_time,))
            
            for row in await cursor.fetchall():
                anomalies.append({
                    'type': 'frequency_anomaly',
                    'severity': 'high',
                    'user_id': row['user_id'],
                    'description': f"单日调用 {row['daily_calls']} 次，远超平均值 {row['avg_calls']:.1f}",
                    'timestamp': row['day']
                })
            
            # 2. 异常高消费
            cursor = await db.execute("""
                SELECT 
                    user_id,
                    timestamp,
                    cost_usd,
                    tokens_input + tokens_output as total_tokens
                FROM audit_logs
                WHERE timestamp >= ?
                AND cost_usd > 1.0
                ORDER BY cost_usd DESC
                LIMIT 10
            """, (start_time,))
            
            for row in await cursor.fetchall():
                anomalies.append({
                    'type': 'cost_anomaly',
                    'severity': 'medium',
                    'user_id': row['user_id'],
                    'description': f"单次调用成本 ${row['cost_usd']:.2f}，消耗 {row['total_tokens']} tokens",
                    'timestamp': row['timestamp']
                })
            
            # 3. 深夜异常活动
            cursor = await db.execute("""
                SELECT 
                    user_id,
                    COUNT(*) as night_calls,
                    GROUP_CONCAT(DISTINCT strftime('%H:%M', timestamp)) as times
                FROM audit_logs
                WHERE timestamp >= ?
                AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 0 AND 5
                GROUP BY user_id
                HAVING night_calls > 10
                ORDER BY night_calls DESC
                LIMIT 10
            """, (start_time,))
            
            for row in await cursor.fetchall():
                anomalies.append({
                    'type': 'night_activity',
                    'severity': 'low',
                    'user_id': row['user_id'],
                    'description': f"深夜时段调用 {row['night_calls']} 次",
                    'timestamp': row['times']
                })
            
            return sorted(anomalies, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['severity']], reverse=True)
    
    async def get_predictive_insights(self) -> Dict:
        """预测性洞察"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # 基于历史数据的简单趋势预测
            cursor = await db.execute("""
                SELECT 
                    date(timestamp) as day,
                    COUNT(*) as calls,
                    SUM(cost_usd) as cost
                FROM audit_logs
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY day
                ORDER BY day
            """)
            daily_data = [dict(row) for row in await cursor.fetchall()]
            
            if len(daily_data) >= 7:
                # 计算 7 日移动平均
                recent_calls = [d['calls'] for d in daily_data[-7:]]
                recent_costs = [d['cost'] for d in daily_data[-7:]]
                
                calls_trend = statistics.mean(recent_calls)
                cost_trend = statistics.mean(recent_costs)
                
                # 简单预测（假设趋势延续）
                predicted_monthly_calls = calls_trend * 30
                predicted_monthly_cost = cost_trend * 30
                
                # 计算增长率
                if len(daily_data) >= 14:
                    prev_week_calls = statistics.mean([d['calls'] for d in daily_data[-14:-7]])
                    growth_rate = (calls_trend - prev_week_calls) / prev_week_calls if prev_week_calls > 0 else 0
                else:
                    growth_rate = 0
                
                return {
                    'daily_average_calls': round(calls_trend, 1),
                    'daily_average_cost': round(cost_trend, 2),
                    'predicted_monthly_calls': round(predicted_monthly_calls),
                    'predicted_monthly_cost': round(predicted_monthly_cost, 2),
                    'growth_rate': round(growth_rate * 100, 1),
                    'trend': 'up' if growth_rate > 0.05 else 'down' if growth_rate < -0.05 else 'stable'
                }
            
            return {}
    
    async def get_session_analysis(self, limit: int = 100) -> List[Dict]:
        """会话分析"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute("""
                SELECT 
                    session_id,
                    user_id,
                    COUNT(*) as messages,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    SUM(cost_usd) as total_cost,
                    GROUP_CONCAT(DISTINCT model) as models_used
                FROM audit_logs
                WHERE session_id IS NOT NULL
                GROUP BY session_id, user_id
                HAVING messages > 1
                ORDER BY messages DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for row in await cursor.fetchall():
                start = datetime.fromisoformat(row['start_time'])
                end = datetime.fromisoformat(row['end_time'])
                duration = (end - start).total_seconds() / 60  # 分钟
                
                sessions.append({
                    'session_id': row['session_id'],
                    'user_id': row['user_id'],
                    'messages': row['messages'],
                    'duration_minutes': round(duration, 1),
                    'total_cost': row['total_cost'],
                    'models_used': row['models_used'].split(',') if row['models_used'] else []
                })
            
            return sessions


# 全局分析引擎实例
analytics = AnalyticsEngine()
