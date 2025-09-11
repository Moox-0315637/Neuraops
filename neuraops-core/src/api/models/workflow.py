"""
Workflow Models for NeuraOps API

Pydantic models for AI workflow orchestration.
Follows CLAUDE.md: < 150 lines, AI-First architecture.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from ...core.structured_output import SafetyLevel, SeverityLevel


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepType(str, Enum):
    """Types of workflow steps"""
    COMMAND = "command"
    ANALYSIS = "analysis"
    DECISION = "decision"
    NOTIFICATION = "notification"
    APPROVAL = "approval"
    WAIT = "wait"


class WorkflowStep(BaseModel):
    """Individual step in workflow"""
    step_id: str
    name: str
    step_type: WorkflowStepType
    description: Optional[str] = None
    
    # Step configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution context
    depends_on: List[str] = Field(default_factory=list)  # step_ids
    condition: Optional[str] = None  # AI-evaluated condition
    timeout_seconds: Optional[int] = Field(default=600, ge=1)
    retry_count: int = Field(default=0, ge=0, le=3)
    
    # Safety validation
    safety_level: SafetyLevel = SafetyLevel.CAUTIOUS
    requires_approval: bool = Field(default=False)


class WorkflowTemplate(BaseModel):
    """Reusable workflow template"""
    template_id: str
    name: str
    description: str
    category: str = Field(..., pattern="^(infrastructure|incident|maintenance|deployment)$")
    steps: List[WorkflowStep]
    
    # Template metadata
    version: str = "1.0.0"
    author: str
    tags: List[str] = Field(default_factory=list)
    
    # Usage constraints
    min_safety_level: SafetyLevel = SafetyLevel.CAUTIOUS
    required_capabilities: List[str] = Field(default_factory=list)
    
    @validator('steps')
    def validate_steps_dependencies(cls, v):
        """Validate step dependencies form valid DAG"""
        step_ids = {step.step_id for step in v}
        for step in v:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"Step {step.step_id} depends on non-existent step {dep}")
        return v


class WorkflowExecution(BaseModel):
    """Active workflow execution instance"""
    execution_id: str
    workflow_name: str
    template_id: Optional[str] = None
    
    # Execution context
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: List[WorkflowStep]
    current_step: Optional[str] = None  # step_id
    
    # Agent assignment
    assigned_agents: List[str] = Field(default_factory=list)
    created_by: str
    
    # Execution tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results and context
    step_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class WorkflowCreateRequest(BaseModel):
    """Request to create new workflow"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    template_id: Optional[str] = None
    steps: Optional[List[WorkflowStep]] = None
    assigned_agents: List[str] = Field(default_factory=list)
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    auto_start: bool = Field(default=False)


class WorkflowInfo(BaseModel):
    """Workflow information for UI display"""
    id: str
    name: str
    description: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.DRAFT
    steps: List[WorkflowStep] = Field(default_factory=list)
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    assigned_agents: List[str] = Field(default_factory=list)


class WorkflowResponse(BaseModel):
    """Generic workflow response"""
    success: bool
    message: str
    execution_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None