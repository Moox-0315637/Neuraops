"""
Agent WebSocket Handler

Handles WebSocket connections for distributed agents.
Follows CLAUDE.md: < 100 lines, Safety-First.
"""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import structlog

from typing import Optional
from ..dependencies import get_jwt_handler
logger = structlog.get_logger()


def _extract_token_from_websocket(websocket: WebSocket) -> Optional[str]:
    """
    Extract JWT token from WebSocket connection
    
    CLAUDE.md: Helper function < 10 lines for token extraction
    Checks query parameters first, then headers
    """
    # Check query parameters first (most common for WebSocket auth)
    token = websocket.query_params.get("token")
    if token:
        return token
    
    # Fallback to Authorization header
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    return None

async def handle_agent_websocket(websocket: WebSocket, agent_id: str, app: FastAPI):
    """
    Handle agent WebSocket connection
    
    CLAUDE.md: Safety-First - Validate agent before connection
    CLAUDE.md: < 50 lines per function
    """
    try:
        # JWT token validation for WebSocket connections
        token = _extract_token_from_websocket(websocket)
        if not token:
            logger.warning("No JWT token provided for WebSocket connection", agent_id=agent_id)
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        # Get JWT handler and validate token
        jwt_handler = get_jwt_handler()
        token_data = jwt_handler.verify_token(token)
        
        if not token_data:
            logger.warning("Invalid JWT token for WebSocket connection", agent_id=agent_id)
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Verify agent_id matches token
        if token_data.agent_id != agent_id:
            logger.warning("Agent ID mismatch in WebSocket connection", 
                          provided=agent_id, token_agent=token_data.agent_id)
            await websocket.close(code=4003, reason="Agent ID mismatch")
            return
        
        # Connection authorized - proceed with WebSocket handling
        await app.state.websocket_manager.connect(websocket, agent_id)
        logger.info("Agent WebSocket connected and authenticated", 
                   agent_id=agent_id, capabilities=token_data.capabilities)
        
        try:
            while True:
                # Receive message from agent
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process message through event handler
                await app.state.websocket_event_handler.handle_message(agent_id, message_data)
                
        except WebSocketDisconnect:
            logger.info("Agent WebSocket disconnected", agent_id=agent_id)
            app.state.websocket_manager.disconnect(agent_id)
            
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in WebSocket message", 
                    agent_id=agent_id, error=str(e))
        app.state.websocket_manager.disconnect(agent_id)
        
    except ConnectionError as e:
        logger.error("WebSocket connection error", 
                    agent_id=agent_id, error=str(e))
        app.state.websocket_manager.disconnect(agent_id)
        
    except Exception as e:
        logger.error("Unexpected WebSocket error", 
                    agent_id=agent_id, error=str(e))
        app.state.websocket_manager.disconnect(agent_id)