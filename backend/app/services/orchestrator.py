"""问答编排：拉取上下文 → 调用知识库 + LLM → 生成回答 → 创建记忆提案。"""
from __future__ import annotations

from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, Message
from app.models.crop import Crop
from app.models.region import Region
from app.services.knowledge import knowledge_service
from app.services.llm import llm_client
from app.services import memory as memory_svc
from app.services import phenology
from app.services import system_config as sys_cfg_svc


@dataclass
class AskResult:
    answer: str
    message_id: int
    proposal_ids: list[int] = field(default_factory=list)
    phenology_stage: str = ""
    proposed_reminders: list[dict] = field(default_factory=list)
    reminder_summary: str = ""


async def ask(
    db: AsyncSession,
    *,
    user_id: int,
    conversation: Conversation,
    question: str,
) -> AskResult:
    """完整问答流程。调用方负责事务提交。"""

    # 1. 加载区域/作物
    region = await db.get(Region, conversation.region_id) if conversation.region_id else None
    crop = await db.get(Crop, conversation.crop_id) if conversation.crop_id else None

    region_name = region.full_name if region else "未指定区域"
    crop_name = crop.name if crop else "未指定作物"

    # 2. 物候期
    stage_obj = None
    if region and crop:
        stage_obj = await phenology.current_stage(db, region, crop.id)
    stage_desc = phenology.format_stage(stage_obj)

    # 3. 长期记忆
    memory_items: list[dict] = []
    memory_id: int | None = None
    if region and crop:
        mem = await memory_svc.get_or_create_memory(db, user_id, region.id, crop.id)
        memory_id = mem.id
        memory_items = await memory_svc.items_as_dict(db, mem.id)

    # 4. 从 DB 获取运行时配置（覆盖 .env）
    runtime_cfg = await sys_cfg_svc.get_all(db)

    # 5. 知识库检索
    snippets = await knowledge_service.search(
        question,
        crop_code=crop.code if crop else None,
        region_agro_zone=region.agro_zone if region else None,
        cfg=runtime_cfg,
    )

    # 6. 历史对话
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(settings.LLM_HISTORY_TURNS * 2)
    )
    history_result = await db.execute(history_stmt)
    history_msgs = list(reversed(history_result.scalars().all()))
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    # 7. 调用 LLM
    llm_result = await llm_client.chat(
        question=question,
        region_full_name=region_name,
        crop_name=crop_name,
        phenology_desc=stage_desc,
        memory_items=memory_items,
        knowledge_snippets=snippets,
        history=history,
        cfg=runtime_cfg,
    )

    # 8. 保存消息
    user_msg = Message(conversation_id=conversation.id, role="user", content=question)
    assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=llm_result.answer)
    db.add_all([user_msg, assistant_msg])
    await db.flush()

    # 9. 写入记忆提案
    proposal_ids: list[int] = []
    if memory_id and llm_result.proposed_memory_items:
        proposals = await memory_svc.create_proposals(
            db,
            memory_id=memory_id,
            conversation_id=conversation.id,
            candidates=llm_result.proposed_memory_items,
        )
        proposal_ids = [p.id for p in proposals]

    # 提醒候选附带 region/crop 信息供前端展示，不写入 DB（等用户确认）
    proposed_reminders = []
    for item in llm_result.proposed_reminders:
        proposed_reminders.append({
            **item,
            "region_id": region.id if region else None,
            "crop_id": crop.id if crop else None,
            "conversation_id": conversation.id,
        })

    return AskResult(
        answer=llm_result.answer,
        message_id=assistant_msg.id,
        proposal_ids=proposal_ids,
        phenology_stage=stage_desc,
        proposed_reminders=proposed_reminders,
        reminder_summary=llm_result.reminder_summary,
    )
