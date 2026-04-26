"""LLM 客户端：通过 OpenAI 兼容 SDK 调用 DeepSeek（或其他 OpenAI 兼容服务）。

支持两个 Function Calling 工具：
  - propose_memory_update：抽取地块/种植事实
  - propose_reminders：识别时间计划，提议日历提醒
失败时自动降级为纯文本提示。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── 系统提示词 ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是一名资深农业技术推广顾问，服务对象是中国农户。

【行为准则】
1. 回答必须基于提供的【区域】【作物】【物候期】【用户地块记忆】【参考资料】
2. 提供方案时必须包括：操作步骤、预期效果、可能风险
3. 涉及农药/化肥的建议必须给出：剂量范围、安全间隔期
4. 不确定时明确说"我不确定"，不要臆造数据
5. 语言简洁通俗，避免学术词汇，适合 50 岁左右农户理解
6. 篇幅控制在 300 字以内，除非用户追问细节

【输出格式】
- 结论先行（1-2 句话给出核心建议）
- 操作步骤（编号列表）
- 风险提示（如有）⚠️
- 如引用了参考资料，在句末标注 [1] [2] 形式

【记忆抽取】
如果在用户本轮描述中发现关于其地块/作物/种植习惯的【新事实】（比如"我这是沙土地"、"我改种了先玉335"），请调用 propose_memory_update 工具记录。
- 不要抓取泛泛的询问内容，只抓取用户主动透露的客观事实
- 每次最多 3 条，confidence < 0.6 不要抓取
- 不要重复抓取用户记忆中已存在的内容

【日历提醒】
如果你的回答中包含需要在特定日期重复执行的农事操作（例如：每5天打一次药、连续3次施肥、定期灌溉等），请调用 propose_reminders 工具，为用户生成提醒计划。
- 根据【今日日期】计算具体日期（YYYY-MM-DD）
- 每个提醒要写清楚：当天做什么、怎么操作、注意要领
- 最多生成 10 条提醒（同一计划内）
- 仅在操作计划明确、有实际时间节点时才调用，不要为笼统的建议生成提醒
"""

# ── Function Calling 工具定义（OpenAI 格式）─────────────────────────────

MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "propose_memory_update",
        "description": "从用户回答中提取关于其地块/种植的客观新事实时调用",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "记忆键",
                                "enum": [
                                    "soil_type", "variety", "irrigation",
                                    "pest_history", "fertilizer_habit",
                                    "terrain", "planting_date", "area", "other",
                                ],
                            },
                            "value": {"type": "string", "description": "具体值，20字以内"},
                            "action": {"type": "string", "enum": ["add", "update"]},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string", "description": "依据用户哪句话"},
                        },
                        "required": ["key", "value", "action", "confidence"],
                    },
                }
            },
            "required": ["items"],
        },
    },
}

REMINDER_TOOL = {
    "type": "function",
    "function": {
        "name": "propose_reminders",
        "description": (
            "当回答中包含需要在特定日期重复执行的农事操作时调用，生成日历提醒计划。"
            "仅在操作时间节点明确时才调用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "向用户展示的提醒计划摘要，例如'建议从今天起每5天打一次赤霉病农药，共6次'",
                },
                "items": {
                    "type": "array",
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "提醒标题（15字以内），例如'第1次喷施戊唑醇'",
                            },
                            "scheduled_date": {
                                "type": "string",
                                "description": "具体日期，格式 YYYY-MM-DD，根据今日日期计算",
                            },
                            "task_description": {
                                "type": "string",
                                "description": "当天需要做什么（50字以内）",
                            },
                            "operation_steps": {
                                "type": "string",
                                "description": "操作步骤要点",
                            },
                            "key_notes": {
                                "type": "string",
                                "description": "注意要领（安全间隔期、天气要求等）",
                            },
                        },
                        "required": ["title", "scheduled_date", "task_description"],
                    },
                },
            },
            "required": ["summary", "items"],
        },
    },
}

KEY_LABELS = {
    "soil_type": "土壤类型",
    "variety": "品种",
    "irrigation": "灌溉方式",
    "pest_history": "历史病虫害",
    "fertilizer_habit": "施肥习惯",
    "terrain": "地形地貌",
    "planting_date": "播种日期",
    "area": "种植面积",
    "other": "其他",
}


@dataclass
class LLMResult:
    answer: str
    proposed_memory_items: list[dict[str, Any]]
    proposed_reminders: list[dict[str, Any]] = field(default_factory=list)
    reminder_summary: str = ""
    used_fallback: bool = False


