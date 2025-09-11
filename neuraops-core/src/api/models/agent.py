"""
Agent Models for NeuraOps API

Pydantic models for agent-related requests and responses.
Follows CLAUDE.md: < 150 lines, structured validation.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class AgentStatus(str, Enum):
    """Agent connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class AgentCapability(str, Enum):
    """Available agent capabilities"""
    LOGS = "logs"
    INFRASTRUCTURE = "infrastructure"
    INCIDENTS = "incidents"
    WORKFLOWS = "workflows"
    HEALTH = "health"
    METRICS = "metrics"
    COMMANDS = "commands"


class AgentRegistrationRequest(BaseModel):
    """Request to register new agent"""
    agent_name: str = Field(..., min_length=1, max_length=50)
    hostname: str = Field(..., min_length=1, max_length=255)
    capabilities: List[AgentCapability]
    api_key: str = Field(..., min_length=8)  # Allow shorter keys for "generate"
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('capabilities')
    def validate_capabilities(cls, v):
        if not v:
            raise ValueError("At least one capability required")
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if v != "generate" and len(v) < 32:
            raise ValueError("API key must be at least 32 characters or 'generate'")
        return v


class AgentRegistrationResponse(BaseModel):
    """Response for agent registration"""
    agent_id: str
    token: str
    expires_at: datetime
    message: str = "Agent registered successfully"


class AgentInfo(BaseModel):
    """Agent information"""
    agent_id: str
    agent_name: str
    hostname: str
    capabilities: List[AgentCapability]
    status: AgentStatus
    registered_at: datetime
    last_seen: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentUpdateRequest(BaseModel):
    """Request to update agent information"""
    capabilities: Optional[List[AgentCapability]] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentListResponse(BaseModel):
    """Response with list of agents"""
    agents: List[AgentInfo]
    total_count: int
    active_count: int


class AgentHeartbeat(BaseModel):
    """Agent heartbeat payload"""
    agent_id: str
    status: AgentStatus = AgentStatus.ACTIVE
    system_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentMetrics(BaseModel):
    """Agent performance metrics"""
    agent_id: str
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    active_tasks: int = Field(..., ge=0)
    completed_tasks: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    uptime_seconds: int = Field(..., ge=0)
    # Extended metrics for network and system info
    network_in: float = Field(default=0.0, ge=0)  # MB/s
    network_out: float = Field(default=0.0, ge=0)  # MB/s
    load_average: List[float] = Field(default=[0.0, 0.0, 0.0])  # 1min, 5min, 15min
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentTaskAssignment(BaseModel):
    """Task assignment to agent"""
    task_id: str
    agent_id: str
    task_type: str
    priority: int = Field(default=1, ge=1, le=5)
    payload: Dict[str, Any]
    timeout_seconds: Optional[int] = Field(default=300, ge=1)


class AgentResponse(BaseModel):
    """Generic agent response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)