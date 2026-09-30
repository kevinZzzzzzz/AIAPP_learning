"""
前端转全栈 03: 用户鉴权、JWT 与依赖注入 (对比 Express Middleware)
==================================================================
全栈开发的核心关口：如何保护敏感 API 接口（如扣除 AI 积分、修改用户配置、管理历史对话）？

Express 中我们习惯写中间件:
`app.get('/api/user/me', authenticateTokenMiddleware, (req, res) => ...)`

FastAPI 中拥有更先进优雅的【依赖注入系统 (Dependency Injection)】：`Depends()`
只需在路由函数形参中声明 `current_user: User = Depends(get_current_user)`，
FastAPI 就会自动拦截请求、解析 Authorization Header、校验 JWT 并自动注入用户实例对象！

运行方法：python 03_用户鉴权与JWT_Middleware对比.py
"""

import time
from typing import Optional, Dict, Any

try:
    from fastapi import FastAPI, Depends, HTTPException, status, Header
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 请安装依赖 `pip install fastapi uvicorn pydantic`。")


if HAS_FASTAPI:
    app = FastAPI(title="全栈 JWT 鉴权与 API 保护 Demo")

    # FastAPI 内置的 Bearer Token 提取器 (会自动在 Swagger UI 中右上角显示 🔒 登录按钮！)
    security_bearer = HTTPBearer()

    # === 1. 简易 JWT Token 签发与解密 (纯 Python 演示逻辑) ===
    SECRET_KEY = "super-secret-key-for-fullstack-ai"

    def create_mock_jwt(user_id: int, username: str) -> str:
        """模拟 JWT Token 签名过程 (生产环境推荐 pyjwt 库)"""
        payload = f"{user_id}:{username}:{int(time.time()) + 3600}"
        return f"mock_jwt_token__{payload}"

    def decode_mock_jwt(token: str) -> Dict[str, Any]:
        """校验并提取 Token Payload"""
        if not token.startswith("mock_jwt_token__"):
            raise ValueError("无效的 Token 签名")
        raw = token.replace("mock_jwt_token__", "")
        parts = raw.split(":")
        user_id, username, exp = int(parts[0]), parts[1], int(parts[2])
        if time.time() > exp:
            raise ValueError("Token 已过期，请重新登录")
        return {"id": user_id, "username": username}


    # === 2. 核心: 鉴权依赖项 (相当于 Express 的 authenticateToken 中间件) ===
    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> Dict[str, Any]:
        """
        FastAPI 依赖注入函数:
        1. 自动从 Header 读取 `Authorization: Bearer <token>`
        2. 校验合法性，失败直接中断请求并抛出 401 错误
        3. 成功则返回当前登录的用户字典
        """
        token = credentials.credentials
        try:
            user_data = decode_mock_jwt(token)
            return user_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"身份验证失败: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


    # === 3. 登录接口 (公开路由，无需 Token) ===
    class LoginRequest(BaseModel):
        username: str
        password: str

    @app.post("/api/auth/login")
    def login(payload: LoginRequest):
        # 简易演示: 任意密码均可登录
        if payload.username in ["kevin", "admin", "alice"]:
            token = create_mock_jwt(user_id=888, username=payload.username)
            return {
                "success": True,
                "token_type": "bearer",
                "access_token": token,
                "user": {"id": 888, "username": payload.username}
            }
        raise HTTPException(status_code=400, detail="用户名或密码错误")


    # === 4. 受保护路由 (Protected Route) ===
    # 💥 注意形参里的 Depends(get_current_user)！这就是 FastAPI 的精髓！
    @app.get("/api/user/profile")
    def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
        # 代码能走到这里，说明 Token 100% 合法且未过期！current_user 已经有值了！
        return {
            "success": True,
            "message": "成功访问受保护的受鉴权接口",
            "current_user": current_user,
            "vip_level": "Pro AI Member",
            "remaining_credits": 999
        }

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动鉴权 API 服务器: http://127.0.0.1:8000")
        print("🔒 体验 Swagger Auth 登录测试: http://127.0.0.1:8000/docs")
        uvicorn.run(app, host="127.0.0.1", port=8000)
