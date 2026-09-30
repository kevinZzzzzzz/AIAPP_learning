"""
前端转全栈 09: 后台异步任务与长耗时任务 (Background Tasks)
====================================================================
在 AI 开发中，有些任务非常耗时（如 AI 视频生成、大量 PDF 向量化化、发送邮件/短信）。
你不能让 HTTP 请求一直挂着挂几分钟，这会导致连接超时。

Node.js 做法: 使用 BullMQ / Redis 消息队列 (生产 `job.add()`)
FastAPI 做法: 原生支持零配置 `BackgroundTasks`！
- API 接收到请求后，立即返回响应：`{"status": "processing", "task_id": "xxx"}`
- 耗时任务在后台线程/协程中异步默默执行，前端可通过轮询 (Polling) 检查任务进度！

运行方法：python 09_后台长耗时任务与异步队列_BullMQ对比.py
"""

import time
import uuid
from typing import Dict, Any, Optional

try:
    from fastapi import FastAPI, BackgroundTasks, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 请安装依赖 `pip install fastapi uvicorn pydantic`。")


if HAS_FASTAPI:
    app = FastAPI(title="全栈后台异步任务 API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 内存任务字典: { task_id: { status, result, progress } }
    tasks_memory_db: Dict[str, Dict[str, Any]] = {}


    # === 1. 后台耗时计算函数 (在后台默默运行) ===
    def run_heavy_ai_job(task_id: str, prompt: str):
        """模拟长达 10 秒的后台 AI 渲染/文档处理任务"""
        print(f"⚙️ [后台 Task-{task_id}] 开始耗时处理: '{prompt}'...")
        
        # 模拟进度 0% -> 50% -> 100%
        tasks_memory_db[task_id]["status"] = "processing"
        tasks_memory_db[task_id]["progress"] = 10
        time.sleep(2)
        
        tasks_memory_db[task_id]["progress"] = 50
        time.sleep(2)
        
        # 任务完成，写入最终结果
        tasks_memory_db[task_id]["status"] = "completed"
        tasks_memory_db[task_id]["progress"] = 100
        tasks_memory_db[task_id]["result"] = f"AI 复杂渲染已完成！对应提示词: '{prompt}' 的高清成果图已生成。"
        print(f"✅ [后台 Task-{task_id}] 处理成功完成！")


    # === 2. API 路由接口 ===
    class TaskCreateRequest(BaseModel):
        prompt: str

    # 触发耗时任务
    # 前端: const { task_id } = await axios.post('/api/tasks/generate', { prompt })
    @app.post("/api/tasks/generate", status_code=202)
    def create_background_task(
        payload: TaskCreateRequest, 
        background_tasks: BackgroundTasks  # FastAPI 自动注入后台任务管理器
    ):
        task_id = str(uuid.uuid4())[:8]  # 生成短任务 ID
        
        # 初始化任务状态
        tasks_memory_db[task_id] = {
            "task_id": task_id,
            "prompt": payload.prompt,
            "status": "pending",
            "progress": 0,
            "result": None,
            "created_at": time.time()
        }

        # 💥 核心：把耗时任务扔进后台，当前 HTTP 请求立即使 202 Accepted 返回！
        background_tasks.add_task(run_heavy_ai_job, task_id, payload.prompt)

        return {
            "success": True,
            "message": "任务已提交后台处理中，请轮询查询进度",
            "task_id": task_id,
            "status": "pending"
        }


    # 前端轮询查询任务进度
    # 前端: const res = await axios.get(`/api/tasks/${taskId}`)
    @app.get("/api/tasks/{task_id}")
    def get_task_status(task_id: str):
        task = tasks_memory_db.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="未找到该任务 ID")
        return {"success": True, "data": task}

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动后台任务 API 服务器: http://127.0.0.1:8000")
        print("📝 文档地址: http://127.0.0.1:8000/docs")
        uvicorn.run(app, host="127.0.0.1", port=8000)
