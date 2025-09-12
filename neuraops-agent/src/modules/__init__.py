"""
NeuraOps Agent Modules

Specialized modules for agent functionality with proper async handling.
Fixes SonarQube S7497 and S7502 errors through modular architecture.
Single responsibility, modular design.
"""

from .agent_exceptions import AsyncExceptionHandler
from .task_manager import TaskManager
from .background_loops import BackgroundLoops

__all__ = [
    "AsyncExceptionHandler",
    "TaskManager", 
    "BackgroundLoops"
]