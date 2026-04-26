from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DB
from app.models.conversation import Conversation, Message
from app.models.crop import Crop
from app.models.region import Region
from app.schemas.conversation import ConversationResponse, ConversationDetail
from app.services.orchestrator import ask as orchestrate_ask

router = APIRouter()


class ConversationCreate(BaseModel):
    region_id: int
    crop_id: int
    title: str | None = None


class AskPayload(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(current_user: CurrentUser, db: DB):
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate, current_user: CurrentUser, db: DB,
):
    region = await db.get(Region, payload.region_id)
    crop = await db.get(Crop, payload.crop_id)
    if not region or not crop:
        raise HTTPException(status_code=400, detail="区域或作物无效")

    title = payload.title or f"{region.name}·{crop.name}"
    conv = Conversation(
        user_id=current_user.id,
        region_id=region.id,
        crop_id=crop.id,
        title=title[:256],
    )
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: int, current_user: CurrentUser, db: DB):
    conv = await _get_user_conversation(db, conversation_id, current_user.id)

    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = list(msg_result.scalars())
    # 返回 dict 避免触发 SQLAlchemy 异步模式下的 lazy-load
    return {
        "id": conv.id,
        "title": conv.title,
        "region_id": conv.region_id,
        "crop_id": conv.crop_id,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": messages,
    }


@router.post("/{conversation_id}/ask")
async def ask(
    conversation_id: int, payload: AskPayload,
    current_user: CurrentUser, db: DB,
):
    conv = await _get_user_conversation(db, conversation_id, current_user.id)
    result = await orchestrate_ask(
        db, user_id=current_user.id, conversation=conv, question=payload.question,
    )
    return {
        "conversation_id": conv.id,
        "message_id": result.message_id,
        "answer": result.answer,
        "phenology_stage": result.phenology_stage,
        "proposal_ids": result.proposal_ids,
        "proposed_reminders": result.proposed_reminders,
        "reminder_summary": result.reminder_summary,
    }


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: int, current_user: CurrentUser, db: DB):
    conv = await _get_user_conversation(db, conversation_id, current_user.id)
    await db.delete(conv)


async def _get_user_conversation(db, conversation_id: int, user_id: int) -> Conversation:
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv
