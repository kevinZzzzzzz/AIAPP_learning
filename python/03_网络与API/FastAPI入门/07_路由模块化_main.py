"""
FastAPI 进阶：路由模块化 (APIRouter)

演示如何将大项目拆分成多个文件。
假设这个文件是主入口 main.py。
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from routers import users, items # 导入其他文件中的路由模块

app = FastAPI(title="模块化 API 示例")

# 将 routers/users.py 和 routers/items.py 中的路由挂载到主应用上
# prefix="/users" 表示 users_router 下的所有路由都会自动带上 /users 前缀
app.include_router(users.router, prefix="/users", tags=["用户管理"])
app.include_router(items.router, prefix="/items", tags=["商品管理"])

@app.get("/")
async def root():
    return {"message": "Hello, 访问 /docs 查看 Swagger 接口文档，你会看到模块化的分组"}


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    # 为了演示，此处文件名使用了 07_路由模块化_main
    uvicorn.run("07_路由模块化_main:app", host="127.0.0.1", port=8000, reload=True)
