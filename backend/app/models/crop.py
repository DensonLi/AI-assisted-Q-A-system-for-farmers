import enum
from sqlalchemy import String, Integer, SmallInteger, Text, ForeignKey
from app.db.types import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CropCategory(str, enum.Enum):
    GRAIN = "GRAIN"         # 粮食
    OIL = "OIL"             # 油料
    VEGETABLE = "VEGETABLE" # 蔬菜
    FRUIT = "FRUIT"         # 水果
    HERB = "HERB"           # 中药材
    CASH = "CASH"           # 经济作物（棉、糖、烟、茶）
    OTHER = "OTHER"


class Crop(Base):
    """作物分类"""
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("crops.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # ["玉米","苞谷"]


class PhenologyStage(Base):
    """物候期：按(农业区 × 作物 × 日期范围)"""
    __tablename__ = "phenology_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agro_zone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_day: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    end_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    end_day: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=31)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_activities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
