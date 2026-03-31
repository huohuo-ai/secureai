"""
简单的 Session 登录认证（演示用）
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

# 演示账号
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "admin"


def verify_login(request: Request):
    """验证用户是否已登录"""
    user = request.session.get("user")
    if user != DEMO_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user


def login_user(request: Request, username: str, password: str) -> bool:
    """验证账号密码并登录"""
    if username == DEMO_USERNAME and password == DEMO_PASSWORD:
        request.session["user"] = username
        return True
    return False


def logout_user(request: Request):
    """登出"""
    request.session.clear()
