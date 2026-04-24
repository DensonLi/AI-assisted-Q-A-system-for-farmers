from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.core.deps import CurrentUser, DB
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    AskRequest, AskResponse, ConversationResponse, ConversationDetail
)
from app.services.knowledge import knowledge_service

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: int, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    conv.messages = msg_result.scalars().all()
    return conv


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, current_user: CurrentUser, db: DB):
    # 获取或新建对话
    if payload.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    else:
        title = payload.question[:30] + ("..." if len(payload.question) > 30 else "")
        conv = Conversation(user_id=current_user.id, title=title)
        db.add(conv)
        await db.flush()

    # 加载历史消息（最近10条，避免 token 过多）
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(history_result.scalars().all())
    ]

    # 调用知识库
    answer = await knowledge_service.ask(payload.question, history)

    # 保存问题和回答
    user_msg = Message(conversation_id=conv.id, role="user", content=payload.question)
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=answer)
    db.add(user_msg)
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    return AskResponse(
        conversation_id=conv.id,
        answer=answer,
        message_id=assistant_msg.id,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: int, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    await db.delete(conv)
