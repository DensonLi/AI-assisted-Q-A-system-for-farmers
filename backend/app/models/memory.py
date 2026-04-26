import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class MemorySource(str, enum.Enum):
    USER_CONFIRMED = "user_confirmed"
    AI_INFERRED = "ai_inferred"
    ADMIN_SEED = "admin_seed"


class MemoryStatus(str, enum.Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class ProposalAction(str, enum.Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


class ProposalStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class UserCropMemory(Base):
    """用户 × 区域 × 作物的记忆体"""
    __tablename__ = "user_crop_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    items: Mapped[list["MemoryItem"]] = relationship(
        "MemoryItem", back_populates="memory", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "region_id", "crop_id", name="uq_user_region_crop"),
    )


class MemoryItem(Base):
    """单条记忆条目"""
    __tablename__ = "memory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_crop_memories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default=MemorySource.USER_CONFIRMED.value, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=MemoryStatus.ACTIVE.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    memory: Mapped["UserCropMemory"] = relationship("UserCropMemory", back_populates="items")


class MemoryUpdateProposal(Base):
    """AI 提出的待确认记忆更新"""
    __tablename__ = "memory_update_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_crop_memories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    target_item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("memory_items.id", ondelete="SET NULL"), nullable=True
    )
    proposed_key: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ProposalStatus.PENDING.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
