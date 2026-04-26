"""系统配置服务：从 DB 读取可动态修改的配置，优先级高于 .env。

配置项：
  knowledge_api_base_url / knowledge_api_key / knowledge_bot_id
  llm_api_key / llm_base_url / llm_model
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)

# 配置项元信息：(显示名, 是否敏感, .env 回退值)
CONFIG_META: dict[str, dict[str, Any]] = {
    "knowledge_api_base_url": {
        "label": "知识库 API 地址",
        "secret": False,
        "env_fallback": lambda: settings.KNOWLEDGE_API_BASE_URL,
        "group": "knowledge",
    },
    "knowledge_api_key": {
        "label": "知识库 API Key",
        "secret": True,
        "env_fallback": lambda: settings.KNOWLEDGE_API_KEY,
        "group": "knowledge",
    },
    "knowledge_bot_id": {
        "label": "知识库 Bot ID",
        "secret": False,
        "env_fallback": lambda: settings.KNOWLEDGE_BOT_ID,
        "group": "knowledge",
    },
    "llm_api_key": {
        "label": "LLM API Key",
        "secret": True,
        "env_fallback": lambda: settings.LLM_API_KEY,
        "group": "llm",
    },
    "llm_base_url": {
        "label": "LLM Base URL",
        "secret": False,
        "env_fallback": lambda: settings.LLM_BASE_URL,
        "group": "llm",
    },
    "llm_model": {
        "label": "LLM 模型",
        "secret": False,
        "env_fallback": lambda: settings.LLM_MODEL,
        "group": "llm",
    },
}


async def get_all(db: AsyncSession) -> dict[str, str]:
    """读取所有配置，DB 值优先，空则回退到 .env。"""
    result = await db.execute(select(SystemConfig))
    rows = {row.key: row.value for row in result.scalars().all()}

    out: dict[str, str] = {}
    for key, meta in CONFIG_META.items():
        db_val = rows.get(key, "").strip()
        out[key] = db_val if db_val else meta["env_fallback"]()
    return out


async def get_value(db: AsyncSession, key: str) -> str:
    """获取单个配置值（DB 优先，回退 .env）。"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    if row and row.value.strip():
        return row.value.strip()
    meta = CONFIG_META.get(key)
    if meta:
        return meta["env_fallback"]()
    return ""


async def set_values(db: AsyncSession, updates: dict[str, str]) -> None:
    """批量更新配置（仅允许已知 key）。"""
    for key, value in updates.items():
        if key not in CONFIG_META:
            continue
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        row = result.scalar_one_or_none()
        if row:
            await db.execute(
                update(SystemConfig)
                .where(SystemConfig.key == key)
                .values(value=value)
            )
        else:
            db.add(SystemConfig(key=key, value=value,
                                description=CONFIG_META[key]["label"]))
    await db.flush()