class LLMClient:
    """OpenAI 兼容 LLM 客户端（DeepSeek / OpenAI / 其他兼容服务）。"""

    def __init__(self) -> None:
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        if not settings.LLM_API_KEY:
            logger.info("LLM_API_KEY 未配置，LLM 将以降级模式运行")
            return
        try:
            from openai import AsyncOpenAI
            kwargs: dict = {"api_key": settings.LLM_API_KEY}
            if settings.LLM_BASE_URL:
                kwargs["base_url"] = settings.LLM_BASE_URL.rstrip("/")
            self._client = AsyncOpenAI(**kwargs)
            logger.info(
                "LLM 客户端初始化成功：model=%s base_url=%s",
                settings.LLM_MODEL,
                settings.LLM_BASE_URL or "(官方 OpenAI)",
            )
        except ImportError:
            logger.warning("openai SDK 未安装，请运行：pip install openai")
        except Exception as e:
            logger.warning("LLM 客户端初始化失败: %s", e)

    async def chat(
        self,
        question: str,
        *,
        region_full_name: str,
        crop_name: str,
        phenology_desc: str,
        memory_items: list[dict],
        knowledge_snippets: list[dict],
        history: list[dict],
        cfg: dict | None = None,
    ) -> LLMResult:
        """生成回答 + 记忆候选 + 提醒候选。

        history: [{"role": "user"|"assistant", "content": "..."}]
        cfg 若提供，优先使用其中的 llm_* 配置（来自数据库）。
        """
        cfg = cfg or {}
        api_key = (cfg.get("llm_api_key") or settings.LLM_API_KEY or "").strip()
        base_url = (cfg.get("llm_base_url") or settings.LLM_BASE_URL or "").strip()
        model = (cfg.get("llm_model") or settings.LLM_MODEL or "").strip()

        # 动态构建客户端（支持 DB 配置覆盖）
        client = self._client
        if api_key and (api_key != settings.LLM_API_KEY or base_url != settings.LLM_BASE_URL):
            try:
                from openai import AsyncOpenAI
                kwargs: dict = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url.rstrip("/")
                client = AsyncOpenAI(**kwargs)
            except Exception as e:
                logger.warning("动态 LLM 客户端初始化失败: %s", e)

        if client is None:
            return self._fallback(question, region_full_name, crop_name, phenology_desc)

        memory_text = self._format_memory(memory_items)
        knowledge_text = self._format_knowledge(knowledge_snippets)
        today_str = date.today().strftime("%Y年%m月%d日")

        user_content = (
            f"【今日日期】{today_str}\n"
            f"【位置】{region_full_name}\n"
            f"【作物】{crop_name}\n"
            f"【当前物候期】{phenology_desc}\n"
            f"【您的地块信息】\n{memory_text}\n\n"
            f"【参考资料】\n{knowledge_text}\n\n"
            f"【问题】{question}"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *list(history),
            {"role": "user", "content": user_content},
        ]

        try:
            response = await client.chat.completions.create(
                model=model or settings.LLM_MODEL,
                messages=messages,
                tools=[MEMORY_TOOL, REMINDER_TOOL],
                tool_choice="auto",
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                timeout=settings.LLM_TIMEOUT_SEC,
            )
        except Exception as e:
            logger.exception("LLM 调用失败: %s", e)
            return self._fallback(question, region_full_name, crop_name, phenology_desc)

        msg = response.choices[0].message
        answer: str = (msg.content or "").strip()

        # 解析工具调用
        proposed_memory: list[dict] = []
        proposed_reminders: list[dict] = []
        reminder_summary: str = ""

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.warning("解析工具调用 %s 失败: %s", name, e)
                    continue

                if name == "propose_memory_update":
                    for item in args.get("items", []):
                        if item.get("confidence", 0) >= 0.6:
                            proposed_memory.append(item)

                elif name == "propose_reminders":
                    reminder_summary = args.get("summary", "")
                    for item in args.get("items", []):
                        if item.get("scheduled_date") and item.get("title"):
                            proposed_reminders.append(item)

        if not answer:
            answer = "抱歉，我没有生成有效回答，请您换个问法再试试。"

        return LLMResult(
            answer=answer,
            proposed_memory_items=proposed_memory,
            proposed_reminders=proposed_reminders,
            reminder_summary=reminder_summary,
        )

    # ── 降级 ─────────────────────────────────────────────────────────────

    def _fallback(self, question: str, region: str, crop: str, stage: str) -> LLMResult:
        txt = (
            f"【LLM 未配置 · 降级模式】\n\n"
            f"您在 {region} 种植 {crop}（当前物候期：{stage}）。\n\n"
            f"您的问题：{question}\n\n"
            f"请在 .env 中配置 LLM_API_KEY，然后重启服务。"
        )
        return LLMResult(answer=txt, proposed_memory_items=[], used_fallback=True)

    # ── 格式化辅助 ────────────────────────────────────────────────────────

    @staticmethod
    def _format_memory(items: list[dict]) -> str:
        if not items:
            return "（暂无记录。欢迎在回答中告诉我地块信息，我会为您记住。）"
        lines = []
        for it in items:
            label = KEY_LABELS.get(it["key"], it["key"])
            lines.append(f"- {label}：{it['value']}")
        return "\n".join(lines)

    @staticmethod
    def _format_knowledge(snippets: list[dict]) -> str:
        if not snippets:
            return "（本次未检索到相关资料，请基于您的专业经验作答。）"
        lines = []
        for i, s in enumerate(snippets, 1):
            lines.append(f"[{i}] {s.get('title', '')}：{s.get('snippet', '')}")
        return "\n".join(lines)


llm_client = LLMClient()
