"""
FastAPI 跨域与中间件 —— 面向前端开发者
======================================

前后端分离开发中，前端 (如 React/Vue) 请求后端 (FastAPI) 最常碰到的就是跨域 (CORS) 报错：
"Access to fetch at '...' from origin '...' has been blocked by CORS policy"

在 Express 中，我们通常使用 `app.use(cors())`。
在 FastAPI 中配置跨域同样非常简单，使用的是内置的 `CORSMiddleware`。
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="CORS & Middleware Demo")

# ======================== 1. 配置 CORS 跨域 ========================

# 允许访问的源 (前端运行的地址)
# 开发环境下为了图省事，也可以直接填 ["*"]
origins = [
    "http://localhost",
    "http://localhost:3000",   # React 默认端口
    "http://localhost:5173",   # Vite 默认端口
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

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # 【请求进入时】记录开始时间
    start_time = time.time()
    
    # 【转交控制权】执行实际的路由处理函数
    response = await call_next(request)
    
    # 【响应返回时】计算耗时并添加到自定义 Header 中
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f} sec"
    
    return response


# ======================== 路由 ========================

@app.get("/")
async def root():
    return {"message": "Hello CORS!"}

@app.get("/data")
async def get_data():
    # 模拟一个耗时操作，以便上面的耗时计算中间件能记录到
    time.sleep(0.1)
    return {"data": "这是受 CORS 保护，且通过中间件记录了耗时的数据"}


"""
运行方法：
$ pip install fastapi uvicorn
$ uvicorn 02_跨域与中间件:app --reload

然后用前端代码发起 fetch 请求测试：
fetch('http://127.0.0.1:8000/data')
  .then(res => res.json())
  .then(console.log)
"""
