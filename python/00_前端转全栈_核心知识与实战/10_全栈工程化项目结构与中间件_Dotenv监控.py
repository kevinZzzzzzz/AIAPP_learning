"""
前端转全栈 10: 项目工程化 —— 环境变量、全局异常兜底与中间件监控
==================================================================
真正工业级的全栈应用，离不开工程化规范：
1. 环境变量配置管理 (`.env` 文件管理密钥 API Key)
2. 全局异常兜底 (未捕获崩溃统一返回 `{ "success": false, "error": "..." }` 防止前端崩溃)
3. 自定义 Middleware 中间件 (统计 API 响应耗时、打印 Request Log)

运行方法：python 10_全栈工程化项目结构与中间件_Dotenv监控.py
"""

import os
import time

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 请安装依赖 `pip install fastapi uvicorn python-dotenv`。")


# === 1. 环境变量管理 (dotenv 机制) ===
# Node.js: require('dotenv').config() / process.env.API_KEY
# Python: from dotenv import load_dotenv; os.getenv("API_KEY")
API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-default-demo-key-999")
ENV_NAME = os.getenv("APP_ENV", "development")


if HAS_FASTAPI:
    app = FastAPI(
        title="全栈工程化规范 API",
        description=f"当前运行环境: {ENV_NAME}"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === 2. 自定义 Request 耗时监控中间件 ===
    # 每次请求会在 Response Header 中返回 `X-Process-Time: 0.002s`
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        
        # 执行下一个中间件/路由处理器 (相当于 Express 的 next())
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        print(f"📡 [API Log] {request.method} {request.url.path} - 完成耗时: {process_time:.4f}s")
        return response


    # === 3. 全局未捕获异常处理 (Global Exception Handler) ===
    # 💥 防止任何 Python 后端报错导致全服崩溃或抛出不友好的 HTML 错误页！
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        print(f"❌ [全局捕获崩溃]: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "后端服务器发生未预期错误，已由全局中间件拦截安全处理",
                "detail": str(exc)
            }
        )


    # === 4. 测试接口 ===
    @app.get("/api/env-info")
    def get_env_info():
        return {
            "success": True,
            "env": ENV_NAME,
            "api_key_masked": f"{API_KEY[:4]}****{API_KEY[-4:]}"
        }

    # 模拟后端触发崩溃的异常接口
    @app.get("/api/test-crash")
    def trigger_crash():
        # 故意除以 0 触发 ZeroDivisionError
        result = 1 / 0
        return {"result": result}

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print(f"🚀 启动工程化 API 服务器 (环境: {ENV_NAME}): http://127.0.0.1:8000")
        print("💡 测试全局报错兜底: GET http://127.0.0.1:8000/api/test-crash")
        uvicorn.run(app, host="127.0.0.1", port=8000)
