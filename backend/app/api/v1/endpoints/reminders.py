"""日历提醒 API。"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentUser, DB
from app.models.reminder import Reminder
from app.models.region import Region
from app.models.crop import Crop

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReminderCreate(BaseModel):
    conversation_id: int | None = None
    region_id: int | None = None
    crop_id: int | None = None
    scheduled_date: date
    title: str
    task_description: str = ""
    operation_steps: str = ""
    key_notes: str = ""


class ReminderBatchCreate(BaseModel):
    items: list[ReminderCreate]


class ReminderDTO(BaseModel):
    id: int
    conversation_id: int | None
    region_id: int | None
    crop_id: int | None
    region_name: str
    crop_name: str
    scheduled_date: date
    title: str
    task_description: str
    operation_steps: str
    key_notes: str
    is_done: bool
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ReminderDTO], summary="查询提醒列表")
async def list_reminders(
    current_user: CurrentUser,
    db: DB,
    year: int | None = None,
    month: int | None = None,
) -> Any:
    stmt = select(Reminder).where(Reminder.user_id == current_user.id)
    if year and month:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        stmt = stmt.where(Reminder.scheduled_date >= start, Reminder.scheduled_date <= end)
    stmt = stmt.order_by(Reminder.scheduled_date)
    result = await db.execute(stmt)
    reminders = result.scalars().all()

    dtos = []
    for r in reminders:
        region_name = ""
        crop_name = ""
        if r.region_id:
            region = await db.get(Region, r.region_id)
            region_name = region.full_name if region else ""
        if r.crop_id:
            crop = await db.get(Crop, r.crop_id)
            crop_name = crop.name if crop else ""
        dtos.append(ReminderDTO(
            id=r.id,
            conversation_id=r.conversation_id,
            region_id=r.region_id,
            crop_id=r.crop_id,
            region_name=region_name,
            crop_name=crop_name,
            scheduled_date=r.scheduled_date,
            title=r.title,
            task_description=r.task_description,
            operation_steps=r.operation_steps,
            key_notes=r.key_notes,
            is_done=r.is_done,
            created_at=r.created_at.isoformat(),
        ))
    return dtos


@router.post("/batch", response_model=list[int], summary="批量创建提醒（用户确认后）")
async def batch_create_reminders(
    body: ReminderBatchCreate,
    current_user: CurrentUser,
    db: DB,
) -> Any:
    ids = []
    for item in body.items:
        r = Reminder(
            user_id=current_user.id,
            conversation_id=item.conversation_id,
            region_id=item.region_id,
            crop_id=item.crop_id,
            scheduled_date=item.scheduled_date,
            title=item.title,
            task_description=item.task_description,
            operation_steps=item.operation_steps,
            key_notes=item.key_notes,
        )
        db.add(r)
        await db.flush()
        ids.append(r.id)
    return ids


@router.patch("/{reminder_id}/done", summary="切换提醒完成状态")
async def toggle_done(
    reminder_id: int,
    current_user: CurrentUser,
    db: DB,
) -> Any:
    r = await db.get(Reminder, reminder_id)
    if not r or r.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提醒不存在")
    r.is_done = not r.is_done
    return {"id": r.id, "is_done": r.is_done}


@router.delete("/{reminder_id}", summary="删除提醒")
async def delete_reminder(
    reminder_id: int,
    current_user: CurrentUser,
    db: DB,
) -> Any:
    r = await db.get(Reminder, reminder_id)
    if not r or r.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提醒不存在")
    await db.delete(r)
    return {"detail": "已删除"}
