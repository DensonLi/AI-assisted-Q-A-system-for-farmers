from sqlalchemy import String, Integer, SmallInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Region(Base):
    """行政区域（省/市/县三级）"""
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1=省 2=市 3=县
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agro_zone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    children: Mapped[list["Region"]] = relationship(
        "Region", backref="parent", remote_side="Region.id",
    )

    __table_args__ = (
        Index("ix_regions_level_parent", "level", "parent_id"),
    )
