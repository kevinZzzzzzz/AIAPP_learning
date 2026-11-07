"""
FastAPI 进阶：后台任务 (Background Tasks)

后台任务允许你在返回 HTTP 响应之后，继续在后台执行耗时的操作。
这对于 AI 应用非常有用，例如：接收请求 -> 立即回复"处理中" -> 后台调用大模型生成文本/图片。
"""



from fastapi import FastAPI, BackgroundTasks, Body
import time
import asyncio


app = FastAPI(title="后台任务 (Background Tasks)")
# 这是一个普通的同步函数，模拟耗时任务（如发送邮件）
def write_notification(email: str, message:  str):
    print(f'开始给{email} 发送邮件')
    time.sleep(3)
    print(f'{email} 邮件发送完成: {message}')

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    """
    在路由参数中声明 BackgroundTasks 即可使用。
    使用 background_tasks.add_task(函数名, 参数1, 参数2...) 来添加任务。
    """
    background_tasks.add_task(write_notification, email, "您有一条新邮件")
    return {"message": "通知邮件已加入后台任务队列，即将发送"}

# ===============将参数放在请求体中=======================

@app.post("/send-notifications")
async def send_notification(background_tasks: BackgroundTasks, email: str = Body(..., embed=True)):
    """
    在路由参数中声明 BackgroundTasks 即可使用。
    使用 background_tasks.add_task(函数名, 参数1, 参数2...) 来添加任务。
    """
    background_tasks.add_task(write_notification, email, "您有一条新邮件")
    return {"message": "通知邮件已加入后台任务队列，即将发送"}



# ======================== AI 场景示例：异步后台任务 ========================
async def generate_ai_report(task_id: str):
    print(f"[Task {task_id}] 正在调用AI 模型生成报告...")
    await asyncio.sleep(5)
    print(f"[Task {task_id} 报告生成完毕]")
    # 实际场景中，这里可能会将结果保存到数据库，或者通过 WebSocket 推送给前端

@app.post("/generate-report/")
async def start_report_generation(background_tasks: BackgroundTasks):
    import uuid
    task_id = str(uuid.uuid4())
    # 添加异步任务到后台
    background_tasks.add_task(generate_ai_report, task_id)
    return {
        "message": "AI 正在奋笔疾书中...",
        "task_id": task_id,
        "status_url": f"/report-status/{task_id}" # 前端可以通过这个接口轮询状态
    }







