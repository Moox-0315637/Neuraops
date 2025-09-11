# src/api/models/agent_command.py
"""
Pydantic models for agent command execution

CLAUDE.md: < 500 lignes, models pour communication agent-core
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum

from src.core.command_classifier import ExecutionLocation


# Constants pour descriptions Pydantic (SonarQube S1192)
COMMAND_ARGS_DESC = "Command arguments"
REQUEST_ID_DESC = "Request identifier"

class CommandStatus(str, Enum):
    """Status of command execution"""
    PENDING = "pending"
    EXECUTING = "executing" 
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentCommandRequest(BaseModel):
    """Request to execute command on agent"""
    command: str = Field(..., description="Main command (e.g., 'health', 'system')")
    args: List[str] = Field(default=[], description=COMMAND_ARGS_DESC)
    agent_name: str = Field(..., description="Target agent name")
    execution_location: ExecutionLocation = Field(..., description="Where to execute command")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    
    class Config:
        json_encoders = {
            ExecutionLocation: str
        }


class AgentCommandResponse(BaseModel):
    """Response from agent command execution"""
    success: bool = Field(..., description="Whether command succeeded")
    return_code: int = Field(default=0, description="Command return code")
    stdout: str = Field(default="", description="Command standard output")
    stderr: str = Field(default="", description="Command standard error")
    command: str = Field(..., description="Original command")
    agent_name: str = Field(..., description="Agent that executed command")
    execution_time_seconds: Optional[float] = Field(None, description="Execution duration")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    
    # Agent-specific data for hybrid commands
    agent_data: Optional[Dict[str, Any]] = Field(None, description="Raw agent data for hybrid processing")


class HybridCommandRequest(BaseModel):
    """Request for hybrid command execution (agent + core)"""
    command: str = Field(..., description="Main command")
    args: List[str] = Field(default=[], description=COMMAND_ARGS_DESC) 
    agent_name: str = Field(..., description="Source agent")
    agent_data: Dict[str, Any] = Field(..., description="Data collected by agent")
    ai_processing_required: bool = Field(default=True, description="Whether AI processing is needed")
    request_id: Optional[str] = Field(None, description=REQUEST_ID_DESC)


class CommandExecutionStatus(BaseModel):
    """Status of ongoing command execution"""
    request_id: str = Field(..., description=REQUEST_ID_DESC)
    command: str = Field(..., description="Command being executed")
    agent_name: str = Field(..., description="Target agent name")
    status: CommandStatus = Field(..., description="Current execution status")
    execution_location: ExecutionLocation = Field(..., description="Execution location")
    started_at: datetime = Field(..., description="Execution start time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Execution progress")
    current_step: Optional[str] = Field(None, description="Current execution step")


class AgentCapabilities(BaseModel):
    """Agent capabilities and supported commands"""
    agent_name: str = Field(..., description="Agent identifier")
    supported_commands: Dict[str, List[str]] = Field(..., description="Supported command modules")
    system_info: Dict[str, Any] = Field(..., description="Agent system information")
    version: str = Field(..., description="Agent version")
    last_seen: datetime = Field(default_factory=datetime.now, description="Last communication")


class CommandValidationError(BaseModel):
    """Command validation error details"""
    command: str = Field(..., description="Invalid command")
    args: List[str] = Field(default=[], description=COMMAND_ARGS_DESC)
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human readable error message")
    allowed_commands: Optional[List[str]] = Field(None, description="List of allowed commands")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class WebSocketCommandMessage(BaseModel):
    """WebSocket message for real-time command execution"""
    type: Literal["command_request", "command_result", "command_status", "command_cancel"]
    request_id: str = Field(..., description=REQUEST_ID_DESC)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Command request fields
    command: Optional[str] = None
    args: Optional[List[str]] = None
    timeout_seconds: Optional[int] = None
    
    # Command result fields  
    success: Optional[bool] = None
    return_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    agent_data: Optional[Dict[str, Any]] = None
    
    # Status update fields
    status: Optional[CommandStatus] = None
    progress_percent: Optional[int] = None
    current_step: Optional[str] = None


class FormattedCommandOutput(BaseModel):
    """Formatted command output for CLI display"""
    raw_output: str = Field(..., description="Raw command output")
    formatted_output: str = Field(..., description="Formatted for CLI display")
    output_format: Literal["table", "json", "text", "rich"] = Field(default="rich")
    metadata: Dict[str, Any] = Field(default={}, description="Output metadata")
    
    # CLI display options
    use_colors: bool = Field(default=True, description="Whether to use colors")
    use_tables: bool = Field(default=True, description="Whether to format as tables")
    compact_mode: bool = Field(default=False, description="Compact display mode")


class CommandMetrics(BaseModel):
    """Metrics for command execution"""
    total_executions: int = Field(default=0, description="Total command executions")
    successful_executions: int = Field(default=0, description="Successful executions")
    failed_executions: int = Field(default=0, description="Failed executions")
    average_execution_time: float = Field(default=0.0, description="Average execution time")
    agent_executions: int = Field(default=0, description="Agent-side executions")
    core_executions: int = Field(default=0, description="Core-side executions") 
    hybrid_executions: int = Field(default=0, description="Hybrid executions")
    last_execution: Optional[datetime] = Field(None, description="Last execution time")


class CommandAuditLog(BaseModel):
    """Audit log entry for command execution"""
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str = Field(..., description=REQUEST_ID_DESC)
    command: str = Field(..., description="Executed command")
    args: List[str] = Field(default=[], description=COMMAND_ARGS_DESC)
    agent_name: str = Field(..., description="Agent that executed command")
    execution_location: ExecutionLocation = Field(..., description="Execution location")
    success: bool = Field(..., description="Whether execution succeeded")
    execution_time_seconds: Optional[float] = Field(None, description="Execution duration")
    return_code: int = Field(default=0, description="Command return code")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context information")