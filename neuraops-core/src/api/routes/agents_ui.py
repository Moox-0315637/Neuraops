"""
Actions Agent étendues pour l'UI NeuraOps.

CLAUDE.md: Respect des 500 lignes maximum par fichier
CLAUDE.md: Single Responsibility - Actions agent pour UI
"""
from typing import List, Optional, Any
from datetime import datetime, timezone
import structlog
from uuid import uuid4
import json

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from pydantic import BaseModel, Field

from ..models.responses import APIResponse
from ..routes.auth import get_current_user, UserInfo
from ..models.agent import AgentInfo
from ...core.structured_output import SeverityLevel
from ..services.agent_service import AgentService
from ..services.agent_command_service import get_agent_command_service
from ..services.agent_management import retrieve_registered_agents
from ..dependencies import get_redis_client

logger = structlog.get_logger()

# Configuration
router = APIRouter(prefix="/agents", tags=["Agent UI Actions"])

# Models supplémentaires pour les actions UI
class LogEntry(BaseModel):
    """Entrée de log d'un agent."""
    id: str
    timestamp: datetime
    level: str
    message: str
    source: str
    metadata: Optional[dict] = None

class AgentCommand(BaseModel):
    """Commande à exécuter sur un agent."""
    command: str = Field(..., min_length=1, description="Commande à exécuter")
    timeout: Optional[int] = Field(default=30, description="Timeout en secondes")

class AgentCommandResult(BaseModel):
    """Résultat d'exécution d'une commande."""
    command_id: str
    status: str = Field(..., description="pending, running, completed, failed")
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

class SystemMetrics(BaseModel):
    """Métriques système d'un agent."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_in: float
    network_out: float
    load_average: List[float]
    uptime: int = Field(..., description="Uptime en secondes")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Helper function for WebSocket validation
def _validate_agent_connection(websocket_manager, agent_id: str) -> Optional[APIResponse]:
    """Validate agent WebSocket connection - CLAUDE.md < 10 lines"""
    if not websocket_manager.is_agent_connected(agent_id):
        return APIResponse(
            status="error",
            message=f"Agent {agent_id} not connected via WebSocket",
            data={"agent_id": agent_id, "status": "agent_not_connected", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
    return None

async def _send_agent_command(websocket_manager, agent_id: str, action: str, current_user: UserInfo) -> APIResponse:
    """Send command to agent via WebSocket - CLAUDE.md < 15 lines"""
    command_message = {"type": "agent_command", "action": action, "command_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat()}
    success = await websocket_manager.send_personal_message(command_message, agent_id)
    
    if success:
        logger.info(f"Agent {action} command sent", agent_id=agent_id, user=current_user.username)
        return APIResponse(status="success", message=f"Agent {agent_id} {action} command sent", data={"agent_id": agent_id, "action": action, "status": "command_sent", "timestamp": datetime.now(timezone.utc).isoformat()})
    else:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to send {action} command to agent {agent_id}")

@router.get("/", response_model=APIResponse[List[AgentInfo]])
async def list_agents_ui(
    current_user: UserInfo = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """
    List all registered agents for UI.
    Uses JWT authentication instead of AgentAuth.
    """
    try:
        
        # Use same service as main agents route but with JWT auth
        agents_response = await retrieve_registered_agents(redis_client, page=1, page_size=100)
        
        if agents_response.total_count == 0:
            logger.info("No registered agents found for UI")
            return APIResponse(
                status="success", 
                message="No agents registered", 
                data=[]
            )
        
        logger.debug("Agents retrieved for UI", count=len(agents_response.agents), user=current_user.username)
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(agents_response.agents)} agents for UI",
            data=agents_response.agents
        )
        
    except Exception as e:
        logger.error("Failed to list agents for UI", error=str(e), user=current_user.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent list for UI"
        )

@router.get("/agents/", response_model=APIResponse[List[AgentInfo]])
async def list_agents_ui_alt(
    current_user: UserInfo = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """
    Alternative endpoint for UI agents list at /api/agents/
    Duplicate of list_agents_ui for UI compatibility.
    """
    return await list_agents_ui(current_user, redis_client)

@router.get("/agents/debug", response_model=APIResponse[List[AgentInfo]])
async def debug_list_agents(redis_client = Depends(get_redis_client)):
    """
    DEBUG ENDPOINT - No auth required
    Temporary endpoint to test agent listing without authentication.
    REMOVE THIS IN PRODUCTION!
    """
    try:
        
        # Use same service as main agents route but without auth
        agents_response = await retrieve_registered_agents(redis_client, page=1, page_size=100)
        
        if agents_response.total_count == 0:
            logger.info("DEBUG: No registered agents found")
            return APIResponse(
                status="success", 
                message="No agents registered", 
                data=[]
            )
        
        logger.info("DEBUG: Agents retrieved", count=len(agents_response.agents))
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(agents_response.agents)} agents (DEBUG)",
            data=agents_response.agents
        )
        
    except Exception as e:
        logger.error("DEBUG: Failed to list agents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DEBUG: Failed to retrieve agent list: {str(e)}"
        )

@router.post("/{agent_id}/start", response_model=APIResponse[dict])
async def start_agent(
    request: Request,
    agent_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Démarre un agent arrêté.
    """
    try:
        websocket_manager = request.app.state.websocket_manager
        connection_error = _validate_agent_connection(websocket_manager, agent_id)
        if connection_error:
            connection_error.data["action"] = "start"
            return connection_error
        
        return await _send_agent_command(websocket_manager, agent_id, "start", current_user)
        
    except Exception as e:
        logger.error("Erreur lors du démarrage de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent {agent_id}"
        )

