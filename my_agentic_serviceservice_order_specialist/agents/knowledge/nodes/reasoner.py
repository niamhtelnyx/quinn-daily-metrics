"""Reasoner node for LLM-based reasoning."""

import logging

from langchain_core.messages import AIMessage, HumanMessage, trim_messages

from my_agentic_serviceservice_order_specialist.agents.knowledge.state import AgentState
from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentConfig
from my_agentic_serviceservice_order_specialist.platform.agent.llm_client import LlmClient

from .base import Node

logger = logging.getLogger(__name__)


class ReasonerNode(Node):
    """Node that invokes the LLM to reason about the next action.

    Handles step limiting and forces a final answer when max steps reached.
    """

    def __init__(
        self,
        llm_with_tools: LlmClient,
        config: AgentConfig,
    ):
        """Initialize the reasoner node.

        Args:
            llm_with_tools: LLM with tools bound
            config: Agent configuration
        """
        self.llm = llm_with_tools
        self.config = config
        self._trimmer = trim_messages(  # type: ignore
            max_tokens=self.config.max_context_tokens,
            strategy="last",
            token_counter=lambda msgs: sum(len(m.content) for m in msgs) // 4,  # ~4 chars per token
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

    def _trim_messages(self, messages: list) -> list:
        """Trim messages if trimmer is configured."""
        if not self._trimmer:
            return messages
        trimmed = self._trimmer.invoke(messages)
        if len(trimmed) < len(messages):
            logger.info(f"Trimmed messages from {len(messages)} to {len(trimmed)}")
        return trimmed

    def _get_token_state_update(self, response: AIMessage) -> dict:
        """Extract token usage from response as state update dict.

        Args:
            response: AIMessage from LLM

        Returns:
            Dict with input/output tokens keyed by model for state reducer
        """
        input_tokens, output_tokens = self.llm.extract_tokens(response)
        return {
            "input_tokens_by_model": {self.llm.model_name: input_tokens},
            "output_tokens_by_model": {self.llm.model_name: output_tokens},
        }

    async def __call__(self, state: AgentState) -> AgentState:
        """Process messages and generate next action or response.

        Args:
            state: Current agent state

        Returns:
            Updated state with LLM response
        """
        messages = state["messages"]
        steps = state.get("reasoning_steps", 0)
        logger.debug(f"Step {steps}, messages count: {len(messages)}")

        chain = self._trimmer | self.llm

        if steps >= self.config.max_reasoning_steps:
            force_final_msg = HumanMessage(
                content=(
                    "You have reached the maximum number of reasoning steps. "
                    "Please provide a final answer now, summarizing your actions "
                    "and results if the task is not fully complete."
                )
            )
            result = await chain.ainvoke(messages + [force_final_msg])
            return {  # type: ignore
                "messages": state["messages"] + [force_final_msg, result],
                "reasoning_steps": steps + 1,
                **self._get_token_state_update(result),
            }

        result = await chain.ainvoke(messages)
        return {  # type: ignore
            "messages": [result],
            "reasoning_steps": steps + 1,
            **self._get_token_state_update(result),
        }
