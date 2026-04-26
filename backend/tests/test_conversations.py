"""
对话 & 问答 API 测试
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region
from app.models.crop import Crop

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def region_crop(db_session: AsyncSession):
    """为对话测试创建必要的区域和作物"""
    region = Region(
        code="880000", name="对话测试省", full_name="对话测试省",
        level=1, agro_zone="黄淮海平原农业区"
    )
    db_session.add(region)
    await db_session.flush()
    await db_session.refresh(region)

    crop = Crop(
        code="dialog_wheat", name="对话测试小麦",
        category="grain", description="测试用"
    )
    db_session.add(crop)
    await db_session.flush()   # 不 commit，由 conftest rollback 清理
    await db_session.refresh(crop)
    return {"region": region, "crop": crop}


@pytest.fixture
async def conversation(client: AsyncClient, user_token: str, region_crop):
    """创建一个测试对话"""
    region = region_crop["region"]
    crop = region_crop["crop"]
    resp = await client.post(
        "/api/v1/conversations",
        json={
            "region_id": region.id,
            "crop_id": crop.id,
            "title": "测试对话",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestConversations:
    async def test_create_conversation(
        self, client: AsyncClient, user_token: str, region_crop
    ):
        region = region_crop["region"]
        crop = region_crop["crop"]
        resp = await client.post(
            "/api/v1/conversations",
            json={"region_id": region.id, "crop_id": crop.id},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["region_id"] == region.id
        assert data["crop_id"] == crop.id
        assert "对话测试省" in data["title"] or "对话测试小麦" in data["title"]

    async def test_create_conversation_invalid_region(
        self, client: AsyncClient, user_token: str, region_crop
    ):
        crop = region_crop["crop"]
        resp = await client.post(
            "/api/v1/conversations",
            json={"region_id": 999999, "crop_id": crop.id},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400

    async def test_list_conversations(
        self, client: AsyncClient, user_token: str, conversation
    ):
        resp = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert any(c["id"] == conversation["id"] for c in items)

    async def test_get_conversation(
        self, client: AsyncClient, user_token: str, conversation
    ):
        conv_id = conversation["id"]
        resp = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conv_id
        assert "messages" in data

    async def test_get_other_users_conversation(
        self, client: AsyncClient, admin_token: str, conversation
    ):
        """管理员也不能访问别人的对话（业务隔离）"""
        conv_id = conversation["id"]
        resp = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_ask_with_mocked_llm(
        self, client: AsyncClient, user_token: str, conversation
    ):
        """模拟 LLM 返回，测试完整 ask 流程"""
        conv_id = conversation["id"]
        from app.services.llm import LLMResult

        mock_result = LLMResult(
            answer="建议在返青期每亩追施尿素15公斤，结合浇水效果更佳。",
            proposed_memory_items=[],
            used_fallback=False,
        )

        with patch(
            "app.services.orchestrator.llm_client.chat",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.post(
                f"/api/v1/conversations/{conv_id}/ask",
                json={"question": "现在应该施什么肥？"},
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["conversation_id"] == conv_id
        assert "message_id" in data
        assert "建议" in data["answer"]
        assert isinstance(data["proposal_ids"], list)

    async def test_ask_empty_question(
        self, client: AsyncClient, user_token: str, conversation
    ):
        conv_id = conversation["id"]
        resp = await client.post(
            f"/api/v1/conversations/{conv_id}/ask",
            json={"question": ""},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 422

    async def test_delete_conversation(
        self, client: AsyncClient, user_token: str, region_crop
    ):
        region = region_crop["region"]
        crop = region_crop["crop"]
        # 创建临时对话
        create_resp = await client.post(
            "/api/v1/conversations",
            json={"region_id": region.id, "crop_id": crop.id},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        conv_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert del_resp.status_code == 204

        get_resp = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert get_resp.status_code == 404
