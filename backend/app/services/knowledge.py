import httpx
from app.core.config import settings


class KnowledgeService:
    """
    知识库 API 调用服务。
    接口文档确认后，在此处实现具体调用逻辑。
    目前提供占位实现，返回模拟回答。
    """

    def __init__(self):
        self.base_url = settings.KNOWLEDGE_API_BASE_URL
        self.api_key = settings.KNOWLEDGE_API_KEY

    async def ask(self, question: str, history: list[dict] | None = None) -> str:
        """
        向知识库发起问答请求。

        Args:
            question: 用户提问
            history: 历史对话列表，格式 [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            知识库返回的答案文本
        """
        if not self.base_url or not self.api_key:
            return self._placeholder_answer(question)

        # TODO: 接收到接口文档后，在此替换为真实实现
        # 示例结构（适配 OpenAI 兼容格式）：
        # async with httpx.AsyncClient(timeout=30) as client:
        #     response = await client.post(
        #         f"{self.base_url}/chat/completions",
        #         headers={"Authorization": f"Bearer {self.api_key}"},
        #         json={
        #             "messages": (history or []) + [{"role": "user", "content": question}]
        #         },
        #     )
        #     response.raise_for_status()
        #     return response.json()["choices"][0]["message"]["content"]

        return self._placeholder_answer(question)

    def _placeholder_answer(self, question: str) -> str:
        return (
            f"【知识库 API 尚未配置】\n\n"
            f"您的问题：{question}\n\n"
            f"请在 .env 文件中配置 KNOWLEDGE_API_BASE_URL 和 KNOWLEDGE_API_KEY，"
            f"并在 app/services/knowledge.py 中实现具体调用逻辑。"
        )


knowledge_service = KnowledgeService()
