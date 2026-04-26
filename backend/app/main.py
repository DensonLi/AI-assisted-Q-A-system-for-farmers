from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.base import engine, AsyncSessionLocal
from app.db.init_db import init_db
import app.models.user  # noqa: F401
import app.models.conversation  # noqa: F401
import app.models.region  # noqa: F401
import app.models.crop  # noqa: F401
import app.models.memory  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库（创建默认管理员）
    async with AsyncSessionLocal() as db:
        await init_db(db)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
