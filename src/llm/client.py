"""LangChain 封装：按配置选择 Anthropic 或 OpenAI，并规整模型返回内容为字符串。"""

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config import get_settings


class LLMClient:
    """统一聊天模型调用入口；构造时可注入自定义 BaseChatModel（便于测试）。"""

    def __init__(self, model: BaseChatModel | None = None) -> None:
        """默认从环境变量装配云端模型。"""
        self._model = model or self._create_default_model()

    def _create_default_model(self) -> BaseChatModel:
        """读取 Settings：anthropic 分支支持可选自定义 API Base URL。"""
        settings = get_settings()

        if settings.llm_provider == "anthropic":
            kwargs: dict[str, Any] = {
                "model": settings.llm_model,
                "api_key": settings.anthropic_api_key,
                "temperature": 0.7,
            }
            if settings.anthropic_base_url:
                kwargs["anthropic_api_url"] = settings.anthropic_base_url
            return ChatAnthropic(**kwargs)
        else:
            return ChatOpenAI(
                model=settings.llm_model,
                api_key=SecretStr(settings.openai_api_key) if settings.openai_api_key else None,
                temperature=0.7,
            )

    def _extract_content(self, content: Any) -> str:
        """部分厂商返回 content 为块列表（含 reasoning/text）；优先抽取 type=text 段落。"""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    return str(text) if text else ""
            # 未找到 text 块则退回拼接，避免返回空但仍有调试信息
            return " ".join(str(item) for item in content)
        return str(content)

    async def ainvoke(self, prompt: str) -> str:
        """单条用户消息异步调用。"""
        try:
            response: BaseMessage = await self._model.ainvoke(prompt)
            return self._extract_content(response.content)
        except Exception as e:
            raise RuntimeError(f"LLM async invocation failed: {e}") from e

    async def ainvoke_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """系统提示 + 用户提示的标准对话格式（各 Agent 默认路径）。"""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            response = await self._model.ainvoke(messages)
            return self._extract_content(response.content)
        except Exception as e:
            raise RuntimeError(f"LLM async invocation with system prompt failed: {e}") from e

    def invoke(self, prompt: str) -> str:
        """同步调用：脚本或测试场景使用；线上 Agent 优先 async。"""
        try:
            response: BaseMessage = self._model.invoke(prompt)
            return self._extract_content(response.content)
        except Exception as e:
            raise RuntimeError(f"LLM sync invocation failed: {e}") from e


def get_llm_client() -> LLMClient:
    """工厂函数：便于依赖注入与日后缓存策略调整。"""
    return LLMClient()
