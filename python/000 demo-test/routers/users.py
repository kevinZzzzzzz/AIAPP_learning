from fastapi import APIRouter

router = APIRouter()

@router.get('/')
async def get_users():
    return [{"username": "Alice"}, {"username": "Bob"}]

@router.get('/{user_id}')
async def get_user_by_id(user_id: int):
    return {"username": "Alice", "user_id": user_id}