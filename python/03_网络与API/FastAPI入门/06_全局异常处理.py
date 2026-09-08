"""
FastAPI 进阶：全局异常处理

在实际项目中，我们希望无论代码哪里出错了，后端都能返回格式统一的 JSON 给前端，
而不是返回一堆难以看懂的堆栈信息或格式不一致的错误结构。
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from fastapi.exceptions import RequestValidationError

app = FastAPI()

# ======================== 1. 自定义业务异常 ========================

class BusinessException(Exception):
    """自定义的基础业务异常类"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

# ======================== 2. 注册异常处理器 ========================

# 处理我们自己抛出的 BusinessException
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=400, # 可以统一定义 HTTP 状态码
        content={
            "success": False,
            "error_code": exc.code,
            "error_message": exc.message,
            "data": None
        },
    )

# 覆盖 FastAPI 默认的请求参数校验失败异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": 42200,
            "error_message": "参数校验失败",
            "details": exc.errors() # 包含具体的校验错误信息
        },
    )

# 兜底：处理所有未被捕获的其他异常 (500 Internal Server Error)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 实际项目中这里应该把 exc 记录到日志系统中
    print(f"服务器内部发生严重错误: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": 50000,
            "error_message": "服务器开小差了，请稍后再试",
            "data": None
        },
    )


# ======================== 3. 路由测试 ========================

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id == 404:
        # 触发自定义业务异常
        raise BusinessException(code=40401, message="商品不存在")
    if item_id == 500:
        # 触发未捕获的代码错误，会走到 global_exception_handler
        return 1 / 0
        
    return {"success": True, "data": {"item_id": item_id}}


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("06_全局异常处理:app", host="127.0.0.1", port=8000, reload=True)
