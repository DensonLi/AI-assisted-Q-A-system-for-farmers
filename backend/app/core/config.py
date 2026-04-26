from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "农户种植技巧AI辅助问答系统"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str
    ASYNC_DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 知识库 API（ziiku.cn RAG 服务）
    KNOWLEDGE_API_BASE_URL: str = ""   # 完整 URL，如 https://center.ziiku.cn/api/aibot/openapi/conversation/chat
    KNOWLEDGE_API_KEY: str = ""        # x-api-key 认证头
    KNOWLEDGE_BOT_ID: str = ""         # bot_id，机器人唯一标识
    KNOWLEDGE_TOP_K: int = 5           # 保留字段，控制上下文片段数（当前固定返回 1 条 RAG 摘要）
    KNOWLEDGE_TIMEOUT_SEC: int = 15

    # LLM 配置（OpenAI 兼容接口，支持 DeepSeek / OpenAI / 其他兼容服务）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"   # OpenAI 兼容 base_url；留空使用官方 OpenAI
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT_SEC: int = 60
    LLM_TEMPERATURE: float = 0.3
    LLM_HISTORY_TURNS: int = 10

    # 初始管理员账号
    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_PASSWORD: str = "Admin@123456"
    FIRST_ADMIN_EMAIL: str = "admin@example.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
