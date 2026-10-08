import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库连接 URL：优先读环境变量 DATABASE_URL，未设置时默认用零配置 SQLite 本地文件 ./sql_app.db
# 本地开发：无需设置，自动生成 ./sql_app.db
# 正式环境：DATABASE_URL="postgresql://user:password@host:5432/db" python main.py
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# SQLite 需关闭单线程检查才能在多线程 Web 服务中使用；其它数据库（PostgreSQL/MySQL）不需要该参数
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

# 创建数据库引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# 创建数据库 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 模型基类
Base = declarative_base()

# 数据库 Session 依赖注入函数 (供 FastAPI 路由使用)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

