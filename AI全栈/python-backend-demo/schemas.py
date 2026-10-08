from pydantic import BaseModel
from typing import Optional, List
import datetime

# --- User Schema ---
class UserBase(BaseModel):
    username: str
    nickname: str
    role: Optional[str] = "USER"

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# --- Appointment Schema ---
class AppointmentBase(BaseModel):
    user_id: int
    title: str
    description: Optional[str] = None
    status: Optional[str] = "PENDING"

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    id: int
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# --- Unified API Result ---
class APIResult(BaseModel):
    code: int = 200
    message: str = "操作成功"
    data: Optional[dict | list | str | int | float | bool] = None
