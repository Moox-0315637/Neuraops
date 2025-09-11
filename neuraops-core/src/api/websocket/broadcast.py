"""
WebSocket Broadcasting Utilities for NeuraOps API

Message broadcasting and notification system following CLAUDE.md: < 100 lines.
Provides specialized broadcasting for different event types.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from .manager import ConnectionManager
from ...core.structured_output import SafetyLevel, SeverityLevel

logger = structlog.get_logger()


class BroadcastService:
    """
    Specialized broadcasting service for NeuraOps events
    
    CLAUDE.md: Single Responsibility - Broadcasting only
    CLAUDE.md: KISS - Simple broadcast patterns
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def broadcast_command_assignment(
        self, 
        command_id: str, 
        target_agents: List[str],
        command_details: Dict[str, Any]
    ):
        """
        Broadcast command assignment to target agents
        
        CLAUDE.md: Safety-First - Include safety information
        """
        message = {
            "type": "command_assignment",
            "command_id": command_id,
            "command": command_details.get("command"),
            "safety_level": command_details.get("safety_level"),
            "timeout_seconds": command_details.get("timeout_seconds", 300),
            "requires_approval": command_details.get("requires_approval", False)
        }
        
        await self.connection_manager.broadcast_message(message, target_agents)
        logger.info("Command assignment broadcasted",
                   command_id=command_id, target_count=len(target_agents))
    
    async def broadcast_workflow_update(
        self,
        workflow_id: str,
        status: str,
        current_step: Optional[str] = None,
        assigned_agents: List[str] = None
    ):
        """
        Broadcast workflow status update
        
        CLAUDE.md: AI-First - Workflow orchestration updates
        """
        message = {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "status": status,
            "current_step": current_step
        }
        
        target_agents = assigned_agents or list(self.connection_manager.active_connections.keys())
        await self.connection_manager.broadcast_message(message, target_agents)
        
        logger.info("Workflow update broadcasted",
                   workflow_id=workflow_id, status=status)
    
    async def broadcast_system_maintenance(
        self,
        maintenance_type: str,
        message: str,
        scheduled_time: Optional[datetime] = None
    ):
        """
        Broadcast system maintenance notification
        
        CLAUDE.md: Fail Fast - Early maintenance warnings
        """
        broadcast_message = {
            "type": "system_maintenance",
            "maintenance_type": maintenance_type,
            "message": message,
            "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
            "priority": "high"
        }
        
        await self.connection_manager.broadcast_system_message(broadcast_message)
        logger.warning("System maintenance broadcasted",
                      maintenance_type=maintenance_type)
    
    async def broadcast_security_alert(
        self,
        alert_type: str,
        severity: SeverityLevel,
        details: Dict[str, Any]
    ):
        """
        Broadcast security alert to all agents
        
        CLAUDE.md: Safety-First - Immediate security notifications
        """
        alert_message = {
            "type": "security_alert",
            "alert_type": alert_type,
            "severity": severity.value,
            "details": details,
            "action_required": severity in [SeverityLevel.ERROR, SeverityLevel.CRITICAL]
        }
        
        await self.connection_manager.broadcast_system_message(alert_message)
        logger.critical("Security alert broadcasted",
                       alert_type=alert_type, severity=severity.value)