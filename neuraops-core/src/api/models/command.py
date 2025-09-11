"""
Command Models for NeuraOps API

Pydantic models for command execution and orchestration.
Follows CLAUDE.md: < 150 lines, Safety-First validation.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from ...core.structured_output import SafetyLevel, SeverityLevel, ActionType


class CommandStatus(str, Enum):
    """Command execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CommandRequest(BaseModel):
    """Request to execute command on agent"""
    command: str = Field(..., min_length=1, max_length=1000)
    description: Optional[str] = Field(None, max_length=500)
    action_type: ActionType
    target_agents: List[str] = Field(..., min_items=1)
    safety_level: SafetyLevel = SafetyLevel.CAUTIOUS
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    requires_approval: bool = Field(default=True)
    environment: Optional[Dict[str, str]] = None
    
    @validator('command')
    def validate_command_safety(cls, v, values):
        """CLAUDE.md: Safety-First - Basic command validation"""
        dangerous_commands = ['rm -rf', 'mkfs', 'fdisk', 'dd if=', 'shutdown', 'reboot']
        if any(cmd in v.lower() for cmd in dangerous_commands):
            if values.get('safety_level') != SafetyLevel.DANGEROUS:
                raise ValueError(f"Command requires DANGEROUS safety level: {v}")
        return v


class CommandResponse(BaseModel):
    """Response from command execution"""
    command_id: str
    agent_id: str
    status: CommandStatus
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CommandExecution(BaseModel):
    """Command execution details"""
    command_id: str = Field(..., min_length=1)
    command: str
    description: Optional[str] = None
    action_type: ActionType
    safety_level: SafetyLevel
    status: CommandStatus = CommandStatus.PENDING
    requested_by: str  # agent_id
    target_agents: List[str]
    responses: List[CommandResponse] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300
    requires_approval: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class CommandApproval(BaseModel):
    """Command approval request"""
    command_id: str
    approved: bool
    approver_id: str
    reason: Optional[str] = None


class CommandBatch(BaseModel):
    """Batch command execution"""
    batch_id: str
    commands: List[CommandRequest]
    execution_mode: str = Field(default="sequential", pattern="^(sequential|parallel)$")
    fail_fast: bool = Field(default=True)
    created_by: str


class CommandHistory(BaseModel):
    """Command execution history"""
    executions: List[CommandExecution]
    total_count: int
    success_count: int
    failed_count: int
    pending_count: int


class CommandStats(BaseModel):
    """Command execution statistics"""
    total_commands: int
    success_rate: float = Field(..., ge=0, le=1)
    average_execution_time: float
    most_used_commands: List[str]
    error_patterns: List[str]
    safety_level_distribution: Dict[SafetyLevel, int]