"""
WebSocket Event Handlers for NeuraOps API

Event processing and routing following CLAUDE.md: < 150 lines.
Handles real-time events between API and agents.
"""
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timezone
import json
import time
import structlog

from .manager import ConnectionManager
from ...core.structured_output import SafetyLevel, SeverityLevel

logger = structlog.get_logger()


class WebSocketEventHandler:
    """
    WebSocket event handler and router
    
    CLAUDE.md: Single Responsibility - Event handling only
    CLAUDE.md: AI-First - Route events to appropriate AI processing
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.event_handlers: Dict[str, Callable] = {}
        self._memory_cache: Dict[str, Any] = {}  # In-memory cache storage
        self._cache_ttl = 300  # Cache TTL: 5 minutes
        self._register_default_handlers()
    
    def _get_current_timestamp(self) -> datetime:
        """
        Get current UTC timestamp in timezone-aware format
        
        CLAUDE.md: Helper function < 10 lines
        Fixes SonarQube S6903: Replace deprecated datetime.utcnow()
        """
        return datetime.now(timezone.utc)
    
    def _register_default_handlers(self):
        """Register default event handlers"""
        self.event_handlers.update({
            "heartbeat": self.handle_heartbeat,
            "task_status": self.handle_task_status,
            "command_result": self.handle_command_result,
            "system_alert": self.handle_system_alert,
            "agent_error": self.handle_agent_error,
            "metrics_update": self.handle_metrics_update
        })
    
    async def handle_message(self, agent_id: str, message_data: Dict[str, Any]):
        """
        Route incoming WebSocket message to appropriate handler
        
        CLAUDE.md: Fail Fast - Validate message format early
        """
        try:
            event_type = self._validate_message_format(agent_id, message_data)
            if not event_type:
                return
            
            handler = self._get_event_handler(agent_id, event_type)
            if not handler:
                return
            
            await self._execute_handler(handler, agent_id, message_data)
            
        except Exception as e:
            logger.error("Error handling WebSocket message",
                        agent_id=agent_id, error=str(e))
    
    def _validate_message_format(self, agent_id: str, message_data: Dict[str, Any]) -> Optional[str]:
        """
        Validate message format and extract event type
        
        CLAUDE.md: Helper function < 10 lines for validation
        """
        event_type = message_data.get("type")
        if not event_type:
            logger.warning("Message missing event type", agent_id=agent_id)
        return event_type
    
    def _get_event_handler(self, agent_id: str, event_type: str) -> Optional[Callable]:
        """
        Get handler for event type with logging
        
        CLAUDE.md: Helper function < 10 lines for handler lookup
        """
        handler = self.event_handlers.get(event_type)
        if not handler:
            logger.warning("No handler for event type",
                          agent_id=agent_id, event_type=event_type)
        return handler
    
    async def _execute_handler(self, handler: Callable, agent_id: str, message_data: Dict[str, Any]):
        """
        Execute handler with proper async/sync handling
        
        CLAUDE.md: Helper function < 10 lines for execution
        """
        import inspect
        if inspect.iscoroutinefunction(handler):
            await handler(agent_id, message_data)
        else:
            handler(agent_id, message_data)

    def _cache_heartbeat(self, agent_id: str, data: Dict[str, Any]):
        """Cache heartbeat with hybrid storage following CLAUDE.md < 10 lines"""
        try:
            key = f"heartbeat:{agent_id}"
            self._memory_cache[key] = {**data, "cached_at": time.time()}
            logger.debug("Heartbeat cached", agent_id=agent_id)
        except Exception as e:
            logger.warning("Failed to cache heartbeat", agent_id=agent_id, error=str(e))
    
    def _cache_command_result(self, data: Dict[str, Any]):
        """Cache command execution result following CLAUDE.md < 10 lines"""
        try:
            command_id = data.get("command_id")
            key = f"command:{command_id}"
            self._memory_cache[key] = {**data, "cached_at": time.time()}
            logger.debug("Command result cached", command_id=command_id)
        except Exception as e:
            logger.warning("Failed to cache command result", error=str(e))
    
    def _cache_agent_error(self, data: Dict[str, Any]):
        """Cache agent error for analysis following CLAUDE.md < 10 lines"""
        try:
            error_type = data.get("error_type")
            agent_id = data.get("agent_id")
            key = f"error:{agent_id}:{error_type}:{time.time()}"
            self._memory_cache[key] = {**data, "cached_at": time.time()}
            logger.debug("Agent error cached", error_type=error_type)
        except Exception as e:
            logger.warning("Failed to cache agent error", error=str(e))
    
    def _cache_agent_metrics(self, data: Dict[str, Any]):
        """Cache agent metrics with timestamp following CLAUDE.md < 10 lines"""
        try:
            agent_id = data.get("agent_id")
            timestamp = int(time.time())
            key = f"metrics:{agent_id}:{timestamp}"
            self._memory_cache[key] = {**data, "cached_at": time.time()}
            logger.debug("Agent metrics cached", agent_id=agent_id, metrics_count=len(data.get("metrics", {})))
        except Exception as e:
            logger.warning("Failed to cache agent metrics", error=str(e))

    def _cleanup_expired_cache(self):
        """Clean up expired cache entries following CLAUDE.md < 10 lines"""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, data in self._memory_cache.items()
                if current_time - data.get("cached_at", 0) > self._cache_ttl
            ]
            for key in expired_keys:
                del self._memory_cache[key]
            if expired_keys:
                logger.debug("Cache cleanup completed", expired_count=len(expired_keys))
        except Exception as e:
            logger.warning("Cache cleanup failed", error=str(e))

    def _store_heartbeat_data(self, agent_id: str, timestamp: datetime):
        """Store heartbeat data for agent monitoring following CLAUDE.md < 10 lines"""
        heartbeat_data = {
            "agent_id": agent_id,
            "last_heartbeat": timestamp.isoformat(),
            "status": "online"
        }
        self._cache_heartbeat(agent_id, heartbeat_data)

    def _store_command_execution(self, agent_id: str, command_data: Dict[str, Any]):
        """Store command execution result following CLAUDE.md < 10 lines"""
        execution_record = {
            "command_id": command_data.get("command_id"),
            "agent_id": agent_id,
            "exit_code": command_data.get("exit_code"),
            "success": command_data.get("exit_code") == 0,
            "timestamp": self._get_current_timestamp().isoformat()
        }
        self._cache_command_result(execution_record)

    def _store_agent_error(self, agent_id: str, error_data: Dict[str, Any]):
        """Store agent error for analysis following CLAUDE.md < 10 lines"""
        error_record = {
            "agent_id": agent_id,
            "error_type": error_data.get("error_type"),
            "error_message": error_data.get("error"),
            "timestamp": self._get_current_timestamp().isoformat(),
            "severity": "error"
        }
        self._cache_agent_error(error_record)

    def _store_agent_metrics(self, agent_id: str, metrics_data: Dict[str, Any]):
        """Store agent metrics with timestamp following CLAUDE.md < 10 lines"""
        metrics_record = {
            "agent_id": agent_id,
            "metrics": metrics_data.get("metrics", {}),
            "timestamp": self._get_current_timestamp().isoformat(),
            "collected_at": self._get_current_timestamp()
        }
        self._cache_agent_metrics(metrics_record)
    
    async def handle_heartbeat(self, agent_id: str, data: Dict[str, Any]):
        """
        Process agent heartbeat
        
        CLAUDE.md: Simple heartbeat processing
        """
        logger.debug("Heartbeat received", agent_id=agent_id)
        
        self._store_heartbeat_data(agent_id, self._get_current_timestamp())
        
        # Respond with acknowledgment
        response = {
            "type": "heartbeat_ack",
            "timestamp": self._get_current_timestamp().isoformat(),
            "server_time": self._get_current_timestamp().isoformat()
        }
        await self.connection_manager.send_personal_message(response, agent_id)
    
    async def handle_task_status(self, agent_id: str, data: Dict[str, Any]):
        """
        Process task status update from agent
        
        CLAUDE.md: AI-First - Analyze task progress
        """
        task_id = data.get("task_id")
        status = data.get("status")
        progress = data.get("progress", 0)
        
        logger.info("Task status update",
                   agent_id=agent_id, task_id=task_id, 
                   status=status, progress=progress)
        
        # Broadcast to other interested agents
        if status in ["completed", "failed"]:
            broadcast_msg = {
                "type": "task_completed",
                "agent_id": agent_id,
                "task_id": task_id,
                "status": status,
                "result": data.get("result")
            }
            await self._broadcast_task_completion(broadcast_msg, agent_id)
    
    async def _broadcast_task_completion(self, message: Dict[str, Any], exclude_agent: str):
        """
        Helper to broadcast task completion message
        
        CLAUDE.md: Helper function < 10 lines for broadcast
        """
        await self.connection_manager.broadcast_system_message(message, exclude=[exclude_agent])
    
    async def handle_command_result(self, agent_id: str, data: Dict[str, Any]):
        """
        Process command execution result
        
        CLAUDE.md: Safety-First - Validate command results
        """
        command_id = data.get("command_id")
        exit_code = data.get("exit_code", -1)
        
        logger.info("Command result received",
                   agent_id=agent_id, command_id=command_id,
                   exit_code=exit_code, success=(exit_code == 0))
        
        self._store_command_execution(agent_id, data)
        
        # Notify command requester if different from executor
        requester_id = data.get("requested_by")
        if requester_id and requester_id != agent_id:
            notification = {
                "type": "command_completed",
                "command_id": command_id,
                "executor_agent": agent_id,
                "exit_code": exit_code,
                "success": exit_code == 0
            }
            await self.connection_manager.send_personal_message(notification, requester_id)
    
    async def handle_system_alert(self, agent_id: str, data: Dict[str, Any]):
        """
        Process system alert from agent
        
        CLAUDE.md: Safety-First - Escalate critical alerts
        """
        alert_type = data.get("alert_type", "unknown")
        severity = data.get("severity", SeverityLevel.INFO.value)
        message = data.get("message", "")
        
        logger.warning("System alert received",
                      agent_id=agent_id, alert_type=alert_type,
                      severity=severity, message=message)
        
        # Broadcast critical alerts to all agents
        if severity in [SeverityLevel.ERROR.value, SeverityLevel.CRITICAL.value]:
            alert_broadcast = {
                "type": "critical_alert",
                "source_agent": agent_id,
                "alert_type": alert_type,
                "severity": severity,
                "message": message
            }
            await self._broadcast_critical_alert(alert_broadcast)
    
    async def _broadcast_critical_alert(self, alert: Dict[str, Any]):
        """
        Helper to broadcast critical system alerts
        
        CLAUDE.md: Helper function < 10 lines for critical alerts
        """
        await self.connection_manager.broadcast_system_message(alert)
    
    def handle_agent_error(self, agent_id: str, data: Dict[str, Any]):
        """
        Process agent error report
        
        CLAUDE.md: Fail Fast - Handle errors immediately
        """
        error_type = data.get("error_type", "unknown")
        error_message = data.get("error", "")
        
        logger.error("Agent error reported",
                    agent_id=agent_id, error_type=error_type,
                    error_message=error_message)
        
        self._store_agent_error(agent_id, data)
    
    def handle_metrics_update(self, agent_id: str, data: Dict[str, Any]):
        """
        Process agent metrics update
        
        CLAUDE.md: Simple metrics collection
        """
        metrics = data.get("metrics", {})
        
        logger.debug("Metrics update received",
                    agent_id=agent_id, cpu=metrics.get("cpu_usage"))
        
        self._store_agent_metrics(agent_id, data)