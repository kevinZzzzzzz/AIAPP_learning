"""
前端转全栈 01: FastAPI 基础路由与参数校验 (对比 Express/Koa)
================================================================
作为前端工程师，你可能熟悉 Node.js 的 Express/Koa 或 Next.js API Routes。
在 Python 领域，FastAPI 就是最受欢迎的全栈后端框架。它基于 asyncio，性能媲美 Node.js，
并且原生支持 TypeScript 风格的类型提示与自动 OpenAPI (Swagger) 文档生成！

运行与测试方法：
1. 安装依赖: pip install fastapi uvicorn
2. 启动服务: uvicorn 01_FastAPI基础路由与参数_Express对比:app --reload
3. 打开浏览器访问 Swagger 自动交互文档: http://127.0.0.1:8000/docs
"""

from typing import Optional, List
from pydantic import BaseModel, Field

# 尝试导入 fastapi，未安装时提供降级提示
try:
    from fastapi import FastAPI, Query, Path, Header, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 尚未安装 `fastapi` 和 `uvicorn`。")
    print("👉 请在终端执行命令安装: pip install fastapi uvicorn pydantic")

# 实例化应用 (相当于 Express 的 const app = express();)
if HAS_FASTAPI:
    app = FastAPI(
        title="前端转全栈 Demo API",
        description="用于前端开发者对比 Express / FastAPI 的接口实现",
        version="1.0.0"
    )

    # === 关键全栈知识点: 配置 CORS 允许前端跨域访问 ===
    # JS/Node (Express): app.use(cors({ origin: "*" }))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],       # 允许跨域的来源域名 (如 http://localhost:3000)
        allow_credentials=True,
        allow_methods=["*"],       # 允许 GET, POST, PUT, DELETE 等
        allow_headers=["*"],       # 允许 Header 参数 (如 Authorization)
    )

    # =================================================================
    # 1. 基础 GET 路由 (对比 Express app.get('/api/ping', (req, res) => ...))
    # =================================================================
    @app.get("/api/ping")
    def ping():
        # Python FastAPI 会自动将 return 的 dict 转为 JSON 返回给前端 (无需 res.json())
        return {"status": "ok", "message": "Pong! 全栈后端运行正常"}


    # =================================================================
    # 2. 路径参数 Path & 查询参数 Query (req.params & req.query)
    # =================================================================
    # Express: app.get('/api/users/:userId', (req, res) => { const { userId } = req.params; const { detail } = req.query; })
    @app.get("/api/users/{user_id}")
    def get_user_detail(
        user_id: int = Path(..., description="用户ID (路径参数)", ge=1),  # ge=1 约束必须 >= 1
        detail: bool = Query(False, description="是否返回详细信息 (查询参数)") # http://localhost:8000/api/users/10?detail=true
    ):
        user_db = {
            10: {"id": 10, "username": "Kevin", "role": "Fullstack Developer"},
            20: {"id": 20, "name": "Alice", "role": "AI Engineer"}
        }

        user = user_db.get(user_id)
        if not user:
            # 异常抛出相当于 Express 的 res.status(404).json({ detail: "..." })
            raise HTTPException(status_code=404, detail="找不到该用户")
        
        if detail:
            user["skills"] = ["React", "TypeScript", "Python", "FastAPI", "LLM"]
        
        return {"success": True, "data": user}


    # =================================================================
    # 3. POST 请求体校验 (req.body vs Pydantic Model)
    # =================================================================
    # 前端 axios.post('/api/articles', { title: "...", tags: [...] })
    class CreateArticleSchema(BaseModel):
        title: str = Field(..., min_length=3, description="文章标题")
        content: str = Field(..., description="文章正文内容")
        tags: List[str] = Field(default=[], description="文章标签")
        is_published: bool = Field(default=True, description="是否立即发布")

    @app.post("/api/articles", status_code=201)
    def create_article(
        payload: CreateArticleSchema,  # FastAPI 自动从 Request Body 读取 JSON 并校验
        auth_token: Optional[str] = Header(None, alias="Authorization") # 读取 Header
    ):
        print(f"接收到的请求头 Authorization: {auth_token}")
        
        # 业务逻辑处理 (相当于后端 Controller 逻辑)
        new_article = {
            "id": 101,
            "title": payload.title,
            "content": payload.content,
            "tags": payload.tags,
            "is_published": payload.is_published
        }
        return {"success": True, "data": new_article}

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动 FastAPI 本地开发服务器: http://127.0.0.1:8000")
        print("📚 打开 API Swagger 交互文档: http://127.0.0.1:8000/docs")
        uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        print("无法启动服务器，请先安装 uvicorn 和 fastapi。")
