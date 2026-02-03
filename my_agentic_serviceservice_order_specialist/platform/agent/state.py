"""Base LangGraph state definition for all agents."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


def add_tokens(existing: dict[str, int], new: dict[str, int]) -> dict[str, int]:
    """Reducer that accumulates token counts by model.

    Args:
        existing: Current token counts by model
        new: New token counts to add

    Returns:
        Merged dict with accumulated counts per model
    """
    result = dict(existing or {})
    for model, tokens in (new or {}).items():
        result[model] = result.get(model, 0) + tokens
    return result


class BaseAgentState(TypedDict):
    """Base LangGraph state shared across all agents.

    Attributes:
        messages: Conversation history with automatic deduplication via add_messages
        thread_id: Unique identifier for the conversation thread
        agent_slug: Identifier for the agent type that owns this thread
        input_tokens_by_model: Cumulative input tokens by model (auto-accumulated via reducer)
        output_tokens_by_model: Cumulative output tokens by model (auto-accumulated via reducer)
    """

    messages: Annotated[list[AnyMessage], add_messages]
    thread_id: str
    agent_slug: str
    input_tokens_by_model: Annotated[dict[str, int], add_tokens]
    output_tokens_by_model: Annotated[dict[str, int], add_tokens]
