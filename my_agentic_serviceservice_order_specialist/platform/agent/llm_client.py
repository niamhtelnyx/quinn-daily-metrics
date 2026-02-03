"""LLM client implementation using LiteLLM."""

from typing import Self

import httpx
import litellm
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM

from my_agentic_serviceservice_order_specialist.platform.agent.metrics import record_agent_tokens

DEFAULT_MAX_INPUT_TOKENS = 8192


class LlmClient(Runnable):
    """LLM client that wraps ChatLiteLLM as a Runnable.

    Provides a consistent interface for LLM interactions with:
    - Full LCEL compatibility (pipe operator, chains)
    - Automatic token metrics recording
    - Tool binding support
    - Max input token lookup (local + proxy API)
    """

    def __init__(
        self,
        agent_slug: str,
        model_name: str,
        api_key: str | None,
        api_base: str | None,
        temperature: float,
        llm=None,
    ):
        """Initialize the LLM client.

        Args:
            model_name: Model identifier (e.g., from LLMProxyModel)
            api_key: API key for authentication
            base_url: Base URL for the LLM proxy
            temperature: Sampling temperature
            llm: Optional pre-configured LLM instance (for bind_tools)
        """
        self._agent_slug = agent_slug
        self._model_name = model_name
        self._api_key = api_key
        self._api_base = api_base
        self._temperature = temperature
        self._llm = llm or ChatLiteLLM(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            temperature=temperature,
        )
        self._max_input_tokens: int | None = None

    @property
    def model_name(self) -> str:
        """The model name/identifier."""
        return self._model_name

    def bind_tools(self, tools: list[BaseTool]) -> Self:
        """Return a new client with tools bound.

        Args:
            tools: Tools to bind to the LLM

        Returns:
            New LlmClient instance with tools bound
        """
        return LlmClient(
            agent_slug=self._agent_slug,
            model_name=self._model_name,
            api_key=self._api_key,
            api_base=self._api_base,
            temperature=self._temperature,
            llm=self._llm.bind_tools(tools),
        )

    async def get_max_input_tokens(self) -> int:
        """Get max input tokens for the model.

        Resolution order:
        1. Cached value (if already resolved)
        2. LiteLLM local model info (strips proxy prefix)
        3. LiteLLM proxy /v1/model/info endpoint
        4. Default fallback
        """
        if self._max_input_tokens is not None:
            return self._max_input_tokens

        # Try local LiteLLM lookup (strip proxy prefix)
        max_tokens = self._get_from_litellm_local()
        if max_tokens:
            self._max_input_tokens = max_tokens
            return max_tokens

        # Try proxy API
        max_tokens = await self._get_from_proxy_api()
        if max_tokens:
            self._max_input_tokens = max_tokens
            return max_tokens

        # Fallback to default
        self._max_input_tokens = DEFAULT_MAX_INPUT_TOKENS
        return self._max_input_tokens

    def _get_from_litellm_local(self) -> int | None:
        """Try to get max tokens from LiteLLM's local model database."""
        # Strip litellm_proxy/ prefix if present
        model = self._model_name
        if model.startswith("litellm_proxy/"):
            model = model[len("litellm_proxy/") :]

        try:
            model_info = litellm.get_model_info(model)
            return model_info.get("max_input_tokens") or model_info.get("max_tokens")
        except Exception:
            return None

    async def _get_from_proxy_api(self) -> int | None:
        """Query LiteLLM proxy for model info."""
        if not self._api_base or not self._api_key:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._api_base}/v1/model/info",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=10.0,
                )
                response.raise_for_status()

                # Find our model in the response
                models = response.json().get("data", [])
                for model in models:
                    if model.get("model_name") == self._model_name:
                        model_info = model.get("model_info", {})
                        return model_info.get("max_input_tokens") or model_info.get("max_tokens")
        except Exception:
            return None

        return None

    @staticmethod
    def extract_tokens(message: AIMessage) -> tuple[int, int]:
        """Extract token counts from an AIMessage's usage metadata.

        Args:
            message: AIMessage from LLM response

        Returns:
            Tuple of (input_tokens, output_tokens), defaults to (0, 0) if unavailable
        """
        usage = getattr(message, "usage_metadata", None)
        if not usage:
            return 0, 0
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0)

    def invoke(self, input, config: RunnableConfig | None = None, **kwargs):
        """Invoke the LLM synchronously.

        Args:
            input: Messages to send to the LLM
            config: Optional runnable config
            **kwargs: Additional arguments passed to underlying LLM

        Returns:
            The LLM's response message
        """
        response = self._llm.invoke(input, config=config, **kwargs)
        input_tokens, output_tokens = self.extract_tokens(response)
        record_agent_tokens(
            self._agent_slug,
            self._model_name,
            input_tokens,
            output_tokens,
        )
        return response

    async def ainvoke(self, input, config: RunnableConfig | None = None, **kwargs):
        """Invoke the LLM asynchronously.

        Args:
            input: Messages to send to the LLM
            config: Optional runnable config
            **kwargs: Additional arguments passed to underlying LLM

        Returns:
            The LLM's response message
        """
        response = await self._llm.ainvoke(input, config=config, **kwargs)
        input_tokens, output_tokens = self.extract_tokens(response)
        record_agent_tokens(
            self._agent_slug,
            self._model_name,
            input_tokens,
            output_tokens,
        )
        return response
