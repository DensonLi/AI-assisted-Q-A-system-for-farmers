"""
pytest 测试固件（fixtures）
────────────────────────────────────────────────
使用 SQLite (aiosqlite) 作为内存数据库，无需真实 PostgreSQL/Redis。
JSONB 列通过 app/db/types.py 自动降级为 JSON。
"""
import os
from typing import AsyncGenerator

# 必须在导入 app 之前设置环境变量
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["ASYNC_DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-padding!!"
os.environ["LLM_API_KEY"] = ""
os.environ["KNOWLEDGE_BASE_URL"] = ""
os.environ["FIRST_ADMIN_USERNAME"] = "admin"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@test.com"
os.environ["FIRST_ADMIN_PASSWORD"] = "Admin@1234"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base, get_db
from app.main import app

# ─── SQLite 测试引擎 ─────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


# ─── 全局建表/删表 ───────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ─── 每个测试独立 session ────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session
        await session.rollback()


# ─── 注入测试 DB 的 HTTPX 客户端 ────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # 关键：FastAPI 依赖覆盖必须是 async generator 函数（不是调用结果）
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── 测试用户 fixtures ───────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """创建管理员用户并返回 JWT access_token"""
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    from sqlalchemy import select

    async with TestSession() as session:
        existing = (
            await session.execute(select(User).where(User.username == "testadmin"))
        ).scalar_one_or_none()
        if not existing:
            user = User(
                username="testadmin",
                email="testadmin@test.com",
                hashed_password=get_password_hash("Admin@1234"),
                role=UserRole.admin,
                is_active=True,
            )
            session.add(user)
            await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin", "password": "Admin@1234"
    })
    assert resp.status_code == 200, f"admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient) -> str:
    """创建普通用户并返回 JWT access_token"""
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    from sqlalchemy import select

    async with TestSession() as session:
        existing = (
            await session.execute(select(User).where(User.username == "testuser"))
        ).scalar_one_or_none()
        if not existing:
            user = User(
                username="testuser",
                email="testuser@test.com",
                hashed_password=get_password_hash("User@1234"),
                role=UserRole.user,
                is_active=True,
            )
            session.add(user)
            await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "User@1234"
    })
    assert resp.status_code == 200, f"user login failed: {resp.text}"
    return resp.json()["access_token"]
