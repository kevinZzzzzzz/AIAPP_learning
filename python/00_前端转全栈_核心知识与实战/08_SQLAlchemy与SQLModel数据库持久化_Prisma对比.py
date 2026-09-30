"""
前端转全栈 08: 真实数据库持久化与 ORM 选型 (对比 Prisma / TypeORM / Mongoose)
==================================================================================
全栈开发的核心核心：数据库 (Database)！
在前端 Node.js 中，你可能用过 Prisma (`prisma.user.findMany()`)、TypeORM 或 MongoDB Mongoose。
在 Python 全栈生态中，标准霸主是 **SQLAlchemy**，以及 FastAPI 作者亲自打造的 **SQLModel**（它完美结合了 Pydantic 校验 + SQLAlchemy ORM！）。

本 Demo 使用 Python 原生零配置轻量数据库 **SQLite** (自动生成 `app_database.db` 文件)：
- 自动建表 (Create Tables)
- 真实数据库事务 (Transactions: Session commit / rollback)
- FastAPI 整合 real DB 交互 (读写磁盘文件，重启服务器数据不丢失！)

运行方法：python 08_SQLAlchemy与SQLModel数据库持久化_Prisma对比.py
"""

import os
import time
from typing import List, Optional

try:
    from fastapi import FastAPI, Depends, HTTPException, Query, status
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    
    # 尝试导入 SQLAlchemy (Python 最成熟的 ORM 框架)
    from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    
    HAS_DB_LIBS = True
except ImportError:
    HAS_DB_LIBS = False
    print("⚠️ 提示: 请安装数据库 ORM 相关依赖包: `pip install fastapi uvicorn sqlalchemy pydantic`。")


if HAS_DB_LIBS:
    # === 1. 数据库连接配置 (Database Connection Setup) ===
    # 使用本地 SQLite 数据库文件 (开发测试首选，生产环境仅需把 url 改为 postgresql://...)
    DB_FILE_PATH = "./app_database.db"
    DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

    # 创建数据库引擎 Engine
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}  # SQLite 专用参数
    )
    
    # 创建数据库会话工厂 (Session Maker)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 所有 ORM 模型基类 (类似于 Prisma Schema 的 model 定义)
    Base = declarative_base()


    # === 2. ORM 表结构定义 (Prisma / TypeORM 对比) ===
    """
    Prisma Schema 等价定义:
    model Conversation {
      id        Int      @id @default(autoincrement())
      title     String
      model     String   @default("deepseek-chat")
      prompt    String
      response  String
      tokens    Int      @default(0)
      created_at Float
    }
    """
    class ConversationModel(Base):
        __tablename__ = "conversations"  # 数据库真实表名

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        title = Column(String(100), nullable=False)
        model = Column(String(50), default="deepseek-chat")
        prompt = Column(Text, nullable=False)
        response = Column(Text, nullable=False)
        tokens = Column(Integer, default=0)
        created_at = Column(Float, default=time.time)


    # === 3. 自动建表 (Auto Create Tables on Startup) ===
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表 `conversations` 初始化成功 (SQLite 存储文件: ./app_database.db)")


    # === 4. Pydantic API 校验模型 (DTO: Data Transfer Object) ===
    class ChatHistoryCreate(BaseModel):
        title: str = Field(..., min_length=1, description="对话标题")
        prompt: str = Field(..., description="用户输入的 Prompt")
        response: str = Field(..., description="AI 模型的回答内容")
        model: str = "deepseek-chat"
        tokens: int = 150

    class ChatHistoryResponse(BaseModel):
        id: int
        title: str
        prompt: str
        response: str
        model: str
        tokens: int
        created_at: float

        class Config:
            from_attributes = True  # 允许与 ORM 模型相互转换


    # === 5. FastAPI + 数据库 Session 依赖注入 (Database Dependency) ===
    def get_db():
        """
        全栈核心点: 每个 HTTP 请求自动开启一个数据库事务 Session，
        请求处理结束后自动关闭，防止数据库连接泄露！
        """
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


    # === 6. FastAPI 全栈数据库 API 路由 ===
    app = FastAPI(title="SQLite 真实数据库持久化 API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 查 (Read All)
    @app.get("/api/db/conversations", response_model=List[ChatHistoryResponse])
    def read_conversations(
        skip: int = 0, 
        limit: int = 20, 
        search: Optional[str] = None,
        db: Session = Depends(get_db)
    ):
        query = db.query(ConversationModel)
        if search:
            query = query.filter(ConversationModel.prompt.contains(search))
        
        # SQL ORDER BY created_at DESC LIMIT limit OFFSET skip
        results = query.order_by(ConversationModel.created_at.desc()).offset(skip).limit(limit).all()
        return results


    # 增 (Create)
    @app.post("/api/db/conversations", response_model=ChatHistoryResponse, status_code=status.HTTP_201_CREATED)
    def create_conversation(
        payload: ChatHistoryCreate, 
        db: Session = Depends(get_db)
    ):
        # 创建 ORM 实体对象
        db_item = ConversationModel(
            title=payload.title,
            prompt=payload.prompt,
            response=payload.response,
            model=payload.model,
            tokens=payload.tokens,
            created_at=time.time()
        )
        db.add(db_item)        # 添加到 SQL 事务
        db.commit()            # 提交到磁盘数据库文件！
        db.refresh(db_item)    # 刷新获得数据库分配的自增 ID
        return db_item


    # 删 (Delete)
    @app.delete("/api/db/conversations/{conv_id}")
    def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
        db_item = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="数据库中未找到该记录")
        
        db.delete(db_item)
        db.commit()
        return {"success": True, "message": f"成功从真实数据库中删除记录 ID={conv_id}"}

else:
    app = None


if __name__ == "__main__":
    if HAS_DB_LIBS:
        import uvicorn
        print("🚀 启动数据库服务: http://127.0.0.1:8000")
        print("🗄️ 数据库文件位置: ./app_database.db (重启服务器数据绝对不会丢失)")
        print("📝 文档交互入口: http://127.0.0.1:8000/docs")
        uvicorn.run(app, host="127.0.0.1", port=8000)
