"""
认证相关 API 测试
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestLogin:
    async def test_login_success(self, client: AsyncClient, user_token: str):
        # user_token fixture 已完成登录，这里验证 token 有效
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"

    async def test_login_wrong_password(self, client: AsyncClient, user_token: str):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser", "password": "WrongPass"
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "ghost", "password": "anything"
        })
        assert resp.status_code == 401

    async def test_protected_route_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        # FastAPI HTTPBearer 无凭证时返回 403
        assert resp.status_code in (401, 403)

    async def test_change_password(self, client: AsyncClient, user_token: str):
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "User@1234", "new_password": "NewPass@5678"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        # 改回来，不影响其他测试
        await client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "NewPass@5678", "new_password": "User@1234"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

    async def test_change_password_wrong_old(self, client: AsyncClient, user_token: str):
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "WrongOld", "new_password": "NewPass@5678"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400


class TestAdminOnly:
    async def test_list_users_as_admin(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_users_as_regular_user(self, client: AsyncClient, user_token: str):
        resp = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_create_user_as_admin(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            "/api/v1/users",
            json={
                "username": "newuser_test",
                "email": "newuser_test@test.com",
                "password": "NewUser@1234",
                "role": "user",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser_test"
