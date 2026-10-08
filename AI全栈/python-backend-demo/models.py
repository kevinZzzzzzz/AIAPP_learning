from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    nickname = Column(String(100), nullable=False)
    role = Column(String(50), default="USER")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AppointmentModel(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
