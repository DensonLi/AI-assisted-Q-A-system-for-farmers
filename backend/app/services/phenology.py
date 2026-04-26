"""物候期计算服务。"""
from __future__ import annotations

from datetime import date
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crop import PhenologyStage
from app.models.region import Region


async def current_stage(
    db: AsyncSession, region: Region, crop_id: int, today: date | None = None
) -> PhenologyStage | None:
    """根据今日日期，查找 (农业区 × 作物) 匹配的物候期。"""
    if today is None:
        today = date.today()
    if not region.agro_zone:
        return None

    m, d = today.month, today.day

    # 物候期可能跨年（例：10月-次年6月），分两种情况
    stmt = select(PhenologyStage).where(
        PhenologyStage.crop_id == crop_id,
        PhenologyStage.agro_zone == region.agro_zone,
        or_(
            # 同年内：start <= today <= end
            and_(
                PhenologyStage.start_month <= PhenologyStage.end_month,
                or_(
                    PhenologyStage.start_month < m,
                    and_(PhenologyStage.start_month == m, PhenologyStage.start_day <= d),
                ),
                or_(
                    PhenologyStage.end_month > m,
                    and_(PhenologyStage.end_month == m, PhenologyStage.end_day >= d),
                ),
            ),
            # 跨年（例如 10月-6月）
            and_(
                PhenologyStage.start_month > PhenologyStage.end_month,
                or_(
                    or_(
                        PhenologyStage.start_month < m,
                        and_(PhenologyStage.start_month == m, PhenologyStage.start_day <= d),
                    ),
                    or_(
                        PhenologyStage.end_month > m,
                        and_(PhenologyStage.end_month == m, PhenologyStage.end_day >= d),
                    ),
                ),
            ),
        ),
    )
    result = await db.execute(stmt)
    return result.scalars().first()


def format_stage(stage: PhenologyStage | None) -> str:
    if stage is None:
        return "未匹配到物候期"
    if stage.description:
        return f"{stage.stage_name}（{stage.description}）"
    return stage.stage_name
