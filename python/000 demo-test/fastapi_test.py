
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Query, Depends
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
import asyncio
import json

# 创建FastAPI 应用
app = FastAPI(
    title = "AI 应用Demo API",
    description="一个用于学习 FastAPI + AI 的示例项目",
    version="0.1.0",
)


# 建议路由
@app.get('/')
async def root():
    return {"message": "Hello, AI Developer!", "status": "ok"}

@app.get('/health')
async def health_check():
    """健康检查接口 —— 部署时必备"""
    return {"status": "healthy", "version": "0.1.0"}


# 路径参数
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    users = {1: "Alice", 2: "Bob", 3: "Charlie"}
    if user_id not in users:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user_id": user_id, "name": users[user_id]}

# ======================== 4. 查询参数 ========================

@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=100, description="返回数量"),
    model: str = Query(default="gpt-4o-mini", description="使用的模型"),
):
    """查询参数 —— /search?q=python&limit=20&model=gpt-4"""
    return {"query": q, "limit": limit, "model": model, "results": []}




if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════╗
    ║     FastAPI AI 学习 Demo 已启动          ║
    ║                                          ║
    ║  API 文档: http://localhost:8000/docs    ║
    ║  健康检查: http://localhost:8000/health  ║
    ║                                          ║
    ║  测试命令:                               ║
    ║  curl http://localhost:8000/             ║
    ║  curl http://localhost:8000/users/1      ║
    ║  curl -X POST http://localhost:8000/chat ║
    ║    -H "Content-Type: application/json"   ║
    ║    -d '{"message":"你好"}'               ║
    ╚══════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8080)
