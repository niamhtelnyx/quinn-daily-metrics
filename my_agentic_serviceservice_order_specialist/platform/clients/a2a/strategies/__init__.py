"""Execution strategies for A2A client.

This module provides different execution strategies for communicating
with A2A agents: synchronous, streaming, and polling.
"""

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import (
    ExecutionResult,
    ExecutionStrategyProtocol,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.polling import PollingStrategy
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.streaming import StreamingStrategy
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.sync import SyncStrategy

__all__ = [
    "ExecutionStrategyProtocol",
    "ExecutionResult",
    "SyncStrategy",
    "StreamingStrategy",
    "PollingStrategy",
]
