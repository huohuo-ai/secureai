"""
AI 使用审计平台 - MVP
FastAPI + SQLite + Session 登录
"""
import os
import webbrowser
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
from typing import Optional

from database import init_db, get_audit_logs, get_dashboard_stats, get_user_stats, get_risk_events, verify_user
from risk_detector import get_risk_color, get_risk_label
from behavior_tagger import get_tag_color

app = FastAPI(title="AI 审计平台")

# Session 配置
app.add_middleware(
    SessionMiddleware,
    secret_key="ai-audit-demo-secret-key-2024",
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
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 400px;
        }
        .login-box h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .login-box .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-size: 14px;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #d9d9d9;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .login-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .demo-info {
            margin-top: 20px;
            padding: 12px;
            background: #f6ffed;
            border: 1px solid #b7eb8f;
            border-radius: 6px;
            font-size: 13px;
            color: #52c41a;
            text-align: center;
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
                <input type="text" name="username" value="admin" required>
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" value="admin" required>
            </div>
            <button type="submit" class="login-btn">登 录</button>
        </form>
        
        <div class="demo-info">
            💡 演示账号：admin / admin
        </div>
    </div>
</body>
</html>
    """


@app.get("/dashboard", response_class=FileResponse)
async def dashboard_page(request: Request):
    """仪表盘页面"""
    if not request.session.get("user"):
        return RedirectResponse("/login")
    return FileResponse(os.path.join(static_dir, "index.html"))


# ==================== API 路由 ====================

@app.post("/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """登录接口"""
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


@app.get("/api/stats/dashboard")
async def api_dashboard_stats(user: str = Depends(get_current_user), days: int = 30):
    """仪表盘统计数据"""
    return await get_dashboard_stats(days)


@app.get("/api/stats/users")
async def api_user_stats(user: str = Depends(get_current_user), days: int = 30):
    """用户统计"""
    return await get_user_stats(days)


@app.get("/api/stats/risk-events")
async def api_risk_events(user: str = Depends(get_current_user), limit: int = 10):
    """最新风险事件"""
    return await get_risk_events(limit)


@app.get("/api/audit/logs")
async def api_audit_logs(
    page: int = 1,
    page_size: int = 20,
    risk_level: Optional[str] = None,
    department: Optional[str] = None,
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    user: str = Depends(get_current_user)
):
    """审计日志查询"""
    return await get_audit_logs(
        page=page,
        page_size=page_size,
        risk_level=risk_level,
        department=department,
        user_id=user_id,
        provider=provider,
        tag=tag,
        keyword=keyword
    )


@app.get("/api/config")
async def api_config(user: str = Depends(get_current_user)):
    """前端配置（风险等级颜色等）"""
    return {
        "risk_levels": {
            "low": {"label": "低风险", "color": "#52c41a"},
            "medium": {"label": "中风险", "color": "#faad14"},
            "high": {"label": "高风险", "color": "#fa8c16"},
            "critical": {"label": "严重", "color": "#f5222d"}
        },
        "behavior_tags": {
            "高频用户": "#722ed1",
            "异常消耗": "#f5222d",
            "测试行为": "#13c2c2",
            "批量操作": "#eb2f96",
            "深夜使用": "#1890ff",
            "敏感操作": "#cf1322",
            "模型对比": "#fa8c16",
            "长对话": "#52c41a"
        }
    }


# ==================== 启动 ====================

async def startup():
    """启动时初始化"""
    await init_db()
    print("✅ 数据库初始化完成")


if __name__ == "__main__":
    import uvicorn
    import asyncio
    import os
    
    # 确保数据目录存在
    os.makedirs("/app/data", exist_ok=True)
    
    # 初始化数据库
    asyncio.run(startup())
    
    # 自动生成演示数据（如果数据库为空）
    async def check_and_generate():
        from database import aiosqlite, DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM audit_logs")
            count = (await cursor.fetchone())[0]
            if count == 0:
                print("📝 数据库为空，自动生成演示数据...")
                from generate_data import generate_demo_data
                await generate_demo_data()
    
    asyncio.run(check_and_generate())
    
    # 非容器环境自动打开浏览器
    if not os.getenv("DOCKER_ENV"):
        print("🌐 正在打开浏览器...")
        webbrowser.open("http://localhost:8000")
    
    # 启动服务
    print("🚀 服务启动: http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
