"""
FastAPI 进阶：路由模块化 (APIRouter)

演示如何将大项目拆分成多个文件。
假设这个文件是主入口 main.py。
"""

from fastapi import FastAPI
from routers import users, items
app = FastAPI(title="模块化 API 实例")


# 将 routers/users.py 和 routers/items.py 中的路由挂载到主应用上
# prefix="/users" 表示 users_router 下的所有路由都会自动带上 /users 前缀
app.include_router(users.router, prefix="/users", tags=["用户管理"])
app.include_router(items.router, prefix="/items", tags=['商品管理'])

@app.get('/')
async def root():
    return {"message": "Hello, 访问 /docs 查看 Swagger 接口文档，你会看到模块化的分组"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run('fastapi_test7:app', host="0.0.0.0", port=8080, reload=True)