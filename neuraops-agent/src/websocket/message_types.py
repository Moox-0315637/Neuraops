# src/websocket/message_types.py
"""
WebSocket Message Types

CLAUDE.md: < 500 lignes, types de messages WebSocket agent-core
Messages structurés pour communication temps réel
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from enum import Enum


# Constants pour descriptions Pydantic (SonarQube S1192)
AGENT_ID_DESC = "Agent identifier"

class MessageType(str, Enum):
    """WebSocket message types"""
    # Command flow
    COMMAND_REQUEST = "command_request"
    COMMAND_RESULT = "command_result"
    COMMAND_STATUS = "command_status"
    COMMAND_CANCEL = "command_cancel"
    
    # Agent management
    AGENT_REGISTER = "agent_register"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_DISCONNECT = "agent_disconnect"
    
    # Status updates
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""
    type: MessageType = Field(..., description="Message type")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for correlation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            MessageType: str
        }


class CommandMessage(WebSocketMessage):
    """Command execution request message"""
    type: Literal[MessageType.COMMAND_REQUEST] = MessageType.COMMAND_REQUEST
    command: str = Field(..., description="Command to execute (e.g., 'health')")
    args: List[str] = Field(default=[], description="Command arguments")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout")
    execution_context: Optional[Dict[str, Any]] = Field(None, description="Additional execution context")


class ResultMessage(WebSocketMessage):
    """Command execution result message"""
    type: Literal[MessageType.COMMAND_RESULT] = MessageType.COMMAND_RESULT
    success: bool = Field(..., description="Whether command succeeded")
    return_code: int = Field(default=0, description="Command return code")
    stdout: str = Field(default="", description="Command standard output")
    stderr: str = Field(default="", description="Command standard error")
    execution_time_seconds: Optional[float] = Field(None, description="Execution duration")
    agent_data: Optional[Dict[str, Any]] = Field(None, description="Raw agent data")
    error_details: Optional[str] = Field(None, description="Detailed error information")


class StatusMessage(WebSocketMessage):
    """Command status update message"""
    type: Literal[MessageType.COMMAND_STATUS] = MessageType.COMMAND_STATUS
    status: Literal["pending", "executing", "completed", "failed", "timeout", "cancelled"] = Field(..., description="Current status")
    progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Execution progress")
    current_step: Optional[str] = Field(None, description="Current execution step")
    estimated_remaining_seconds: Optional[int] = Field(None, description="Estimated time remaining")


class CancelMessage(WebSocketMessage):
    """Command cancellation request message"""
    type: Literal[MessageType.COMMAND_CANCEL] = MessageType.COMMAND_CANCEL
    reason: Optional[str] = Field(None, description="Cancellation reason")


class AgentRegisterMessage(WebSocketMessage):
    """Agent registration message"""
    type: Literal[MessageType.AGENT_REGISTER] = MessageType.AGENT_REGISTER
    agent_name: str = Field(..., description=AGENT_ID_DESC)
    capabilities: List[str] = Field(default=[], description="Agent capabilities")
    system_info: Dict[str, Any] = Field(default={}, description="Agent system information")
    version: str = Field(default="1.0.0", description="Agent version")


class HeartbeatMessage(WebSocketMessage):
    """Agent heartbeat message"""
    type: Literal[MessageType.AGENT_HEARTBEAT] = MessageType.AGENT_HEARTBEAT
    agent_name: str = Field(..., description=AGENT_ID_DESC)
    uptime_seconds: Optional[int] = Field(None, description="Agent uptime")
    system_status: Optional[Dict[str, Any]] = Field(None, description="Current system status")
    active_commands: int = Field(default=0, description="Number of active commands")


class DisconnectMessage(WebSocketMessage):
    """Agent disconnect notification"""
    type: Literal[MessageType.AGENT_DISCONNECT] = MessageType.AGENT_DISCONNECT
    agent_name: str = Field(..., description=AGENT_ID_DESC)
    reason: Optional[str] = Field(None, description="Disconnect reason")


class ErrorMessage(WebSocketMessage):
    """Error notification message"""
    type: Literal[MessageType.ERROR_NOTIFICATION] = MessageType.ERROR_NOTIFICATION
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    context: Optional[Dict[str, Any]] = Field(None, description="Error context information")
    recovery_suggestions: Optional[List[str]] = Field(None, description="Suggested recovery actions")


class MessageParser:
    """Parse and validate WebSocket messages"""
    
    @staticmethod
    def parse_message(raw_message: str) -> WebSocketMessage:
        """
        Parse raw WebSocket message into typed message
        
        Args:
            raw_message: JSON string message
            
        Returns:
            Parsed and validated message
            
        Raises:
            ValueError: If message cannot be parsed or is invalid
        """
        try:
            import json
            data = json.loads(raw_message)
            
            message_type = data.get("type")
            if not message_type:
                raise ValueError("Message missing 'type' field")
            
            # Route to appropriate message class
            message_classes = {
                MessageType.COMMAND_REQUEST: CommandMessage,
                MessageType.COMMAND_RESULT: ResultMessage,
                MessageType.COMMAND_STATUS: StatusMessage,
                MessageType.COMMAND_CANCEL: CancelMessage,
                MessageType.AGENT_REGISTER: AgentRegisterMessage,
                MessageType.AGENT_HEARTBEAT: HeartbeatMessage,
                MessageType.AGENT_DISCONNECT: DisconnectMessage,
                MessageType.ERROR_NOTIFICATION: ErrorMessage,
            }
            
            message_class = message_classes.get(MessageType(message_type))
            if not message_class:
                # Fallback to base WebSocketMessage
                return WebSocketMessage(**data)
            
            return message_class(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Message validation failed: {e}")
    
    @staticmethod
    def serialize_message(message: WebSocketMessage) -> str:
        """
        Serialize message to JSON string
        
        Args:
            message: Message to serialize
            
        Returns:
            JSON string representation
        """
        return message.json()


class MessageValidator:
    """Validate WebSocket messages for security and correctness"""
    
    # Maximum message size (1MB)
    MAX_MESSAGE_SIZE = 1024 * 1024
    
    # Allowed command patterns
    ALLOWED_COMMAND_PATTERNS = {
        "health": ["disk", "cpu-memory", "network", "processes", "monitor", "system-health"],
        "system": ["info", "environment"],
        "logs": ["read-local"]  # For hybrid commands
    }
    
    @classmethod
    def validate_message_size(cls, message: str) -> bool:
        """Check if message size is within limits"""
        return len(message.encode('utf-8')) <= cls.MAX_MESSAGE_SIZE
    
    @classmethod
    def validate_command_message(cls, message: CommandMessage) -> List[str]:
        """
        Validate command message for security
        
        Args:
            message: Command message to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check command is allowed
        if message.command not in cls.ALLOWED_COMMAND_PATTERNS:
            errors.append(f"Command '{message.command}' not allowed")
        else:
            # Check subcommand is allowed
            allowed_subcommands = cls.ALLOWED_COMMAND_PATTERNS[message.command]
            if message.args and message.args[0] not in allowed_subcommands:
                errors.append(f"Subcommand '{message.args[0]}' not allowed for '{message.command}'")
        
        # Check timeout is reasonable
        if message.timeout_seconds > 300:
            errors.append("Timeout too long (max 300 seconds)")
        
        # Check for potentially dangerous arguments
        dangerous_patterns = ["rm", "del", "format", "shutdown", "reboot", "../", "sudo", "su"]
        for arg in message.args:
            for pattern in dangerous_patterns:
                if pattern in arg.lower():
                    errors.append(f"Potentially dangerous argument: {arg}")
                    break
        
        return errors
    
    @classmethod
    def validate_message(cls, message: WebSocketMessage) -> List[str]:
        """
        Validate any WebSocket message
        
        Args:
            message: Message to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        if isinstance(message, CommandMessage):
            return cls.validate_command_message(message)
        
        # For other message types, basic validation
        return []