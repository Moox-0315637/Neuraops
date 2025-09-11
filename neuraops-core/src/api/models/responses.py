"""
Common Response Models for NeuraOps API

Standardized response models following CLAUDE.md: < 150 lines.
Consistent API responses with proper error handling.
"""
from typing import Optional, Dict, Any, List, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

T = TypeVar('T')


class ResponseStatus(str, Enum):
    """API response status"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class ErrorCode(str, Enum):
    """Standard error codes"""
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT_ERROR = "timeout_error"


class APIError(BaseModel):
    """Error details in API response"""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    field: Optional[str] = None  # For validation errors


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper
    
    CLAUDE.md: Consistent structured outputs for AI validation
    """
    status: ResponseStatus
    message: str
    data: Optional[T] = None
    error: Optional[APIError] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[int] = None
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    service_name: str = "NeuraOps Core API"
    version: str = "1.1.0"
    status: str = "healthy"
    uptime_seconds: int
    dependencies: Dict[str, str] = Field(default_factory=dict)  # service -> status
    system_metrics: Optional[Dict[str, float]] = None  # CPU, memory, disk usage
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetricsResponse(BaseModel):
    """Metrics endpoint response"""
    total_agents: int
    active_agents: int
    total_commands: int
    successful_commands: int
    failed_commands: int
    average_response_time_ms: float
    system_load: Optional[Dict[str, float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response for list endpoints"""
    items: List[T]
    total_count: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    has_next: bool
    has_previous: bool


class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    total_requested: int
    successful: int
    failed: int
    partial: int = 0
    errors: List[APIError] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None


class AsyncOperationResponse(BaseModel):
    """Response for asynchronous operations"""
    operation_id: str
    status: str = "initiated"
    estimated_completion_time: Optional[datetime] = None
    progress_url: Optional[str] = None
    webhook_url: Optional[str] = None