"""LLM client with support for multiple providers."""

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from src.config import get_settings


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, model: BaseChatModel | None = None) -> None:
        """Initialize LLM client."""
        self._model = model or self._create_default_model()

    def _create_default_model(self) -> BaseChatModel:
        """Create default model based on settings."""
        settings = get_settings()

        if settings.llm_provider == "anthropic":
            return ChatAnthropic(
                model=settings.llm_model,
                api_key=settings.anthropic_api_key,
                temperature=0.7,
            )
        else:
            return ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                temperature=0.7,
            )

    async def ainvoke(self, prompt: str) -> str:
        """Invoke LLM asynchronously."""
        try:
            response: BaseMessage = await self._model.ainvoke(prompt)
            return str(response.content)
        except Exception as e:
            raise RuntimeError(f"LLM async invocation failed: {e}") from e

    async def ainvoke_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke LLM with separate system and user prompts."""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            response = await self._model.ainvoke(messages)
            return str(response.content)
        except Exception as e:
            raise RuntimeError(f"LLM async invocation with system prompt failed: {e}") from e

    def invoke(self, prompt: str) -> str:
        """Invoke LLM synchronously."""
        try:
            response: BaseMessage = self._model.invoke(prompt)
            return str(response.content)
        except Exception as e:
            raise RuntimeError(f"LLM sync invocation failed: {e}") from e


def get_llm_client() -> LLMClient:
    """Get LLM client instance."""
    return LLMClient()
