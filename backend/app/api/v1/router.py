from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, conversations, regions, crops, memories, system_config, reminders

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(regions.router, prefix="/regions", tags=["区域"])
api_router.include_router(crops.router, prefix="/crops", tags=["作物"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["问答对话"])
api_router.include_router(memories.router, prefix="/memories", tags=["记忆管理"])
api_router.include_router(system_config.router, prefix="/system-config", tags=["系统配置"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["日历提醒"])
