from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models, schemas, crud
from database import engine, get_db

# 1. 自动根据 ORM 模型创建 SQLite 数据表
models.Base.metadata.create_all(bind=engine)

# 2. 实例化 FastAPI 应用
app = FastAPI(
    title="Python FastAPI 全栈后端示例 API",
    description="支持与前端 React/Vue/Axios 联调的完整 RESTful 后端项目",
    version="1.0.0"
)

# 3. 配置 CORS 全局跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 自动装载初始测试种子数据
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    if db.query(models.UserModel).count() == 0:
        crud.create_user(db, schemas.UserCreate(username="admin", nickname="全栈超级管理员", role="ADMIN"))
        crud.create_user(db, schemas.UserCreate(username="kevin", nickname="前端工程师", role="USER"))
        crud.create_user(db, schemas.UserCreate(username="alice", nickname="AI 算法工程师", role="USER"))
        
        crud.create_appointment(db, schemas.AppointmentCreate(user_id=2, title="AI 全栈架构咨询", description="关于 FastAPI + React 方案", status="CONFIRMED"))
        crud.create_appointment(db, schemas.AppointmentCreate(user_id=3, title="大模型工具函数联调", description="Function Calling 调试", status="PENDING"))
        print("🌱 Python FastAPI: 初始化默认 3 条用户 & 2 条预约数据成功！")

# 5. RESTful API 路由

@app.get("/")
def read_root():
    return {
        "code": 200,
        "message": "🚀 Python FastAPI 服务运行正常！",
        "docs": "访问 http://127.0.0.1:8000/docs 查看可视化 Swagger 文档"
    }

# --- Users API ---
@app.get("/api/users")
def read_users(db: Session = Depends(get_db)):
    users = crud.get_users(db)
    return {"code": 200, "message": "获取成功", "data": users}

@app.get("/api/users/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="找不到该用户")
    return {"code": 200, "message": "获取成功", "data": user}

@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    created = crud.create_user(db, user)
    return {"code": 200, "message": "用户创建成功", "data": created}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": f"成功删除用户 ID={user_id}", "data": None}

# --- Appointments API ---
@app.get("/api/appointments")
def read_appointments(user_id: int = None, db: Session = Depends(get_db)):
    appts = crud.get_appointments(db, user_id=user_id)
    return {"code": 200, "message": "获取成功", "data": appts}

@app.post("/api/appointments", status_code=status.HTTP_201_CREATED)
def create_appointment(appt: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    created = crud.create_appointment(db, appt)
    return {"code": 200, "message": "预约创建成功", "data": created}


if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 Python FastAPI 服务器: http://127.0.0.1:8000")
    print("📚 API 可视化交互文档: http://127.0.0.1:8000/docs")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
