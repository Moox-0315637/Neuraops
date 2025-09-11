"""
Alerts Routes for NeuraOps API

Simple proxy to system alerts endpoint for UI compatibility.
Follows CLAUDE.md: < 50 lines, Single Responsibility.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
import structlog

from ..models.responses import APIResponse
from ..routes.auth import get_current_user, UserInfo
from ..routes.system import Alert, get_alerts as system_get_alerts, acknowledge_alert as system_acknowledge_alert

logger = structlog.get_logger()
router = APIRouter()


@router.get("/alerts", response_model=APIResponse[List[Alert]])
async def get_alerts(
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgement status"),
    severity: Optional[str] = Query(None, description="Filter by severity level"), 
    limit: int = Query(50, le=100, description="Maximum number of alerts"),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    List system alerts - Proxy to system alerts endpoint
    
    CLAUDE.md: Simple proxy for UI compatibility
    """
    return await system_get_alerts(
        acknowledged=acknowledged,
        severity=severity,
        limit=limit,
        current_user=current_user
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=APIResponse[Alert])
async def acknowledge_alert(
    alert_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Acknowledge system alert - Proxy to system alerts endpoint
    
    CLAUDE.md: Simple proxy for UI compatibility
    """
    return await system_acknowledge_alert(
        alert_id=alert_id,
        current_user=current_user
    )