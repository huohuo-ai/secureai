#!/usr/bin/env python3
"""
AI 审计平台 - 增强版
FastAPI + SQLite + Session 登录 + 实时数据
"""
import os
import json
import webbrowser
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import asyncio

from database import (
    init_db, get_audit_logs, get_dashboard_stats, get_user_stats, 
    get_risk_events, verify_user, aiosqlite, DB_PATH
)
from risk_detector import get_risk_color, get_risk_label
from behavior_tagger import get_tag_color

app = FastAPI(title="AI 审计平台 - 增强版")

# Session 配置
app.add_middleware(
    SessionMiddleware,
    secret_key="ai-audit-enhanced-secret-key-2024",
    max_age=3600 * 24
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 静态文件
static_dir = os.path.join(os.path.dirname(__file__), 'static')
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


def get_current_user(request: Request):
    """获取当前用户"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    if request.session.get("user"):
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页面"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 审计平台 - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-box {
            background: white;
            padding: 50px;
            border-radius: 20px;
            box-shadow: 0 25px 80px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 420px;
            animation: slideUp 0.6s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .login-box h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 32px;
            font-weight: 700;
        }
        .login-box .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 15px;
        }
        .form-group {
            margin-bottom: 24px;
        }
        .form-group label {
            display: block;
            margin-bottom: 10px;
            color: #333;
            font-size: 14px;
            font-weight: 600;
        }
        .form-group input {
            width: 100%;
            padding: 14px 18px;
            border: 2px solid #e8e8e8;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }
        .login-btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 17px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .demo-info {
            margin-top: 30px;
            padding: 16px;
            background: linear-gradient(135deg, #f6ffed 0%, #e6f7ff 100%);
            border-radius: 10px;
            font-size: 14px;
            color: #52c41a;
            text-align: center;
            border: 1px solid #b7eb8f;
        }
        .features {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 30px;
            font-size: 13px;
            color: #999;
        }
        .features span {
            display: flex;
            align-items: center;
            gap: 5px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🛡️ AI 审计平台</h1>
        <p class="subtitle">企业级 AI 模型调用审计与风险分析</p>
        
        <form method="POST" action="/api/login">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" value="admin" placeholder="请输入用户名" required>
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" value="admin" placeholder="请输入密码" required>
            </div>
            <button type="submit" class="login-btn">登 录</button>
        </form>
        
        <div class="demo-info">
            💡 演示账号：admin / admin
        </div>
        
        <div class="features">
            <span>🔒 安全审计</span>
            <span>📊 数据分析</span>
            <span>⚡ 实时监控</span>
        </div>
    </div>
</body>
</html>
    """


@app.get("/dashboard", response_class=FileResponse)
async def dashboard_page(request: Request):
    """管理后台"""
    if not request.session.get("user"):
        return RedirectResponse("/login")
    return FileResponse(os.path.join(static_dir, "index.html"))


# ==================== API 路由 ====================

@app.post("/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """登录"""
    if await verify_user(username, password):
        request.session["user"] = username
        return RedirectResponse("/dashboard", status_code=302)
    return HTMLResponse("""
        <script>alert('用户名或密码错误'); window.location='/login';</script>
    """, status_code=401)


@app.get("/api/logout")
async def logout(request: Request):
    """登出"""
    request.session.clear()
    return RedirectResponse("/login")


# 仪表盘 API
@app.get("/api/stats/dashboard")
async def api_dashboard_stats(
    user: str = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    """仪表盘统计数据"""
    return await get_dashboard_stats(days)


@app.get("/api/stats/trend")
async def api_trend(
    user: str = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", regex="^(hour|day|week)$")
):
    """趋势数据（支持小时/天/周聚合）"""
    from database import ch_client
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        if group_by == "hour":
            sql = """
                SELECT 
                    strftime('%Y-%m-%d %H:00', timestamp) as period,
                    COUNT(*) as calls,
                    SUM(cost_usd) as cost,
                    COUNT(DISTINCT user_id) as users
                FROM audit_logs
                WHERE timestamp >= ?
                GROUP BY period
                ORDER BY period
            """
        elif group_by == "week":
            sql = """
                SELECT 
                    strftime('%Y-W%W', timestamp) as period,
                    COUNT(*) as calls,
                    SUM(cost_usd) as cost,
                    COUNT(DISTINCT user_id) as users
                FROM audit_logs
                WHERE timestamp >= ?
                GROUP BY period
                ORDER BY period
            """
        else:  # day
            sql = """
                SELECT 
                    date(timestamp) as period,
                    COUNT(*) as calls,
                    SUM(cost_usd) as cost,
                    COUNT(DISTINCT user_id) as users
                FROM audit_logs
                WHERE timestamp >= ?
                GROUP BY period
                ORDER BY period
            """
        
        cursor = await db.execute(sql, (start_time,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@app.get("/api/stats/hourly-distribution")
async def api_hourly_distribution(user: str = Depends(get_current_user)):
    """24小时分布"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                COUNT(*) as count,
                AVG(cost_usd) as avg_cost
            FROM audit_logs
            GROUP BY hour
            ORDER BY hour
        """)
        return [dict(row) for row in await cursor.fetchall()]


@app.get("/api/stats/model-usage")
async def api_model_usage(
    user: str = Depends(get_current_user),
    days: int = Query(30, ge=1)
):
    """模型使用统计"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = await db.execute("""
            SELECT 
                model,
                provider,
                COUNT(*) as calls,
                SUM(cost_usd) as total_cost,
                AVG(tokens_input + tokens_output) as avg_tokens
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY model, provider
            ORDER BY calls DESC
        """, (start_time,))
        return [dict(row) for row in await cursor.fetchall()]


@app.get("/api/stats/cost-analysis")
async def api_cost_analysis(user: str = Depends(get_current_user)):
    """成本分析"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 按部门统计
        cursor = await db.execute("""
            SELECT 
                department,
                SUM(cost_usd) as total_cost,
                COUNT(*) as calls,
                SUM(cost_usd) / COUNT(*) as avg_cost_per_call
            FROM audit_logs
            GROUP BY department
            ORDER BY total_cost DESC
        """)
        by_department = [dict(row) for row in await cursor.fetchall()]
        
        # 按用户统计（Top 20）
        cursor = await db.execute("""
            SELECT 
                user_id,
                department,
                SUM(cost_usd) as total_cost,
                COUNT(*) as calls
            FROM audit_logs
            GROUP BY user_id, department
            ORDER BY total_cost DESC
            LIMIT 20
        """)
        by_user = [dict(row) for row in await cursor.fetchall()]
        
        # 成本趋势（最近 30 天）
        start_time = (datetime.now() - timedelta(days=30)).isoformat()
        cursor = await db.execute("""
            SELECT 
                date(timestamp) as day,
                SUM(cost_usd) as daily_cost
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY day
            ORDER BY day
        """, (start_time,))
        trend = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "by_department": by_department,
            "by_user": by_user,
            "trend": trend
        }


# 用户分析 API
@app.get("/api/stats/users")
async def api_user_stats(
    user: str = Depends(get_current_user),
    days: int = Query(30, ge=1),
    sort_by: str = Query("calls", regex="^(calls|cost|risk)$")
):
    """用户统计排行"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        order_field = {
            "calls": "total_calls",
            "cost": "total_cost",
            "risk": "risk_score"
        }.get(sort_by, "total_calls")
        
        cursor = await db.execute(f"""
            SELECT 
                user_id,
                department,
                COUNT(*) as total_calls,
                SUM(cost_usd) as total_cost,
                AVG(tokens_input + tokens_output) as avg_tokens,
                MAX(CASE risk_level 
                    WHEN 'critical' THEN 4 
                    WHEN 'high' THEN 3 
                    WHEN 'medium' THEN 2 
                    ELSE 1 
                END) as risk_score,
                COUNT(DISTINCT model) as models_used
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY user_id, department
            ORDER BY {order_field} DESC
            LIMIT 100
        """, (start_time,))
        return [dict(row) for row in await cursor.fetchall()]


@app.get("/api/stats/user/{user_id}/detail")
async def api_user_detail(user_id: str, user: str = Depends(get_current_user)):
    """用户详情"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 基本信息
        cursor = await db.execute("""
            SELECT 
                user_id,
                department,
                COUNT(*) as total_calls,
                SUM(cost_usd) as total_cost,
                MIN(timestamp) as first_call,
                MAX(timestamp) as last_call
            FROM audit_logs
            WHERE user_id = ?
            GROUP BY user_id, department
        """, (user_id,))
        basic = dict(await cursor.fetchone() or {})
        
        # 使用偏好
        cursor = await db.execute("""
            SELECT 
                provider,
                model,
                COUNT(*) as calls
            FROM audit_logs
            WHERE user_id = ?
            GROUP BY provider, model
            ORDER BY calls DESC
        """, (user_id,))
        preferences = [dict(row) for row in await cursor.fetchall()]
        
        # 风险记录
        cursor = await db.execute("""
            SELECT * FROM audit_logs
            WHERE user_id = ? AND risk_level IN ('high', 'critical')
            ORDER BY timestamp DESC
            LIMIT 20
        """, (user_id,))
        risk_records = [dict(row) for row in await cursor.fetchall()]
        
        # 行为标签统计
        cursor = await db.execute("""
            SELECT behavior_tags FROM audit_logs WHERE user_id = ?
        """, (user_id,))
        tag_counts = {}
        for row in await cursor.fetchall():
            tags = json.loads(row['behavior_tags'] or '[]')
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "basic": basic,
            "preferences": preferences,
            "risk_records": risk_records,
            "behavior_tags": sorted(tag_counts.items(), key=lambda x: -x[1])
        }


