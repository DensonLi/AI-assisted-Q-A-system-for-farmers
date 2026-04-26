from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.deps import CurrentUser, DB
from app.models.memory import (
    UserCropMemory, MemoryItem, MemoryUpdateProposal,
    MemoryStatus, ProposalStatus,
)
from app.services import memory as memory_svc

router = APIRouter()


class MemoryItemUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=500)


class MemoryItemCreate(BaseModel):
    region_id: int
    crop_id: int
    key: str = Field(..., max_length=64)
    value: str = Field(..., min_length=1, max_length=500)


@router.get("")
async def list_memories(
    region_id: int, crop_id: int, current_user: CurrentUser, db: DB,
):
    """按 (区域, 作物) 返回该用户的记忆条目。"""
    stmt = select(UserCropMemory).where(
        UserCropMemory.user_id == current_user.id,
        UserCropMemory.region_id == region_id,
        UserCropMemory.crop_id == crop_id,
    )
    result = await db.execute(stmt)
    mem = result.scalar_one_or_none()
    if not mem:
        return {"memory_id": None, "items": []}

    items = await memory_svc.list_active_items(db, mem.id)
    return {
        "memory_id": mem.id,
        "items": [
            {
                "id": i.id, "key": i.key, "value": i.value,
                "confidence": i.confidence, "source": i.source,
                "created_at": i.created_at, "updated_at": i.updated_at,
            } for i in items
        ],
    }


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(payload: MemoryItemCreate, current_user: CurrentUser, db: DB):
    mem = await memory_svc.get_or_create_memory(
        db, current_user.id, payload.region_id, payload.crop_id
    )
    item = MemoryItem(
        memory_id=mem.id,
        key=payload.key,
        value=payload.value,
        source="user_confirmed",
        status=MemoryStatus.ACTIVE.value,
    )
    db.add(item)
    await db.flush()
    return {"id": item.id, "key": item.key, "value": item.value}


@router.put("/items/{item_id}")
async def update_item(item_id: int, payload: MemoryItemUpdate, current_user: CurrentUser, db: DB):
    item = await db.get(MemoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记忆条目不存在")
    mem = await db.get(UserCropMemory, item.memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此条目")
    item.value = payload.value
    db.add(item)
    return {"id": item.id, "value": item.value}


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int, current_user: CurrentUser, db: DB):
    item = await db.get(MemoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记忆条目不存在")
    mem = await db.get(UserCropMemory, item.memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此条目")
    item.status = MemoryStatus.DELETED.value
    db.add(item)


@router.get("/proposals")
async def list_proposals(
    current_user: CurrentUser, db: DB,
    conversation_id: int | None = None,
    status_filter: str = ProposalStatus.PENDING.value,
):
    """列出待确认的记忆提案。"""
    stmt = (
        select(MemoryUpdateProposal, UserCropMemory)
        .join(UserCropMemory, MemoryUpdateProposal.memory_id == UserCropMemory.id)
        .where(UserCropMemory.user_id == current_user.id)
        .where(MemoryUpdateProposal.status == status_filter)
    )
    if conversation_id is not None:
        stmt = stmt.where(MemoryUpdateProposal.conversation_id == conversation_id)
    stmt = stmt.order_by(MemoryUpdateProposal.created_at.desc()).limit(50)

    result = await db.execute(stmt)
    out = []
    for proposal, _mem in result.all():
        existing_value = None
        if proposal.target_item_id:
            old = await db.get(MemoryItem, proposal.target_item_id)
            existing_value = old.value if old else None
        out.append({
            "id": proposal.id,
            "memory_id": proposal.memory_id,
            "action": proposal.action,
            "key": proposal.proposed_key,
            "proposed_value": proposal.proposed_value,
            "existing_value": existing_value,
            "confidence": proposal.confidence,
            "reason": proposal.reason,
            "created_at": proposal.created_at,
        })
    return out


@router.post("/proposals/{proposal_id}/accept")
async def accept(proposal_id: int, current_user: CurrentUser, db: DB):
    proposal = await db.get(MemoryUpdateProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="提案不存在")
    mem = await db.get(UserCropMemory, proposal.memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权处理此提案")
    item = await memory_svc.accept_proposal(db, proposal)
    return {"accepted": True, "item_id": item.id}


@router.post("/proposals/{proposal_id}/reject")
async def reject(proposal_id: int, current_user: CurrentUser, db: DB):
    proposal = await db.get(MemoryUpdateProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="提案不存在")
    mem = await db.get(UserCropMemory, proposal.memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权处理此提案")
    await memory_svc.reject_proposal(db, proposal)
    return {"rejected": True}
