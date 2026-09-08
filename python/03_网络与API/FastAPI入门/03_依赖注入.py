"""
FastAPI 进阶：依赖注入 (Dependency Injection)

依赖注入是 FastAPI 的核心特性，它允许你在路由处理函数中声明所需的依赖项（如数据库连接、认证信息、通用参数等）。
FastAPI 会在请求到达路由之前，自动执行依赖项函数，并将结果传递给路由。
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional

app = FastAPI()

# ======================== 1. 基础依赖项 ========================

async def common_parameters(q: Optional[str] = None, skip: int = 0, limit: int = 100):
    """一个通用的分页查询参数依赖"""
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    """
    通过 Depends(common_parameters)，FastAPI 会：
    1. 接收请求中的 q, skip, limit 查询参数
    2. 将它们传给 common_parameters 函数
    3. 将 common_parameters 的返回值赋给 commons 变量
    """
    return {"message": "Items fetched", "params": commons}

@app.get("/users/")
async def read_users(commons: dict = Depends(common_parameters)):
    # 依赖项可以被多个路由复用，减少代码重复
    return {"message": "Users fetched", "params": commons}


# ======================== 2. 用于鉴权的依赖项 ========================

async def verify_token(x_token: str = Header(...)):
    """验证 Header 中是否包含特定的 Token"""
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")
    return x_token

@app.get("/secret-data/")
async def get_secret_data(token: str = Depends(verify_token)):
    """只有在 Header 中传入了正确的 X-Token，才能访问此路由"""
    return {"message": "Secret data access granted", "token_used": token}


# ======================== 3. 类作为依赖项 ========================

class CommonQueryParams:
    def __init__(self, q: Optional[str] = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

# FastAPI 会自动实例化这个类
@app.get("/things/")
async def read_things(commons: CommonQueryParams = Depends(CommonQueryParams)):
    # 简写形式：commons: CommonQueryParams = Depends()
    return {"q": commons.q, "skip": commons.skip, "limit": commons.limit}


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("03_依赖注入:app", host="127.0.0.1", port=8000, reload=True)