# 审计日志 API
@app.get("/api/audit/logs")
async def api_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = None,
    department: Optional[str] = None,
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    sort_by: str = Query("timestamp", regex="^(timestamp|cost|risk)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: str = Depends(get_current_user)
):
    """审计日志查询"""
    return await get_audit_logs(
        page=page, page_size=page_size,
        risk_level=risk_level, department=department,
        user_id=user_id, provider=provider, tag=tag, keyword=keyword,
        start_time=start_time, end_time=end_time
    )


@app.get("/api/audit/export")
async def api_export_logs(
    format: str = Query("csv", regex="^(csv|json)$"),
    days: int = Query(30, ge=1),
    user: str = Depends(get_current_user)
):
    """导出审计日志"""
    from database import DB_PATH
    import csv
    import io
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = await db.execute("""
            SELECT * FROM audit_logs
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (start_time,))
        rows = await cursor.fetchall()
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['timestamp', 'user_id', 'department', 'provider', 'model', 
                           'risk_level', 'cost_usd', 'tokens_input', 'tokens_output'])
            for row in rows:
                writer.writerow([
                    row['timestamp'], row['user_id'], row['department'],
                    row['provider'], row['model'], row['risk_level'],
                    row['cost_usd'], row['tokens_input'], row['tokens_output']
                ])
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
        else:
            data = [dict(row) for row in rows]
            return StreamingResponse(
                io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d')}.json"}
            )


# 风险分析 API
@app.get("/api/stats/risk-events")
async def api_risk_events(
    user: str = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    level: Optional[str] = None
):
    """风险事件列表"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if level:
            cursor = await db.execute("""
                SELECT * FROM audit_logs
                WHERE risk_level = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (level, limit))
        else:
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


@app.get("/api/stats/risk-summary")
async def api_risk_summary(user: str = Depends(get_current_user)):
    """风险汇总统计"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 按风险等级统计
        cursor = await db.execute("""
            SELECT 
                risk_level,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as users,
                SUM(cost_usd) as total_cost
            FROM audit_logs
            GROUP BY risk_level
        """)
        by_level = [dict(row) for row in await cursor.fetchall()]
        
        # 按部门统计风险
        cursor = await db.execute("""
            SELECT 
                department,
                SUM(CASE WHEN risk_level IN ('high', 'critical') THEN 1 ELSE 0 END) as risk_count,
                COUNT(*) as total
            FROM audit_logs
            GROUP BY department
            ORDER BY risk_count DESC
        """)
        by_dept = [dict(row) for row in await cursor.fetchall()]
        
        # 按原因统计
        cursor = await db.execute("SELECT risk_reasons FROM audit_logs")
        reason_counts = {}
        for row in await cursor.fetchall():
            reasons = json.loads(row[0] or '[]')
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            "by_level": by_level,
            "by_department": by_dept,
            "top_reasons": sorted(reason_counts.items(), key=lambda x: -x[1])[:10]
        }


# 高级分析 API
@app.get("/api/analytics/usage-patterns")
async def api_usage_patterns(user: str = Depends(get_current_user), days: int = 30):
    """使用模式分析"""
    from analytics import analytics
    return await analytics.get_usage_patterns(days)


@app.get("/api/analytics/efficiency")
async def api_efficiency(user: str = Depends(get_current_user)):
    """效率指标分析"""
    from analytics import analytics
    return await analytics.get_efficiency_metrics()


@app.get("/api/analytics/anomalies")
async def api_anomalies(user: str = Depends(get_current_user), days: int = 7):
    """异常检测"""
    from analytics import analytics
    return await analytics.get_anomaly_detection(days)


@app.get("/api/analytics/predictions")
async def api_predictions(user: str = Depends(get_current_user)):
    """预测性洞察"""
    from analytics import analytics
    return await analytics.get_predictive_insights()


@app.get("/api/analytics/sessions")
async def api_sessions(user: str = Depends(get_current_user), limit: int = 100):
    """会话分析"""
    from analytics import analytics
    return await analytics.get_session_analysis(limit)


# 实时监控 WebSocket
@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """WebSocket 实时数据推送"""
    await manager.connect(websocket)
    try:
        while True:
            # 每 5 秒推送一次统计数据
            await asyncio.sleep(5)
            
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("""
                    SELECT 
                        COUNT(*) as total_24h,
                        SUM(cost_usd) as cost_24h,
                        COUNT(CASE WHEN risk_level IN ('high', 'critical') THEN 1 END) as risk_count
                    FROM audit_logs
                    WHERE timestamp >= datetime('now', '-1 day')
                """)
                row = await cursor.fetchone()
                
                await websocket.send_json({
                    "type": "stats",
                    "data": {
                        "calls_24h": row[0],
                        "cost_24h": round(row[1], 2),
                        "risk_24h": row[2]
                    }
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# 配置 API
@app.get("/api/config")
async def api_config(user: str = Depends(get_current_user)):
    """前端配置"""
    return {
        "risk_levels": {
            "low": {"label": "低风险", "color": "#52c41a", "bg": "#f6ffed"},
            "medium": {"label": "中风险", "color": "#faad14", "bg": "#fffbe6"},
            "high": {"label": "高风险", "color": "#fa8c16", "bg": "#fff7e6"},
            "critical": {"label": "严重", "color": "#f5222d", "bg": "#fff1f0"}
        },
        "behavior_tags": {
            "高频用户": "#722ed1",
            "异常消耗": "#f5222d",
            "测试行为": "#13c2c2",
            "批量操作": "#eb2f96",
            "深夜使用": "#1890ff",
            "敏感操作": "#cf1322",
            "模型对比": "#fa8c16",
            "长对话": "#52c41a",
            "首次使用": "#8c8c8c",
            "成本敏感": "#ffa940"
        },
        "providers": {
            "openai": {"name": "OpenAI", "color": "#10a37f"},
            "claude": {"name": "Claude", "color": "#cc785c"},
            "qwen": {"name": "通义千问", "color": "#1677ff"},
            "baidu": {"name": "文心一言", "color": "#2932e1"},
            "azure": {"name": "Azure", "color": "#0078d4"}
        }
    }


# 健康检查
@app.get("/health")
async def health():
    return {"status": "healthy", "time": datetime.now().isoformat()}


# 启动
def startup():
    """启动时初始化"""
    print("🚀 AI 审计平台启动中...")


if __name__ == "__main__":
    import uvicorn
    
    # 确保数据目录存在
    data_dir = "/app/data" if os.getenv("DOCKER_ENV") else "data"
    os.makedirs(data_dir, exist_ok=True)
    
    print("\n" + "=" * 60)
    print("🚀 AI 审计平台 - 超级增强版")
    print("=" * 60)
    
    # 初始化数据库
    print("\n📦 初始化数据库...")
    asyncio.run(init_db())
    
    # 自动生成演示数据（如果为空）
    async def check_and_generate():
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM audit_logs")
            count = (await cursor.fetchone())[0]
            if count == 0:
                print("\n📝 数据库为空，正在生成超级演示数据...")
                print("   ├─ 时间跨度: 90 天")
                print("   ├─ 记录数量: 150,000 条")
                print("   ├─ 用户数量: 60+ 虚拟用户")
                print("   ├─ 部门覆盖: 8 个部门")
                print("   ├─ 供应商: 5 家 (OpenAI/Claude/文心/通义/Azure)")
                print("   ├─ 场景类型: 14 种真实业务场景")
                print("   ├─ 行为标签: 10 种自动识别标签")
                print("   └─ 预计时间: 5-10 分钟")
                print("\n⏳ 开始生成，请耐心等待...\n")
                from super_generate_data import generate_super_data
                await generate_super_data(days=90, total_records=150000)
            else:
                print(f"\n✅ 数据库已有 {count:,} 条记录，跳过生成")
                print(f"   如需重新生成，请删除 {data_dir}/audit.db 后重启\n")
    
    asyncio.run(check_and_generate())
    
    print("\n" + "=" * 60)
    print("🎉 系统启动成功！")
    print("=" * 60)
    print("\n📱 访问地址:")
    print("   ├─ http://localhost:8000")
    print("   └─ http://127.0.0.1:8000")
    print("\n🔑 登录信息:")
    print("   ├─ 用户名: admin")
    print("   └─ 密码: admin")
    print("\n📊 功能模块:")
    print("   ├─ 📈 仪表盘 - 全局数据概览")
    print("   ├─ 📝 审计日志 - 详细调用记录")
    print("   ├─ 👥 用户分析 - 用户行为画像")
    print("   ├─ ⚠️  风险分析 - 风险事件追踪")
    print("   ├─ 💰 成本分析 - 费用统计预测")
    print("   ├─ 📡 实时监控 - WebSocket 实时数据")
    print("   └─ 🔍 高级分析 - 模式识别/异常检测")
    print("\n📦 数据规模:")
    print("   ├─ 150,000+ 条调用记录")
    print("   ├─ 60+ 虚拟用户")
    print("   └─ 90 天时间跨度")
    print("=" * 60 + "\n")
    
    # 非容器环境自动打开浏览器
    if not os.getenv("DOCKER_ENV"):
        webbrowser.open("http://localhost:8000")
    
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
