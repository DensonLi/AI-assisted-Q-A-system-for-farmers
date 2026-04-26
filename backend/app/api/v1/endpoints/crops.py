from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from app.core.deps import CurrentUser, DB
from app.models.crop import Crop, PhenologyStage
from app.models.region import Region
from app.services import phenology as phenology_svc

router = APIRouter()


@router.get("/tree")
async def crop_tree(db: DB, _: CurrentUser):
    """按分类返回作物列表（前端侧做分组展示）。"""
    stmt = select(Crop).order_by(Crop.category, Crop.code)
    result = await db.execute(stmt)
    crops = list(result.scalars())

    groups: dict[str, list[dict]] = {}
    for c in crops:
        groups.setdefault(c.category, []).append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "category": c.category,
            "description": c.description,
        })
    return groups


@router.get("/popular")
async def popular_crops(db: DB, _: CurrentUser):
    """常用作物（写死 8 种最常见）。"""
    codes = ["maize_summer", "rice_mid", "wheat_winter", "cotton",
             "tomato", "cucumber", "apple", "potato"]
    stmt = select(Crop).where(Crop.code.in_(codes))
    result = await db.execute(stmt)
    crops = list(result.scalars())
    order = {c: i for i, c in enumerate(codes)}
    crops.sort(key=lambda c: order.get(c.code, 999))
    return [{"id": c.id, "code": c.code, "name": c.name, "category": c.category} for c in crops]


@router.get("/search")
async def search_crops(
    q: str = Query(..., min_length=1, max_length=32),
    db: DB = None, _: CurrentUser = None,
):
    pattern = f"%{q}%"
    stmt = select(Crop).where(or_(Crop.name.ilike(pattern), Crop.code.ilike(pattern))).limit(20)
    result = await db.execute(stmt)
    return [{"id": c.id, "code": c.code, "name": c.name, "category": c.category}
            for c in result.scalars()]


@router.get("/{crop_id}/phenology")
async def phenology_for_region(
    crop_id: int, region_id: int, db: DB, _: CurrentUser,
):
    region = await db.get(Region, region_id)
    if not region:
        return {"current_stage": None}
    stage = await phenology_svc.current_stage(db, region, crop_id)
    if stage is None:
        return {"current_stage": None}
    return {
        "current_stage": {
            "stage_name": stage.stage_name,
            "description": stage.description,
            "key_activities": stage.key_activities or [],
        }
    }
