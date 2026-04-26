from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from app.core.deps import CurrentUser, DB
from app.models.region import Region

router = APIRouter()


@router.get("/provinces")
async def list_provinces(db: DB, _: CurrentUser):
    stmt = select(Region).where(Region.level == 1).order_by(Region.code)
    result = await db.execute(stmt)
    return [_region_to_dict(r) for r in result.scalars()]


@router.get("/children")
async def list_children(parent_id: int, db: DB, _: CurrentUser):
    stmt = select(Region).where(Region.parent_id == parent_id).order_by(Region.code)
    result = await db.execute(stmt)
    return [_region_to_dict(r) for r in result.scalars()]


@router.get("/search")
async def search_regions(
    q: str = Query(..., min_length=1, max_length=32),
    db: DB = None, _: CurrentUser = None,
):
    pattern = f"%{q}%"
    stmt = (
        select(Region)
        .where(or_(Region.name.ilike(pattern), Region.full_name.ilike(pattern)))
        .where(Region.level == 3)
        .limit(20)
    )
    result = await db.execute(stmt)
    return [_region_to_dict(r) for r in result.scalars()]


@router.get("/{region_id}")
async def get_region(region_id: int, db: DB, _: CurrentUser):
    region = await db.get(Region, region_id)
    if not region:
        return {}
    return _region_to_dict(region)


def _region_to_dict(r: Region) -> dict:
    return {
        "id": r.id,
        "code": r.code,
        "name": r.name,
        "full_name": r.full_name,
        "level": r.level,
        "parent_id": r.parent_id,
        "agro_zone": r.agro_zone,
    }
