"""用户记忆管理：获取、提案生成、接受/拒绝。"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import (
    UserCropMemory, MemoryItem, MemoryUpdateProposal,
    MemorySource, MemoryStatus, ProposalAction, ProposalStatus,
)


async def get_or_create_memory(
    db: AsyncSession, user_id: int, region_id: int, crop_id: int
) -> UserCropMemory:
    stmt = select(UserCropMemory).where(
        UserCropMemory.user_id == user_id,
        UserCropMemory.region_id == region_id,
        UserCropMemory.crop_id == crop_id,
    )
    result = await db.execute(stmt)
    memory = result.scalar_one_or_none()
    if memory:
        return memory
    memory = UserCropMemory(user_id=user_id, region_id=region_id, crop_id=crop_id)
    db.add(memory)
    await db.flush()
    return memory


async def list_active_items(db: AsyncSession, memory_id: int) -> list[MemoryItem]:
    stmt = select(MemoryItem).where(
        MemoryItem.memory_id == memory_id,
        MemoryItem.status == MemoryStatus.ACTIVE.value,
    ).order_by(MemoryItem.key, MemoryItem.updated_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars())


async def items_as_dict(db: AsyncSession, memory_id: int) -> list[dict]:
    items = await list_active_items(db, memory_id)
    return [{"key": i.key, "value": i.value, "confidence": i.confidence} for i in items]


async def create_proposals(
    db: AsyncSession,
    *,
    memory_id: int,
    conversation_id: int | None,
    candidates: list[dict],
) -> list[MemoryUpdateProposal]:
    """把 LLM 抽取出的候选写入 pending 队列。"""
    active_items = await list_active_items(db, memory_id)
    by_key: dict[str, MemoryItem] = {it.key: it for it in active_items}

    proposals: list[MemoryUpdateProposal] = []
    for c in candidates:
        key = c.get("key")
        value = (c.get("value") or "").strip()
        if not key or not value:
            continue
        action = c.get("action", "add")
        existing = by_key.get(key)

        # 若值与现有记忆完全相同，跳过
        if existing and existing.value.strip() == value:
            continue

        # 去重：同 key 相同 value 的 pending 已存在则跳过
        dup = await db.execute(
            select(MemoryUpdateProposal).where(
                MemoryUpdateProposal.memory_id == memory_id,
                MemoryUpdateProposal.proposed_key == key,
                MemoryUpdateProposal.proposed_value == value,
                MemoryUpdateProposal.status == ProposalStatus.PENDING.value,
            )
        )
        if dup.scalars().first():
            continue

        proposal = MemoryUpdateProposal(
            memory_id=memory_id,
            conversation_id=conversation_id,
            action=ProposalAction.UPDATE.value if existing else ProposalAction.ADD.value,
            target_item_id=existing.id if existing else None,
            proposed_key=key,
            proposed_value=value,
            confidence=float(c.get("confidence", 0.7)),
            reason=c.get("reason"),
        )
        db.add(proposal)
        proposals.append(proposal)
    await db.flush()
    return proposals


async def accept_proposal(db: AsyncSession, proposal: MemoryUpdateProposal) -> MemoryItem:
    """接受提案：更新/新增条目，旧条目置为 superseded。"""
    if proposal.status != ProposalStatus.PENDING.value:
        raise ValueError("该提案已被处理")

    # 若是 UPDATE，将原条目置为 superseded
    if proposal.action == ProposalAction.UPDATE.value and proposal.target_item_id:
        old = await db.get(MemoryItem, proposal.target_item_id)
        if old:
            old.status = MemoryStatus.SUPERSEDED.value
            db.add(old)

    new_item = MemoryItem(
        memory_id=proposal.memory_id,
        key=proposal.proposed_key,
        value=proposal.proposed_value,
        confidence=proposal.confidence,
        source=MemorySource.USER_CONFIRMED.value,
        status=MemoryStatus.ACTIVE.value,
    )
    db.add(new_item)

    proposal.status = ProposalStatus.ACCEPTED.value
    proposal.resolved_at = datetime.now(timezone.utc)
    db.add(proposal)
    await db.flush()
    return new_item


async def reject_proposal(db: AsyncSession, proposal: MemoryUpdateProposal) -> None:
    proposal.status = ProposalStatus.REJECTED.value
    proposal.resolved_at = datetime.now(timezone.utc)
    db.add(proposal)
    await db.flush()
