"""系统配置 API（仅管理员可访问）。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.user import User, UserRole
from app.services import system_config as svc

router = APIRouter()


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可操作")
    return current_user


class ConfigItem(BaseModel):
    key: str
    label: str
    group: str
    secret: bool
    value: str          # 敏感项返回掩码


class ConfigListResponse(BaseModel):
    items: list[ConfigItem]


class ConfigUpdateRequest(BaseModel):
    updates: dict[str, str]   # key -> 新值（敏感项传空字符串表示不修改）


@router.get("", response_model=ConfigListResponse, summary="获取系统配置")
async def list_configs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
) -> Any:
    values = await svc.get_all(db)
    items: list[ConfigItem] = []
    for key, meta in svc.CONFIG_META.items():
        raw = values.get(key, "")
        display = _mask(raw) if meta["secret"] else raw
        items.append(ConfigItem(
            key=key,
            label=meta["label"],
            group=meta["group"],
            secret=meta["secret"],
            value=display,
        ))
    return ConfigListResponse(items=items)


@router.put("", summary="更新系统配置")
async def update_configs(
    body: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
) -> Any:
    # 过滤掉敏感项中值为掩码（未修改）的条目
    filtered: dict[str, str] = {}
    for key, val in body.updates.items():
        meta = svc.CONFIG_META.get(key)
        if not meta:
            continue
        if meta["secret"] and _is_masked(val):
            continue           # 掩码值 → 用户未改，跳过
        filtered[key] = val.strip()

    await svc.set_values(db, filtered)
    return {"detail": "保存成功"}


def _mask(value: str) -> str:
    """将敏感值掩码显示：保留前4后4，中间替换为 *。"""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def _is_masked(value: str) -> bool:
    """判断值是否为掩码（含 * 且长度与掩码规则一致）。"""
    return "*" in value
