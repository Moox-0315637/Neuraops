# src/websocket/__init__.py
"""
NeuraOps Agent WebSocket Module

CLAUDE.md: < 500 lignes, WebSocket communication pour agent
Gestion des commandes temps réel entre Core et Agent
"""

from .command_handler import AgentCommandHandler
from .message_types import WebSocketMessage, CommandMessage, ResultMessage

__all__ = [
    "AgentCommandHandler",
    "WebSocketMessage", 
    "CommandMessage",
    "ResultMessage"
]

__version__ = "1.0.0"