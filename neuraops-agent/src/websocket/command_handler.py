# src/websocket/command_handler.py
"""
Agent WebSocket Command Handler

CLAUDE.md: < 500 lignes, gestionnaire commandes WebSocket agent
Traite les commandes reçues via WebSocket et retourne les résultats
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import json

try:
    import websockets
except ImportError:
    websockets = None  # Will be handled in connect() method

from .message_types import (
    MessageParser, MessageValidator, WebSocketMessage, CommandMessage,
    ResultMessage, StatusMessage, ErrorMessage, MessageType
)
from ..agent_cli.command_executor import AgentCommandExecutor


class AgentCommandHandler:
    """
    Handle WebSocket command execution on agent
    
    CLAUDE.md: Single responsibility pour traitement commandes WebSocket
    """
    
    def __init__(self, agent_name: str, websocket=None):
        """
        Initialize command handler
        
        Args:
            agent_name: Name of this agent
            websocket: WebSocket connection to core
        """
        self.agent_name = agent_name
        self.websocket = websocket
        self.logger = logging.getLogger(__name__)
        
        # Command executor
        self.executor = AgentCommandExecutor()
        
        # Track active commands
        self.active_commands: Dict[str, Dict[str, Any]] = {}
        
        # Track cleanup tasks for proper lifecycle management (SonarQube S7502)
        self.cleanup_tasks: Dict[str, Any] = {}
        
        # Message handlers
        self.message_handlers = {
            MessageType.COMMAND_REQUEST: self._handle_command_request,
            MessageType.COMMAND_CANCEL: self._handle_command_cancel,
            MessageType.AGENT_HEARTBEAT: self._handle_heartbeat_request,
        }
    
    async def handle_message(self, raw_message: str) -> None:
        """
        Handle incoming WebSocket message
        
        Args:
            raw_message: Raw JSON message from WebSocket
        """
        try:
            # Validate message size
            if not MessageValidator.validate_message_size(raw_message):
                await self._send_error("Message too large", "MESSAGE_SIZE_EXCEEDED")
                return
            
            # Parse message
            try:
                message = MessageParser.parse_message(raw_message)
            except ValueError as e:
                await self._send_error(f"Invalid message format: {e}", "INVALID_MESSAGE")
                return
            
            # Validate message
            validation_errors = MessageValidator.validate_message(message)
            if validation_errors:
                await self._send_error(
                    f"Message validation failed: {'; '.join(validation_errors)}", 
                    "VALIDATION_FAILED"
                )
                return
            
            # Route to appropriate handler
            handler = self.message_handlers.get(message.type)
            if handler:
                await handler(message)
            else:
                await self._send_error(
                    f"Unsupported message type: {message.type}", 
                    "UNSUPPORTED_MESSAGE"
                )
        
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
            await self._send_error(f"Internal handler error: {str(e)}", "HANDLER_ERROR")
    
    async def _handle_command_request(self, message: CommandMessage) -> None:
        """Handle command execution request"""
        request_id = message.request_id
        if not request_id:
            await self._send_error("Command request missing request_id", "MISSING_REQUEST_ID")
            return
        
        try:
            self.logger.info(f"Executing command: {message.command} {' '.join(message.args)}")
            
            # Track command
            self.active_commands[request_id] = {
                "command": message.command,
                "args": message.args,
                "start_time": time.time(),
                "status": "executing"
            }
            
            # Send status update
            await self._send_status_update(request_id, "executing", current_step="Starting command execution")
            
            # Execute command
            result = await self.executor.execute(
                command=message.command,
                args=message.args,
                timeout_seconds=message.timeout_seconds
            )
            
            # Update command tracking
            if request_id in self.active_commands:
                self.active_commands[request_id]["status"] = "completed" if result.get("success") else "failed"
                self.active_commands[request_id]["end_time"] = time.time()
            
            # Send result
            await self._send_command_result(request_id, result)
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            
            # Update command tracking
            if request_id in self.active_commands:
                self.active_commands[request_id]["status"] = "failed"
                self.active_commands[request_id]["end_time"] = time.time()
                self.active_commands[request_id]["error"] = str(e)
            
            # Send error result
            error_result = {
                "success": False,
                "return_code": 1,
                "command": message.command,
                "subcommand": message.args[0] if message.args else None,
                "error": f"Command execution failed: {str(e)}",
                "execution_time_seconds": 0,
                "timestamp": datetime.now().isoformat()
            }
            
            await self._send_command_result(request_id, error_result)
        
        finally:
            # Clean up command tracking after some time (SonarQube S7502)
            if request_id in self.active_commands:
                cleanup_task = asyncio.create_task(self._cleanup_command(request_id, delay=60))
                self.cleanup_tasks[request_id] = cleanup_task
    
    async def _handle_command_cancel(self, message) -> None:
        """Handle command cancellation request"""
        request_id = message.request_id
        if not request_id:
            return
        
        if request_id in self.active_commands:
            self.active_commands[request_id]["status"] = "cancelled"
            self.logger.info(f"Command {request_id} cancelled: {message.reason or 'No reason given'}")
            
            # Send cancellation confirmation
            await self._send_status_update(
                request_id, 
                "cancelled", 
                current_step=f"Cancelled: {message.reason or 'User requested'}"
            )
    
    async def _handle_heartbeat_request(self, message) -> None:
        """Handle heartbeat request from core"""
        # Respond with agent status
        from ..agent_cli.health_commands import AgentHealthCommands
        
        try:
            health = AgentHealthCommands()
            cpu_memory = health.check_cpu_memory()
            
            system_status = {
                "cpu_percent": cpu_memory.get("cpu", {}).get("percent_used", 0),
                "memory_percent": cpu_memory.get("memory", {}).get("percent_used", 0),
                "active_commands": len([cmd for cmd in self.active_commands.values() 
                                     if cmd.get("status") == "executing"])
            }
            
            # Send heartbeat response (reuse HeartbeatMessage structure)
            heartbeat_data = {
                "type": MessageType.AGENT_HEARTBEAT,
                "agent_name": self.agent_name,
                "system_status": system_status,
                "active_commands": len(self.active_commands),
                "timestamp": datetime.now().isoformat()
            }
            
            if self.websocket:
                await self.websocket.send_text(json.dumps(heartbeat_data))
        
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {e}")
    
    async def _send_command_result(self, request_id: str, result: Dict[str, Any]) -> None:
        """Send command execution result"""
        if not self.websocket:
            return
        
        try:
            result_message = ResultMessage(
                request_id=request_id,
                success=result.get("success", False),
                return_code=result.get("return_code", 1),
                stdout="",  # Will be formatted by core
                stderr="",  # Will be formatted by core  
                execution_time_seconds=result.get("execution_time_seconds"),
                agent_data=result.get("agent_data", result),  # Send raw data for core formatting
                error_details=result.get("error")
            )
            
            await self.websocket.send_text(result_message.json())
            
        except Exception as e:
            self.logger.error(f"Error sending command result: {e}")
    
    async def _send_status_update(
        self, 
        request_id: str, 
        status: str, 
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None
    ) -> None:
        """Send command status update"""
        if not self.websocket:
            return
        
        try:
            status_message = StatusMessage(
                request_id=request_id,
                status=status,
                progress_percent=progress_percent,
                current_step=current_step
            )
            
            await self.websocket.send_text(status_message.json())
            
        except Exception as e:
            self.logger.error(f"Error sending status update: {e}")
    
    async def _send_error(self, error_message: str, error_code: str, request_id: Optional[str] = None) -> None:
        """Send error message"""
        if not self.websocket:
            return
        
        try:
            error_msg = ErrorMessage(
                request_id=request_id,
                error_code=error_code,
                error_message=error_message,
                context={"agent_name": self.agent_name}
            )
            
            await self.websocket.send_text(error_msg.json())
            
        except Exception as e:
            self.logger.error(f"Error sending error message: {e}")
    
    async def _cleanup_command(self, request_id: str, delay: int = 0):
        """Clean up command tracking after delay"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        if request_id in self.active_commands:
            del self.active_commands[request_id]
        
        # Clean up task reference (SonarQube S7502)
        if request_id in self.cleanup_tasks:
            del self.cleanup_tasks[request_id]

    async def _cancel_all_cleanup_tasks(self):
        """Cancel all pending cleanup tasks for proper shutdown"""
        for request_id, task in self.cleanup_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    # Expected behavior when cancelling tasks
                    self.logger.debug(f"Cleanup task {request_id} cancelled successfully")
                    raise  # Re-raise CancelledError as required by SonarQube S7497
        self.cleanup_tasks.clear()
    
    def get_active_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active commands"""
        return self.active_commands.copy()
    
    def get_command_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific command"""
        return self.active_commands.get(request_id)
    
    def set_websocket(self, websocket) -> None:
        """Set WebSocket connection"""
        self.websocket = websocket
    
    async def disconnect(self) -> None:
        """Handle disconnect - clean up resources"""
        self.logger.info(f"Agent {self.agent_name} disconnecting")
        
        # Cancel all active commands (SonarQube S7504: removed unnecessary list())
        for request_id in self.active_commands.keys():
            if self.active_commands[request_id].get("status") == "executing":
                self.active_commands[request_id]["status"] = "cancelled"
        
        # Cancel all cleanup tasks
        await self._cancel_all_cleanup_tasks()
        
        # Send disconnect message
        if self.websocket:
            try:
                from .message_types import DisconnectMessage
                disconnect_msg = DisconnectMessage(
                    agent_name=self.agent_name,
                    reason="Agent shutdown"
                )
                await self.websocket.send_text(disconnect_msg.json())
            except Exception as e:
                self.logger.debug(f"Error sending disconnect message: {e}")


