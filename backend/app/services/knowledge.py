"""知识库客户端：对接 ziiku.cn RAG 问答 API，非流式调用，失败降级为空结果。

接口地址：POST {KNOWLEDGE_API_BASE_URL}
认证方式：请求头 x-api-key: {KNOWLEDGE_API_KEY}
必填参数：query（问题）、bot_id（机器人ID）
非流式响应：
  {"success": true, "data": {"content": "...", "message_id": "...", "conversation_id": "..."}}
"""
from __future__ import annotations

import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# 知识库回答内容截取上限（字符），避免过长占用 LLM context window
_SNIPPET_MAX_CHARS = 1200


class KnowledgeService:
    """调用 ziiku.cn RAG 知识库获取参考内容，供 LLM 进行二次综合。

    失败时静默降级返回 []，不阻断主问答流程。
    """

    # ── 公开接口 ────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        crop_code: str | None = None,
        region_agro_zone: str | None = None,
        cfg: dict | None = None,          # 运行时配置覆盖（来自 DB system_configs）
    ) -> list[dict]:
        """查询知识库，返回 [{"title", "snippet", "source", "url", "score"}]。

        crop_code / region_agro_zone 用于丰富查询上下文，提升知识库召回相关度。
        cfg 若提供，优先使用其中的 knowledge_* 配置（来自数据库）。
        """
        cfg = cfg or {}
        base_url = (cfg.get("knowledge_api_base_url") or settings.KNOWLEDGE_API_BASE_URL).strip()
        api_key = (cfg.get("knowledge_api_key") or settings.KNOWLEDGE_API_KEY).strip()
        bot_id = (cfg.get("knowledge_bot_id") or settings.KNOWLEDGE_BOT_ID).strip()

        if not base_url or not api_key or not bot_id:
            # 未配置时静默跳过，LLM 仍可基于记忆和物候期作答
            return []

        enriched_query = self._enrich_query(query, crop_code, region_agro_zone)

        payload = {
            "query": enriched_query,
            "bot_id": bot_id,
            # 每次问答生成新 user_id，避免跨用户/跨会话串流
            "user_id": str(uuid.uuid4()),
            "stream": False,
            "source_document": False,   # 不要求来源文档，减少响应体积
            "use_ai_answer": 1,         # 1 = AI 优选（知识库 + AI 综合）
        }

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.KNOWLEDGE_TIMEOUT_SEC) as client:
                resp = await client.post(base_url, json=payload, headers=headers)
                resp.raise_for_status()
                return self._parse_response(resp.json())
        except httpx.TimeoutException:
            logger.warning("知识库请求超时 (query=%r)", query[:60])
            return []
        except httpx.HTTPStatusError as e:
            logger.warning("知识库 HTTP 错误: %s %s", e.response.status_code, e.response.text[:200])
            return []
        except Exception as e:
            logger.warning("知识库检索失败: %s", e)
            return []

    # ── 私有方法 ─────────────────────────────────────────────────────────

    @staticmethod
    def _enrich_query(
        query: str,
        crop_code: str | None,
        region_agro_zone: str | None,
    ) -> str:
        """在查询中附加作物/农区背景，提升知识库检索相关性。

        示例：
          "小麦什么时候浇返青水？（背景：农业区：黄淮海平原，作物：wheat_winter）"
        """
        parts: list[str] = []
        if region_agro_zone:
            parts.append(f"农业区：{region_agro_zone}")
        if crop_code:
            parts.append(f"作物：{crop_code}")
        if parts:
            return f"{query}（背景：{'，'.join(parts)}）"
        return query

    @staticmethod
    def _parse_response(data: dict) -> list[dict]:
        """将 ziiku.cn 响应解析为通用片段格式。

        仅当 success=true 且 data.content 不为空时返回结果。
        """
        if not data.get("success"):
            logger.warning("知识库返回 success=false: %s", data.get("error", ""))
            return []

        content: str = ((data.get("data") or {}).get("content") or "").strip()
        if not content:
            return []

        # 截断过长内容，避免占满 LLM context window
        if len(content) > _SNIPPET_MAX_CHARS:
            content = content[:_SNIPPET_MAX_CHARS] + "……（内容截断）"

        return [
            {
                "title": "农业知识库",
                "snippet": content,
                "source": "ziiku.cn",
                "url": "",
                "score": 1.0,
            }
        ]


knowledge_service = KnowledgeService()
