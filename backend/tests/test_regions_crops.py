"""
区域 & 作物 API 测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region
from app.models.crop import Crop

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seed_region(db_session: AsyncSession) -> Region:
    """创建测试用省级区域"""
    province = Region(
        code="990000", name="测试省", full_name="测试省",
        level=1, agro_zone="黄淮海平原农业区"
    )
    db_session.add(province)
    await db_session.flush()
    await db_session.refresh(province)

    city = Region(
        code="990100", name="测试市", full_name="测试省测试市",
        level=2, parent_id=province.id, agro_zone="黄淮海平原农业区"
    )
    db_session.add(city)
    await db_session.flush()
    await db_session.refresh(city)

    county = Region(
        code="990101", name="测试县", full_name="测试省测试市测试县",
        level=3, parent_id=city.id, agro_zone="黄淮海平原农业区"
    )
    db_session.add(county)
    await db_session.flush()   # 不 commit，由 conftest rollback 清理
    await db_session.refresh(county)
    return county


@pytest.fixture
async def seed_crop(db_session: AsyncSession) -> Crop:
    """创建测试用作物"""
    crop = Crop(
        code="test_wheat", name="测试冬小麦",
        category="grain", description="测试用"
    )
    db_session.add(crop)
    await db_session.flush()   # 不 commit
    await db_session.refresh(crop)
    return crop


class TestRegions:
    async def test_list_provinces(
        self, client: AsyncClient, user_token: str, seed_region: Region
    ):
        resp = await client.get(
            "/api/v1/regions/provinces",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        provinces = resp.json()
        assert isinstance(provinces, list)
        codes = [p["code"] for p in provinces]
        assert "990000" in codes

    async def test_list_children(
        self, client: AsyncClient, user_token: str, seed_region: Region
    ):
        # 先取省 id
        resp = await client.get(
            "/api/v1/regions/provinces",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        province = next(p for p in resp.json() if p["code"] == "990000")
        province_id = province["id"]

        resp = await client.get(
            f"/api/v1/regions/children?parent_id={province_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        children = resp.json()
        assert any(c["code"] == "990100" for c in children)

    async def test_search_region(
        self, client: AsyncClient, user_token: str, seed_region: Region
    ):
        resp = await client.get(
            "/api/v1/regions/search?q=测试县",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert results[0]["code"] == "990101"

    async def test_get_region_by_id(
        self, client: AsyncClient, user_token: str, seed_region: Region
    ):
        resp = await client.get(
            f"/api/v1/regions/{seed_region.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "990101"


class TestCrops:
    async def test_crop_tree(
        self, client: AsyncClient, user_token: str, seed_crop: Crop
    ):
        resp = await client.get(
            "/api/v1/crops/tree",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        tree = resp.json()
        assert isinstance(tree, dict)
        # 应包含 grain 分类
        assert "grain" in tree

    async def test_search_crops(
        self, client: AsyncClient, user_token: str, seed_crop: Crop
    ):
        resp = await client.get(
            "/api/v1/crops/search?q=冬小麦",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert any(c["code"] == "test_wheat" for c in results)

    async def test_phenology_no_region(
        self, client: AsyncClient, user_token: str, seed_crop: Crop
    ):
        resp = await client.get(
            f"/api/v1/crops/{seed_crop.id}/phenology?region_id=9999",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["current_stage"] is None
