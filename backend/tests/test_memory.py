"""
记忆管理 API 测试
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region
from app.models.crop import Crop
from app.models.memory import UserCropMemory, MemoryItem, MemoryStatus

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def memory_context(db_session: AsyncSession, user_token: str, client: AsyncClient):
    """创建区域、作物、用户记忆容器"""
    region = Region(
        code="770000", name="记忆测试省", full_name="记忆测试省",
        level=1, agro_zone="长江中下游水稻小麦区"
    )
    db_session.add(region)
    await db_session.flush()
    await db_session.refresh(region)

    crop = Crop(
        code="memory_rice", name="记忆测试水稻", category="grain"
    )
    db_session.add(crop)
    await db_session.flush()   # 不 commit，由 conftest rollback 清理
    await db_session.refresh(crop)

    # 通过 API 获取当前用户 ID
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    user_id = me_resp.json()["id"]

    return {"region": region, "crop": crop, "user_id": user_id}


class TestMemoryItems:
    async def test_list_memories_empty(
        self, client: AsyncClient, user_token: str, memory_context
    ):
        region = memory_context["region"]
        crop = memory_context["crop"]
        resp = await client.get(
            f"/api/v1/memories?region_id={region.id}&crop_id={crop.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_create_memory_item(
        self, client: AsyncClient, user_token: str, memory_context
    ):
        region = memory_context["region"]
        crop = memory_context["crop"]
        resp = await client.post(
            "/api/v1/memories/items",
            json={
                "region_id": region.id,
                "crop_id": crop.id,
                "key": "field_size",
                "value": "约25亩，砂壤土",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"] == "field_size"
        assert "25亩" in data["value"]

    async def test_list_memories_after_create(
        self, client: AsyncClient, user_token: str, memory_context
    ):
        region = memory_context["region"]
        crop = memory_context["crop"]

        # 创建
        await client.post(
            "/api/v1/memories/items",
            json={
                "region_id": region.id, "crop_id": crop.id,
                "key": "irrigation", "value": "漫灌为主",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        # 查询
        resp = await client.get(
            f"/api/v1/memories?region_id={region.id}&crop_id={crop.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(i["key"] == "irrigation" for i in items)

    async def test_update_memory_item(
        self, client: AsyncClient, user_token: str, memory_context
    ):
        region = memory_context["region"]
        crop = memory_context["crop"]

        create_resp = await client.post(
            "/api/v1/memories/items",
            json={
                "region_id": region.id, "crop_id": crop.id,
                "key": "soil_type", "value": "黏土",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/v1/memories/items/{item_id}",
            json={"value": "砂壤土（已更正）"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert update_resp.status_code == 200
        assert "砂壤土" in update_resp.json()["value"]

    async def test_delete_memory_item(
        self, client: AsyncClient, user_token: str, memory_context
    ):
        region = memory_context["region"]
        crop = memory_context["crop"]

        create_resp = await client.post(
            "/api/v1/memories/items",
            json={
                "region_id": region.id, "crop_id": crop.id,
                "key": "to_be_deleted", "value": "临时值",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/memories/items/{item_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert del_resp.status_code == 204

        # 确认不再出现在列表中（已软删除）
        list_resp = await client.get(
            f"/api/v1/memories?region_id={region.id}&crop_id={crop.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        items = list_resp.json()["items"]
        assert not any(i["id"] == item_id for i in items)

    async def test_update_other_users_item_forbidden(
        self, client: AsyncClient, admin_token: str, user_token: str, memory_context
    ):
        region = memory_context["region"]
        crop = memory_context["crop"]

        # 普通用户创建
        create_resp = await client.post(
            "/api/v1/memories/items",
            json={
                "region_id": region.id, "crop_id": crop.id,
                "key": "private_key", "value": "私有值",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = create_resp.json()["id"]

        # 管理员尝试修改
        update_resp = await client.put(
            f"/api/v1/memories/items/{item_id}",
            json={"value": "管理员篡改"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert update_resp.status_code == 403


class TestMemoryServices:
    """测试记忆服务层核心逻辑"""

    async def test_get_or_create_memory(self, db_session: AsyncSession, memory_context):
        from app.services import memory as mem_svc

        region = memory_context["region"]
        crop = memory_context["crop"]
        user_id = memory_context["user_id"]

        mem1 = await mem_svc.get_or_create_memory(db_session, user_id, region.id, crop.id)
        mem2 = await mem_svc.get_or_create_memory(db_session, user_id, region.id, crop.id)

        assert mem1.id == mem2.id  # 幂等，不重复创建

    async def test_accept_proposal_creates_item(
        self, db_session: AsyncSession, memory_context
    ):
        from app.services import memory as mem_svc
        from app.models.memory import MemoryUpdateProposal, ProposalStatus

        region = memory_context["region"]
        crop = memory_context["crop"]
        user_id = memory_context["user_id"]

        mem = await mem_svc.get_or_create_memory(db_session, user_id, region.id, crop.id)

        proposals = await mem_svc.create_proposals(
            db_session,
            memory_id=mem.id,
            conversation_id=None,
            candidates=[{
                "action": "add",
                "key": "last_pest",
                "value": "2025年6月发生蚜虫",
                "confidence": 0.85,
                "reason": "用户主动提及",
            }],
        )
        assert len(proposals) == 1

        item = await mem_svc.accept_proposal(db_session, proposals[0])
        assert item.key == "last_pest"
        assert item.status == MemoryStatus.ACTIVE.value

        # 检查提案状态已更新
        await db_session.refresh(proposals[0])
        assert proposals[0].status == ProposalStatus.ACCEPTED.value

    async def test_reject_proposal(
        self, db_session: AsyncSession, memory_context
    ):
        from app.services import memory as mem_svc
        from app.models.memory import ProposalStatus

        region = memory_context["region"]
        crop = memory_context["crop"]
        user_id = memory_context["user_id"]

        mem = await mem_svc.get_or_create_memory(db_session, user_id, region.id, crop.id)
        proposals = await mem_svc.create_proposals(
            db_session,
            memory_id=mem.id,
            conversation_id=None,
            candidates=[{
                "action": "add",
                "key": "reject_test",
                "value": "应被拒绝的值",
                "confidence": 0.7,
                "reason": None,
            }],
        )

        await mem_svc.reject_proposal(db_session, proposals[0])
        await db_session.refresh(proposals[0])
        assert proposals[0].status == ProposalStatus.REJECTED.value
