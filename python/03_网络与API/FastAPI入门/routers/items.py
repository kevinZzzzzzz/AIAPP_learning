# pyrefly: ignore [missing-import]
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_items():
    return [{"item_name": "Keyboard"}, {"item_name": "Mouse"}]
