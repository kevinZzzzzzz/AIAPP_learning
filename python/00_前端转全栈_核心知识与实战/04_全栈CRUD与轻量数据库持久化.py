"""
前端转全栈 04: 全栈 CRUD (增删改查)、条件筛选与分页列表设计
================================================================
前端应用（如 Admin 管理后台、对话历史列表）最常对接的就是 CRUD 接口。
本 Demo 演示如何使用 FastAPI 实现标准规范的 RESTful API：
- GET    /api/todos          (列表与分页过滤)
- POST   /api/todos          (新增资源)
- PUT    /api/todos/{id}     (更新资源)
- DELETE /api/todos/{id}     (删除资源)

运行方法：python 04_全栈CRUD与轻量数据库持久化.py
"""

from typing import List, Optional
import time

try:
    from fastapi import FastAPI, HTTPException, Query, status
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 请安装依赖 `pip install fastapi uvicorn pydantic`。")


if HAS_FASTAPI:
    app = FastAPI(title="全栈 CRUD 数据库模型 API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === 1. 数据模型定义 ===
    class TodoCreateSchema(BaseModel):
        title: str = Field(..., min_length=1, description="待办事项标题")
        priority: str = Field("medium", description="优先级: low / medium / high")

    class TodoUpdateSchema(BaseModel):
        title: Optional[str] = None
        completed: Optional[bool] = None
        priority: Optional[str] = None

    class TodoResponseSchema(BaseModel):
        id: int
        title: str
        completed: bool
        priority: str
        created_at: float

    # 内存数据库 (在实际开发中对应 SQLite / PostgreSQL / MongoDB)
    todos_db: List[dict] = [
        {"id": 1, "title": "学习 Python 基础语法", "completed": True, "priority": "high", "created_at": time.time() - 3600},
        {"id": 2, "title": "掌握 FastAPI 全栈后端", "completed": False, "priority": "high", "created_at": time.time() - 1800},
        {"id": 3, "title": "构建第一个全栈 AI Agent 应用", "completed": False, "priority": "medium", "created_at": time.time()},
    ]
    auto_id_counter = 3


    # === 2. API 路由实现 ===

    # READ ALL (带搜索与分页)
    # 前端: axios.get('/api/todos', { params: { page: 1, page_size: 10, search: 'AI' } })
    @app.get("/api/todos")
    def get_todos(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=50, description="每页条数"),
        search: Optional[str] = Query(None, description="搜索关键词")
    ):
        filtered = todos_db
        if search:
            filtered = [t for t in filtered if search.lower() in t["title"].lower()]
        
        total = len(filtered)
        # 分页切片计算 (与 JS arr.slice(start, end) 完全相同)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = filtered[start_idx:end_idx]

        return {
            "success": True,
            "data": paged_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }


    # CREATE
    # 前端: axios.post('/api/todos', { title: '写代码', priority: 'high' })
    @app.post("/api/todos", status_code=status.HTTP_201_CREATED)
    def create_todo(payload: TodoCreateSchema):
        global auto_id_counter
        auto_id_counter += 1
        
        new_item = {
            "id": auto_id_counter,
            "title": payload.title,
            "completed": False,
            "priority": payload.priority,
            "created_at": time.time()
        }
        todos_db.append(new_item)
        return {"success": True, "data": new_item}


    # UPDATE
    # 前端: axios.put('/api/todos/2', { completed: true })
    @app.put("/api/todos/{todo_id}")
    def update_todo(todo_id: int, payload: TodoUpdateSchema):
        todo = next((t for t in todos_db if t["id"] == todo_id), None)
        if not todo:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if payload.title is not None:
            todo["title"] = payload.title
        if payload.completed is not None:
            todo["completed"] = payload.completed
        if payload.priority is not None:
            todo["priority"] = payload.priority

        return {"success": True, "data": todo}


    # DELETE
    # 前端: axios.delete('/api/todos/1')
    @app.delete("/api/todos/{todo_id}")
    def delete_todo(todo_id: int):
        global todos_db
        todo = next((t for t in todos_db if t["id"] == todo_id), None)
        if not todo:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        todos_db = [t for t in todos_db if t["id"] != todo_id]
        return {"success": True, "message": f"成功删除 ID={todo_id} 的项"}

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动全栈 CRUD API 服务器: http://127.0.0.1:8000")
        print("📝 API 测试文档: http://127.0.0.1:8000/docs")
        uvicorn.run(app, host="127.0.0.1", port=8000)
