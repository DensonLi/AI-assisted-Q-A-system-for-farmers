from datetime import date, datetime, timezone
from sqlalchemy import Integer, String, Text, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    region_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)
    crop_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crops.id", ondelete="SET NULL"), nullable=True)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    task_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    operation_steps: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
