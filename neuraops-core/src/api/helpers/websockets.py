"""
WebSocket Endpoints Configuration

Handles WebSocket endpoint setup with delegated handlers.
Follows CLAUDE.md: < 100 lines, Single Responsibility.
"""
from fastapi import FastAPI, WebSocket
import structlog

from ..websocket.agent_handler import handle_agent_websocket
from ..websocket.cli_handler import handle_cli_websocket

logger = structlog.get_logger()


def setup_websocket_endpoints(app: FastAPI) -> None:
    """
    Setup WebSocket endpoints
    
    CLAUDE.md: < 30 lines - Delegate to specialized handlers
    Reduces cognitive complexity by moving logic to separate files
    """
    
    @app.websocket("/ws/{agent_id}")
    async def websocket_endpoint(websocket: WebSocket, agent_id: str):
        """
        WebSocket endpoint for agent communication
        
        CLAUDE.md: Delegate to agent_handler to reduce complexity
        """
        await handle_agent_websocket(websocket, agent_id, app)
    
    @app.websocket("/ws/cli")
    async def cli_websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for CLI interactive mode
        
        CLAUDE.md: Delegate to cli_handler to reduce complexity
        Fixes import and exception handling issues
        Note: app parameter unused in handler (SonarQube S1172 fix)
        """
        await handle_cli_websocket(websocket, app)