# src/agent_cli/__init__.py
"""
NeuraOps Agent CLI Module

CLAUDE.md: < 500 lignes, agent-side command execution
Provides local command execution capabilities for system monitoring
"""

from .health_commands import AgentHealthCommands
from .system_commands import AgentSystemCommands
from .command_executor import AgentCommandExecutor
from .formatter import AgentOutputFormatter

__all__ = [
    "AgentHealthCommands",
    "AgentSystemCommands", 
    "AgentCommandExecutor",
    "AgentOutputFormatter"
]

__version__ = "1.0.0"