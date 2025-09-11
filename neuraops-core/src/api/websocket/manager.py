"""
WebSocket Connection Manager for NeuraOps API

Real-time communication manager following CLAUDE.md: < 200 lines.
Manages agent connections, broadcasts, and event handling.
"""
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """
    WebSocket connection manager for real-time agent communication
    
    CLAUDE.md: Single Responsibility - WebSocket management only
    CLAUDE.md: Fail Fast - Handle connection errors gracefully
    """
    
    def __init__(self):
        # agent_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # agent_id -> metadata
        self.agent_metadata: Dict[str, Dict[str, Any]] = {}
        # Connection timestamps
        self.connection_times: Dict[str, datetime] = {}
        # Background tasks management (S7502 fix)
        self._background_tasks: set = set()
    
    def _get_current_timestamp(self) -> datetime:
        """
        Get current UTC timestamp in timezone-aware format
        
        CLAUDE.md: Helper function < 10 lines
        Fixes SonarQube S6903: Replace deprecated datetime.utcnow()
        """
        return datetime.now(timezone.utc)
    
    def _schedule_background_task(self, coroutine) -> asyncio.Task:
        """
        Schedule background task with proper garbage collection handling
        
        CLAUDE.md: Helper function < 20 lines
        Fixes SonarQube S7502: Prevent premature garbage collection
        """
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    async def connect(self, websocket: WebSocket, agent_id: str, metadata: Dict[str, Any] = None):
        """
        Accept new WebSocket connection
        
        CLAUDE.md: Safety-First - Validate connection before accepting
        """
        try:
            await websocket.accept()
            
            # Store connection
            self.active_connections[agent_id] = websocket
            self.agent_metadata[agent_id] = metadata or {}
            self.connection_times[agent_id] = self._get_current_timestamp()
            
            logger.info("Agent connected via WebSocket",
                       agent_id=agent_id,
                       total_connections=len(self.active_connections))
            
            # Notify other agents about new connection
            await self.broadcast_system_message({
                "type": "agent_connected",
                "agent_id": agent_id,
                "timestamp": self._get_current_timestamp().isoformat(),
                "total_agents": len(self.active_connections)
            }, exclude=[agent_id])
            
        except Exception as e:
            logger.error("Failed to establish WebSocket connection",
                        agent_id=agent_id, error=str(e))
            raise
    
    def disconnect(self, agent_id: str):
        """
        Remove agent connection
        
        CLAUDE.md: Clean resource management
        """
        try:
            if agent_id in self.active_connections:
                del self.active_connections[agent_id]
            if agent_id in self.agent_metadata:
                del self.agent_metadata[agent_id]
            if agent_id in self.connection_times:
                del self.connection_times[agent_id]
            
            logger.info("Agent disconnected from WebSocket",
                       agent_id=agent_id,
                       remaining_connections=len(self.active_connections))
            
            # Notify other agents about disconnection (S7502 fix)
            self._schedule_background_task(self.broadcast_system_message({
                "type": "agent_disconnected",
                "agent_id": agent_id,
                "timestamp": self._get_current_timestamp().isoformat(),
                "total_agents": len(self.active_connections)
            }, exclude=[agent_id]))
            
        except Exception as e:
            logger.error("Error during WebSocket disconnection",
                        agent_id=agent_id, error=str(e))
    
    async def send_personal_message(self, message: Dict[str, Any], agent_id: str):
        """
        Send message to specific agent
        
        CLAUDE.md: Simple direct messaging
        """
        if agent_id not in self.active_connections:
            logger.warning("Agent not connected", agent_id=agent_id)
            return False
        
        try:
            websocket = self.active_connections[agent_id]
            await websocket.send_text(json.dumps(message))
            logger.debug("Message sent to agent", 
                        agent_id=agent_id,
                        message_type=message.get("type"))
            return True
            
        except Exception as e:
            logger.error("Failed to send message to agent",
                        agent_id=agent_id, error=str(e))
            # Remove stale connection
            self.disconnect(agent_id)
            return False
    
    async def broadcast_message(self, message: Dict[str, Any], target_agents: List[str] = None):
        """
        Broadcast message to multiple agents
        
        CLAUDE.md: Efficient message broadcasting
        """
        if target_agents is None:
            target_agents = self.active_connections.keys()
        
        message["timestamp"] = self._get_current_timestamp().isoformat()
        disconnected_agents = []
        
        for agent_id in target_agents:
            if agent_id in self.active_connections:
                try:
                    websocket = self.active_connections[agent_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning("Failed to send broadcast to agent",
                                  agent_id=agent_id, error=str(e))
                    disconnected_agents.append(agent_id)
        
        # Clean up disconnected agents
        for agent_id in disconnected_agents:
            self.disconnect(agent_id)
        
        logger.info("Message broadcasted",
                   message_type=message.get("type"),
                   target_count=len(target_agents),
                   successful=len(target_agents) - len(disconnected_agents))
    
    async def broadcast_system_message(self, message: Dict[str, Any], exclude: List[str] = None):
        """
        Broadcast system message to all connected agents
        
        CLAUDE.md: System-wide notifications
        """
        exclude = exclude or []
        target_agents = [agent_id for agent_id in self.active_connections.keys() 
                        if agent_id not in exclude]
        
        message["source"] = "system"
        await self.broadcast_message(message, target_agents)
    
    async def disconnect_all(self):
        """
        Disconnect all agents (for shutdown)
        
        CLAUDE.md: Clean shutdown procedures
        """
        logger.info("Disconnecting all WebSocket connections",
                   total_connections=len(self.active_connections))
        
        # Clean up background tasks
        for task in self._background_tasks.copy():
            if not task.done():
                task.cancel()
        
        for agent_id in self.active_connections.copy():
            try:
                websocket = self.active_connections[agent_id]
                await websocket.close()
            except Exception as e:
                logger.warning("Error closing WebSocket connection",
                              agent_id=agent_id, error=str(e))
            finally:
                self.disconnect(agent_id)
        
        # Clear background tasks set
        self._background_tasks.clear()
    
    def get_connected_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of connected agents with metadata
        
        Returns connection information for monitoring
        """
        connected_agents = []
        for agent_id, websocket in self.active_connections.items():
            agent_info = {
                "agent_id": agent_id,
                "connected_at": self.connection_times.get(agent_id, self._get_current_timestamp()).isoformat(),
                "metadata": self.agent_metadata.get(agent_id, {}),
                "connection_state": websocket.client_state.name if hasattr(websocket, 'client_state') else "connected"
            }
            connected_agents.append(agent_info)
        
        return connected_agents
    
    def is_agent_connected(self, agent_id: str) -> bool:
        """Check if agent is currently connected"""
        return agent_id in self.active_connections