@router.post("/{agent_id}/stop", response_model=APIResponse[dict])
async def stop_agent(
    request: Request,
    agent_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Arrête un agent en cours d'exécution.
    """
    try:
        websocket_manager = request.app.state.websocket_manager
        connection_error = _validate_agent_connection(websocket_manager, agent_id)
        if connection_error:
            connection_error.data["action"] = "stop"
            return connection_error
        
        return await _send_agent_command(websocket_manager, agent_id, "stop", current_user)
        
    except Exception as e:
        logger.error("Erreur lors de l'arrêt de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent {agent_id}"
        )

@router.post("/{agent_id}/restart", response_model=APIResponse[dict])
async def restart_agent(
    request: Request,
    agent_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Redémarre un agent (arrêt puis démarrage).
    """
    try:
        websocket_manager = request.app.state.websocket_manager
        connection_error = _validate_agent_connection(websocket_manager, agent_id)
        if connection_error:
            connection_error.data["action"] = "restart"
            return connection_error
        
        return await _send_agent_command(websocket_manager, agent_id, "restart", current_user)
        
    except Exception as e:
        logger.error("Erreur lors du redémarrage de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart agent {agent_id}"
        )

@router.get("/{agent_id}/logs", response_model=APIResponse[List[LogEntry]])
async def get_agent_logs(
    request: Request,
    agent_id: str,
    level: Optional[str] = Query(None, description="Filtrer par niveau (INFO, WARNING, ERROR)"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Récupère les logs d'un agent spécifique.
    """
    try:
        # Vérifier l'existence de l'agent
        _verify_agent_exists(agent_id)
        
        # Récupérer les logs depuis Redis
        agent_logs = await _fetch_agent_logs_from_redis(agent_id, level, limit)
        
        # Si pas de logs, vérifier si l'agent est connecté
        if not agent_logs:
            agent_logs = _get_fallback_logs(request, agent_id)
        
        logger.debug("Agent logs retrieved", agent_id=agent_id, count=len(agent_logs))
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(agent_logs)} log entries for agent {agent_id}",
            data=agent_logs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la récupération des logs de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logs for agent {agent_id}"
        )


def _verify_agent_exists(agent_id: str) -> None:
    """Vérifie qu'un agent existe."""
    redis_client = get_redis_client()
    agent_service = AgentService(jwt_handler=None, redis_client=redis_client)
    agent_info = agent_service.get_agent_info(agent_id)
    
    if not agent_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )


async def _fetch_agent_logs_from_redis(
    agent_id: str,
    level: Optional[str],
    limit: int
) -> List[LogEntry]:
    """Récupère les logs depuis Redis."""
    redis_client = get_redis_client()
    if not redis_client:
        return []
    
    try:
        # Récupérer les clés de logs pour cet agent
        log_keys = await redis_client.keys(f"agent_logs:{agent_id}:*")
        
        # Traiter uniquement les derniers logs selon la limite
        log_keys = log_keys[-limit:] if log_keys else []
        
        agent_logs = []
        for key in log_keys:
            log_entry = await _process_log_entry(redis_client, key, level)
            if log_entry:
                agent_logs.append(log_entry)
        
        return agent_logs
        
    except Exception as e:
        logger.warning("Failed to retrieve logs from Redis", agent_id=agent_id, error=str(e))
        return []


async def _process_log_entry(
    redis_client: Any,
    key: str,
    level_filter: Optional[str]
) -> Optional[LogEntry]:
    """Traite une entrée de log depuis Redis."""
    log_data = await redis_client.get(key)
    if not log_data:
        return None
    
    log_entry_data = json.loads(log_data)
    
    # Filtrage par niveau
    if level_filter and log_entry_data.get("level", "").upper() != level_filter.upper():
        return None
    
    return LogEntry(
        id=log_entry_data.get("id", str(uuid4())),
        timestamp=datetime.fromisoformat(
            log_entry_data.get("timestamp", datetime.now(timezone.utc).isoformat())
        ),
        level=log_entry_data.get("level", "INFO"),
        message=log_entry_data.get("message", ""),
        source=log_entry_data.get("source", "agent"),
        metadata=log_entry_data.get("metadata")
    )


def _get_fallback_logs(request: Request, agent_id: str) -> List[LogEntry]:
    """Retourne des logs par défaut si l'agent est connecté mais sans historique."""
    if request.app.state.websocket_manager.is_agent_connected(agent_id):
        return [LogEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            level="INFO",
            message="Agent connected - no historical logs available",
            source="system"
        )]
    return []

@router.get("/{agent_id}/metrics-ui", response_model=APIResponse[SystemMetrics])
async def get_agent_metrics(
    request: Request,
    agent_id: str,
    current_user: UserInfo = Depends(get_current_user),
    redis_client = Depends(get_redis_client)  # Use dependency injection
):
    """
    Récupère les métriques système d'un agent spécifique.
    UI-specific endpoint to avoid route conflict with agent-only endpoint.
    """
    try:
        logger.debug("Getting metrics for agent", agent_id=agent_id, user=current_user.username)
        
        # Try direct Redis lookup for metrics first
        if redis_client:
            try:
                metrics_key = f"agent_metrics:{agent_id}"
                metrics_data = await redis_client.get(metrics_key)
                if metrics_data:
                    metrics_dict = json.loads(metrics_data)
                    metrics = SystemMetrics(
                        cpu_usage=metrics_dict.get("cpu_usage", 0.0), 
                        memory_usage=metrics_dict.get("memory_usage", 0.0),
                        disk_usage=metrics_dict.get("disk_usage", 0.0), 
                        network_in=metrics_dict.get("network_in", 0.0),
                        network_out=metrics_dict.get("network_out", 0.0), 
                        load_average=metrics_dict.get("load_average", [0.0, 0.0, 0.0]),
                        uptime=metrics_dict.get("uptime", 0), 
                        timestamp=datetime.fromisoformat(metrics_dict.get("timestamp", datetime.now(timezone.utc).isoformat()))
                    )
                    
                    logger.debug("Metrics retrieved from Redis", agent_id=agent_id)
                    return APIResponse(status="success", message=f"Retrieved stored metrics for agent {agent_id}", data=metrics)
            except Exception as e:
                logger.warning("Failed to retrieve metrics from Redis", agent_id=agent_id, error=str(e))
        
        # For now, always return default metrics to avoid service dependency issues
        default_metrics = SystemMetrics(
            cpu_usage=0.0, memory_usage=0.0, disk_usage=0.0, network_in=0.0, network_out=0.0,
            load_average=[0.0, 0.0, 0.0], uptime=0, timestamp=datetime.now(timezone.utc)
        )
        
        logger.info("Returning default metrics for agent", agent_id=agent_id)
        
        return APIResponse(
            status="success",
            message=f"Retrieved default metrics for agent {agent_id}",
            data=default_metrics
        )
        
    except Exception as e:
        logger.error("Erreur lors de la récupération des métriques de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics for agent {agent_id}"
        )

@router.post("/{agent_id}/execute", response_model=APIResponse[AgentCommandResult])
async def execute_command_on_agent(
    agent_id: str,
    command_data: AgentCommand,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Exécute une commande sur un agent spécifique.
    """
    try:
        # Utiliser AgentCommandService existant pour exécution
        command_service = get_agent_command_service()
        
        # Parser command et args depuis command_data.command
        command_parts = command_data.command.strip().split()
        main_command = command_parts[0] if command_parts else "status"
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        # Exécuter commande via service
        result = await command_service.execute_command(
            command=main_command,
            args=args, 
            agent_name=agent_id,
            timeout_seconds=command_data.timeout or 30
        )
        
        # Convertir result en AgentCommandResult
        command_result = AgentCommandResult(
            command_id=result.get("request_id", str(uuid4())),
            status="completed" if result.get("success") else "failed",
            output=result.get("stdout", ""),
            error=result.get("stderr", ""),
            exit_code=result.get("return_code", 0),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Command executed on agent", 
                   agent_id=agent_id, 
                   command=command_data.command,
                   success=result.get("success", False),
                   user=current_user.username)
        
        return APIResponse(
            status="success",
            message=f"Command executed on agent {agent_id}",
            data=command_result
        )
        
    except Exception as e:
        logger.error("Erreur lors de l'exécution de la commande sur l'agent", agent_id=agent_id, command=command_data.command, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute command on agent {agent_id}"
        )

@router.get("/{agent_id}/status", response_model=APIResponse[dict])
async def get_agent_status(
    request: Request,
    agent_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Récupère le statut d'un agent spécifique.
    """
    try:
        # Utiliser AgentService existant
        redis_client = get_redis_client()
        agent_service = AgentService(jwt_handler=None, redis_client=redis_client)
        
        # Récupérer info agent depuis cache/storage
        agent_info = agent_service.get_agent_info(agent_id)
        
        if not agent_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Vérifier connexion WebSocket
        websocket_manager = request.app.state.websocket_manager
        is_connected = websocket_manager.is_agent_connected(agent_id)
        
        # Récupérer métriques récentes
        recent_metrics = await agent_service.get_agent_metrics(agent_id, minutes=5)
        
        agent_status = {
            "agent_id": agent_id,
            "status": "connected" if is_connected else agent_info.status,
            "version": getattr(agent_info, 'version', '1.0.0'),
            "last_heartbeat": agent_info.last_seen.isoformat() if agent_info.last_seen else None,
            "uptime": int((datetime.now(timezone.utc) - agent_info.registered_at).total_seconds()) if agent_info.registered_at else 0,
            "is_connected": is_connected,
            "capabilities": [cap.value if hasattr(cap, 'value') else str(cap) for cap in agent_info.capabilities],
            "recent_metrics": len(recent_metrics) if recent_metrics else 0
        }
        
        logger.debug("Agent status retrieved", agent_id=agent_id, status=agent_status["status"])
        
        return APIResponse(
            status="success",
            message=f"Retrieved status for agent {agent_id}",
            data=agent_status
        )
        
    except Exception as e:
        logger.error("Erreur lors de la récupération du statut de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status for agent {agent_id}"
        )

@router.put("/{agent_id}/config", response_model=APIResponse[dict])
async def update_agent_config(
    request: Request,
    agent_id: str,
    config_data: dict,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Met à jour la configuration d'un agent spécifique.
    """
    try:
        websocket_manager = request.app.state.websocket_manager
        
        # Vérifier connexion agent 
        if not websocket_manager.is_agent_connected(agent_id):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Agent {agent_id} not connected via WebSocket"
            )
        
        # Valider config_data structure
        if not isinstance(config_data, dict) or not config_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid configuration data"
            )
        
        # Envoyer commande update config via WebSocket
        config_message = {
            "type": "config_update",
            "config_data": config_data,
            "command_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.username
        }
        
        success = await websocket_manager.send_personal_message(config_message, agent_id)
        
        if success:
            # Stocker config dans Redis pour persistance
            redis_client = get_redis_client()
            
            if redis_client:
                config_key = f"agent_config:{agent_id}"
                await redis_client.setex(
                    config_key,
                    86400 * 7,  # 7 jours TTL
                    json.dumps({
                        "config": config_data,
                        "updated_by": current_user.username, 
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                )
            
            updated_config = {
                "agent_id": agent_id,
                "config": config_data,
                "updated_by": current_user.username,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "configuration_updated"
            }
            
            logger.info("Agent configuration updated", 
                       agent_id=agent_id, 
                       config_keys=list(config_data.keys()),
                       user=current_user.username)
            
            return APIResponse(
                status="success", 
                message=f"Configuration updated for agent {agent_id}",
                data=updated_config
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to send configuration update to agent {agent_id}"
            )
        
    except Exception as e:
        logger.error("Erreur lors de la mise à jour de la configuration de l'agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration for agent {agent_id}"
        )