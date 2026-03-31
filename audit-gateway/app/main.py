from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import logging
import os
import secrets

from app.config import settings
from app.routers import audit, admin, stats
from app.auth import login_user, logout_user, DEMO_USERNAME

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {settings.APP_NAME}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Session 配置（演示用，使用随机 secret）
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    max_age=3600 * 8  # 8小时过期
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(audit.router)
app.include_router(admin.router)
app.include_router(stats.router)

# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ==================== 登录相关页面 ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页 - 如果已登录跳转到 admin，否则跳转到 login"""
    if request.session.get("user"):
        return RedirectResponse(url="/admin")
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    if request.session.get("user"):
        return RedirectResponse(url="/admin")
    
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 审计网关 - 登录</title>
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
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .login-box h1 {
            text-align: center;
            color: #333;
            margin-bottom: 8px;
            font-size: 24px;
        }
        .login-box p {
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
        .error-msg {
            margin-bottom: 15px;
            padding: 10px;
            background: #fff1f0;
            border: 1px solid #ffa39e;
            border-radius: 6px;
            color: #cf1322;
            font-size: 13px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🛡️ AI 审计网关</h1>
        <p>企业级 AI 模型调用审计平台</p>
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" value="admin" required>
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" value="admin" required>
            </div>
            <button type="submit" class="login-btn">登录</button>
        </form>
        
        <div class="demo-info">
            💡 演示账号：admin / admin
        </div>
    </div>
</body>
</html>
    """


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """登录处理"""
    if login_user(request, username, password):
        return RedirectResponse(url="/admin", status_code=302)
    
    # 登录失败返回错误页面
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录失败</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .error-box {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
        }}
        .error-box h2 {{ color: #cf1322; margin-bottom: 15px; }}
        .error-box p {{ color: #666; margin-bottom: 25px; }}
        .back-btn {{
            padding: 12px 30px;
            background: #1890ff;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="error-box">
        <h2>❌ 登录失败</h2>
        <p>用户名或密码错误</p>
        <a href="/login" class="back-btn">返回登录</a>
    </div>
</body>
</html>
    """, status_code=401)


@app.get("/logout")
async def logout(request: Request):
    """登出"""
    logout_user(request)
    return RedirectResponse(url="/login")


@app.get("/admin", response_class=FileResponse)
async def admin_page(request: Request):
    """管理后台 - 需要登录"""
    if not request.session.get("user"):
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(static_dir, 'index.html'))


@app.get("/api/user")
async def get_current_user(request: Request):
    """获取当前登录用户"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"username": user}


@app.get("/health")
async def health():
    return {"status": "healthy"}
