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

    # 知识库 API（后续填入）
    KNOWLEDGE_API_BASE_URL: str = ""
    KNOWLEDGE_API_KEY: str = ""

    # 初始管理员账号
    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_PASSWORD: str = "Admin@123456"
    FIRST_ADMIN_EMAIL: str = "admin@example.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
