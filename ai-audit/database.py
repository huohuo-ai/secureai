"""
SQLite 数据库操作（异步）
"""
import aiosqlite
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

import os
DB_PATH = os.getenv("DB_PATH", "/app/data/audit.db")


async def init_db():
    """初始化数据库"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 审计日志表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                department TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt TEXT,
                prompt_length INTEGER DEFAULT 0,
                response_length INTEGER DEFAULT 0,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                risk_level TEXT DEFAULT 'low',
                risk_reasons TEXT,  -- JSON
                behavior_tags TEXT, -- JSON
                session_id TEXT,
                client_ip TEXT
            )
        """)
        
        # 用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        
        # 插入默认用户 admin/admin
        await db.execute("""
            INSERT OR IGNORE INTO users (username, password_hash)
            VALUES ('admin', 'admin')
        """)
        
        await db.commit()


async def insert_audit_log(log: Dict):
    """插入单条审计日志"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO audit_logs 
            (timestamp, user_id, department, provider, model, prompt, 
             prompt_length, response_length, tokens_input, tokens_output,
             cost_usd, risk_level, risk_reasons, behavior_tags, session_id, client_ip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log['timestamp'],
            log['user_id'],
            log['department'],
            log['provider'],
            log['model'],
            log.get('prompt', ''),
            log.get('prompt_length', 0),
            log.get('response_length', 0),
            log.get('tokens_input', 0),
            log.get('tokens_output', 0),
            log.get('cost_usd', 0),
            log.get('risk_level', 'low'),
            json.dumps(log.get('risk_reasons', [])),
            json.dumps(log.get('behavior_tags', [])),
            log.get('session_id', ''),
            log.get('client_ip', '')
        ))
        await db.commit()


async def insert_audit_logs(logs: List[Dict]):
    """批量插入审计日志"""
    async with aiosqlite.connect(DB_PATH) as db:
        for log in logs:
            await db.execute("""
                INSERT INTO audit_logs 
                (timestamp, user_id, department, provider, model, prompt, 
                 prompt_length, response_length, tokens_input, tokens_output,
                 cost_usd, risk_level, risk_reasons, behavior_tags, session_id, client_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log['timestamp'],
                log['user_id'],
                log['department'],
                log['provider'],
                log['model'],
                log.get('prompt', ''),
                log.get('prompt_length', 0),
                log.get('response_length', 0),
                log.get('tokens_input', 0),
                log.get('tokens_output', 0),
                log.get('cost_usd', 0),
                log.get('risk_level', 'low'),
                json.dumps(log.get('risk_reasons', [])),
                json.dumps(log.get('behavior_tags', [])),
                log.get('session_id', ''),
                log.get('client_ip', '')
            ))
        await db.commit()


async def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    risk_level: Optional[str] = None,
    department: Optional[str] = None,
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict:
    """查询审计日志（带筛选）"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 构建 WHERE 条件
        conditions = ["1=1"]
        params = []
        
        if risk_level:
            conditions.append("risk_level = ?")
            params.append(risk_level)
        if department:
            conditions.append("department = ?")
            params.append(department)
        if user_id:
            conditions.append("user_id LIKE ?")
            params.append(f"%{user_id}%")
        if provider:
            conditions.append("provider = ?")
            params.append(provider)
        if tag:
            conditions.append("behavior_tags LIKE ?")
            params.append(f"%{tag}%")
        if keyword:
            conditions.append("(user_id LIKE ? OR prompt LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        cursor = await db.execute(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}", params)
        total = (await cursor.fetchone())[0]
        
        # 查询数据
        offset = (page - 1) * page_size
        cursor = await db.execute(f"""
            SELECT * FROM audit_logs 
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, params + [page_size, offset])
        
        rows = await cursor.fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item['risk_reasons'] = json.loads(item['risk_reasons'] or '[]')
            item['behavior_tags'] = json.loads(item['behavior_tags'] or '[]')
            items.append(item)
        
        return {
            'total': total,
            'items': items,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }


async def get_dashboard_stats(days: int = 30) -> Dict:
    """获取仪表盘统计数据"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 总统计
        cursor = await db.execute("""
            SELECT 
                COUNT(*) as total_calls,
                SUM(cost_usd) as total_cost,
                COUNT(DISTINCT user_id) as unique_users,
                SUM(tokens_input + tokens_output) as total_tokens
            FROM audit_logs
            WHERE timestamp >= ?
        """, (start_time,))
        row = await cursor.fetchone()
        total_stats = dict(row) if row else {}
        
        # 风险分布
        cursor = await db.execute("""
            SELECT risk_level, COUNT(*) as count
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY risk_level
        """, (start_time,))
        risk_dist = {row['risk_level']: row['count'] for row in await cursor.fetchall()}
        
        # 供应商分布
        cursor = await db.execute("""
            SELECT provider, COUNT(*) as count
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY provider
            ORDER BY count DESC
        """, (start_time,))
        provider_dist = {row['provider']: row['count'] for row in await cursor.fetchall()}
        
        # 部门分布
        cursor = await db.execute("""
            SELECT department, COUNT(*) as count, SUM(cost_usd) as cost
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY department
            ORDER BY count DESC
        """, (start_time,))
        dept_dist = [dict(row) for row in await cursor.fetchall()]
        
        # 时间趋势（按天）
        cursor = await db.execute("""
            SELECT 
                date(timestamp) as day,
                COUNT(*) as calls,
                SUM(cost_usd) as cost
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY day
        """, (start_time,))
        trend = [dict(row) for row in await cursor.fetchall()]
        
        # Top 行为标签
        cursor = await db.execute("""
            SELECT behavior_tags FROM audit_logs
            WHERE timestamp >= ?
        """, (start_time,))
        tag_counts = {}
        for row in await cursor.fetchall():
            tags = json.loads(row['behavior_tags'] or '[]')
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]
        
        return {
            'total_calls': total_stats.get('total_calls', 0),
            'total_cost': round(total_stats.get('total_cost', 0), 2),
            'unique_users': total_stats.get('unique_users', 0),
            'total_tokens': total_stats.get('total_tokens', 0),
            'risk_distribution': risk_dist,
            'provider_distribution': provider_dist,
            'department_distribution': dept_dist,
            'trend': trend,
            'top_behavior_tags': [{'tag': tag, 'count': count} for tag, count in top_tags]
        }


async def get_user_stats(days: int = 30) -> List[Dict]:
    """获取用户统计排行"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = await db.execute("""
            SELECT 
                user_id,
                department,
                COUNT(*) as total_calls,
                SUM(cost_usd) as total_cost,
                AVG(tokens_input + tokens_output) as avg_tokens,
                MAX(risk_level) as max_risk
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY user_id, department
            ORDER BY total_calls DESC
            LIMIT 50
        """, (start_time,))
        
        return [dict(row) for row in await cursor.fetchall()]


async def get_risk_events(limit: int = 10) -> List[Dict]:
    """获取最新风险事件（High/Critical）"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT * FROM audit_logs
            WHERE risk_level IN ('high', 'critical')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = await cursor.fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item['risk_reasons'] = json.loads(item['risk_reasons'] or '[]')
            item['behavior_tags'] = json.loads(item['behavior_tags'] or '[]')
            items.append(item)
        return items


async def verify_user(username: str, password: str) -> bool:
    """验证用户密码"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        )
        row = await cursor.fetchone()
        if row:
            # 简单明文比较（演示用）
            return row[0] == password
        return False
