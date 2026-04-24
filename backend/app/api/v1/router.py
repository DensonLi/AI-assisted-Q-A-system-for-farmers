from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, conversations

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["问答对话"])
