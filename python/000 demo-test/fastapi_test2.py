from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title='CORS & Middleware Demo')

# ======================== 1. 配置 CORS 跨域 ========================
# 允许访问的源 (前端运行的地址)
# 开发环境下为了图省事，也可以直接填 ["*"]
origins = [
    "http://192.169.31.135",
    # "*"
]
# 将 CORS 中间件加入应用
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 允许的源
    allow_credentials=True,      # 允许携带 Cookie
    allow_methods=["*"],         # 允许的请求方法，如 GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],         # 允许的请求头
)
# ======================== 2. 编写自定义中间件 ========================
"""
中间件 (Middleware) 是一个拦截请求并在返回响应前后做一些处理的函数。
在 JS (Express/Koa) 中：
app.use(async (req, res, next) => {
    // 请求前处理
    await next();
    // 响应后处理
});

FastAPI 的中间件写法非常类似，使用 @app.middleware("http")
"""
@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    start_time = time.time() # 请求进入时，记录开始时间
    response = await call_next(request) # 执行实际的路由处理函数
    # 响应返回时，计算耗时并添加到自定义Header中
    process_time = time.time() - start_time
    response.headers['X-Process-Time'] = f"{process_time:.4f} sec"
    return response


# =========路由================
@app.get('/')
async def root():
    return {"message": "hello CORS"}

@app.get("/data")
async def get_data():
    time.sleep(2)
    return {"data": "这是受 CORS 保护。且通过中间件记录了耗时的数据"}
    


    """
运行方法：
$ pip install fastapi uvicorn
    uvicorn fastapi_test2:app --host 0.0.0.0 --port 8080 --reload
    """