class AgentWebSocketManager:
    """
    Manage WebSocket connection and message handling for agent
    
    CLAUDE.md: Lightweight manager pour connexion WebSocket
    """
    
    def __init__(self, agent_name: str):
        """Initialize WebSocket manager"""
        self.agent_name = agent_name
        self.logger = logging.getLogger(__name__)
        self.websocket = None
        self.command_handler = None
        self.connected = False
    
    async def connect(self, websocket_url: str) -> bool:
        """
        Connect to Core WebSocket endpoint
        
        Args:
            websocket_url: WebSocket URL for Core
            
        Returns:
            True if connected successfully
        """
        try:
            if websockets is None:
                raise ImportError("websockets package not available")
            
            self.logger.info(f"Connecting to Core WebSocket: {websocket_url}")
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(websocket_url)
            
            # Initialize command handler
            self.command_handler = AgentCommandHandler(self.agent_name, self.websocket)
            
            self.connected = True
            self.logger.info("Connected to Core WebSocket")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Core WebSocket: {e}")
            self.connected = False
            return False
    
    async def listen(self) -> None:
        """Listen for WebSocket messages"""
        if not self.websocket or not self.command_handler:
            self.logger.error("Not connected to WebSocket")
            return
        
        try:
            while self.connected:
                message = await self.websocket.recv()
                await self.command_handler.handle_message(message)
                
        except Exception as e:
            self.logger.error(f"WebSocket listen error: {e}")
            self.connected = False
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket"""
        self.connected = False
        
        if self.command_handler:
            await self.command_handler.disconnect()
        
        if self.websocket:
            await self.websocket.close()
            
        self.logger.info("Disconnected from Core WebSocket")