# pyrefly: ignore [missing-import]
from fastapi import APIRouter

# 创建一个 APIRouter 实例，它就像是一个迷你的 FastAPI 应用
router = APIRouter()

# 注意这里路径是 "/"，由于在 main 中挂载时设置了 prefix="/users"
# 所以实际访问路径是 "/users/"
@router.get("/")
async def get_users():
    return [{"username": "Alice"}, {"username": "Bob"}]

@router.get("/{user_id}")
async def get_user_by_id(user_id: int):
    return {"username": "Alice", "user_id": user_id}
