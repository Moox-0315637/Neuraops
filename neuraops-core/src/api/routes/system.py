"""Routes système et monitoring pour l'UI NeuraOps - CLAUDE.md < 500 lignes"""
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import structlog

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from ..models.responses import APIResponse
from ..routes.auth import get_current_user, UserInfo
from ...core.structured_output import SeverityLevel
from ..services.agent_command_service import get_agent_command_service

logger = structlog.get_logger()

# Configuration
router = APIRouter(prefix="/system", tags=["System & Monitoring"])

# Constants pour messages d'erreur
ERROR_MSG_ACKNOWLEDGE_ALERT = "Failed to acknowledge alert"

# Models système et monitoring
class SystemMetrics(BaseModel):
    """Métriques système."""
    cpu_usage: float = Field(..., description="Usage CPU en pourcentage")
    memory_usage: float = Field(..., description="Usage mémoire en pourcentage")
    disk_usage: float = Field(..., description="Usage disque en pourcentage")
    network_in: float = Field(..., description="Trafic réseau entrant (MB/s)")
    network_out: float = Field(..., description="Trafic réseau sortant (MB/s)")
    active_agents: int = Field(..., description="Nombre d'agents actifs")
    running_workflows: int = Field(..., description="Workflows en cours")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Alert(BaseModel):
    """Alerte système."""
    id: str
    title: str
    message: str
    severity: SeverityLevel
    source: str = Field(..., description="Source de l'alerte")
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

class LogEntry(BaseModel):
    """Entrée de log système."""
    id: str
    timestamp: datetime
    level: str = Field(..., description="Niveau de log (DEBUG, INFO, WARNING, ERROR)")
    source: str = Field(..., description="Source du log")
    message: str
    metadata: Optional[dict] = None

class Command(BaseModel):
    """Commande exécutée."""
    id: str
    agent_id: str
    command: str
    status: str = Field(..., description="Status: pending, running, completed, failed")
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

# Database client pour gestion alertes
from ...integration.postgres_client import PostgreSQLClient

# Instance client DB globale
db_client = PostgreSQLClient()

# Implémentations DB réelles

@router.get("/metrics", response_model=APIResponse[SystemMetrics])
async def get_system_metrics(current_user: UserInfo = Depends(get_current_user)):
    """Récupère les métriques système globales depuis les vraies sources."""
    try:
        import psutil
        
        # Real system metrics using psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        # Convert network bytes to MB/s (approximation)
        network_in_mb = net_io.bytes_recv / (1024 * 1024) if net_io else 0.0
        network_out_mb = net_io.bytes_sent / (1024 * 1024) if net_io else 0.0
        
        # Get real active agents count from database
        if not db_client.connected:
            await db_client.connect()
        
        # Get agent statistics from database
        agents_data = await db_client.get_agents()
        active_agents = len([a for a in agents_data if a.get("status") == "active"])
        
        # Get running workflows from database
        workflows_data = await db_client.get_workflows()
        running_workflows = len([w for w in workflows_data if w.get("status") == "running"])
        
        metrics = SystemMetrics(
            cpu_usage=round(cpu_percent, 1),
            memory_usage=round(memory.percent, 1),
            disk_usage=round((disk.used / disk.total) * 100, 1),
            network_in=round(network_in_mb, 1),
            network_out=round(network_out_mb, 1),
            active_agents=active_agents,
            running_workflows=running_workflows
        )
        
    except Exception as e:
        logger.error("Failed to collect system metrics", error=str(e))
        # Fallback to basic metrics if psutil or database fails
        metrics = SystemMetrics(
            cpu_usage=0.0,
            memory_usage=0.0,
            disk_usage=0.0,
            network_in=0.0,
            network_out=0.0,
            active_agents=0,
            running_workflows=0
        )
    
    return APIResponse(
        status="success",
        message="System metrics retrieved",
        data=metrics
    )

@router.get("/alerts", response_model=APIResponse[List[Alert]])
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filtrer par sévérité"),
    acknowledged: Optional[bool] = Query(None, description="Filtrer par statut acquittement"),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserInfo = Depends(get_current_user)
):
    """Liste les alertes système depuis la base de données avec filtres."""
    try:
        # Connexion DB
        if not db_client.connected:
            await db_client.connect()
        
        # Get alerts from database
        alerts_data = await db_client.get_alerts(acknowledged=acknowledged, limit=limit)
        
        # Convert to Alert objects and apply severity filter
        alerts = []
        for alert_data in alerts_data:
            # Apply severity filter
            if severity and alert_data["severity"] != severity:
                continue
                
            alert = Alert(
                id=str(alert_data["id"]),
                title=alert_data["title"],
                message=alert_data["message"],
                severity=SeverityLevel(alert_data["severity"]),
                source=alert_data["source"],
                created_at=alert_data["created_at"],
                acknowledged=alert_data["acknowledged"],
                acknowledged_by=alert_data["acknowledged_by"],
                acknowledged_at=alert_data["acknowledged_at"]
            )
            alerts.append(alert)
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(alerts)} alerts",
            data=alerts
        )
        
    except Exception as e:
        logger.error("Failed to get alerts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )

@router.post("/alerts/{alert_id}/acknowledge", response_model=APIResponse[Alert])
async def acknowledge_alert(
    alert_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """Acquitte une alerte système dans la base de données."""
    try:
        # Connexion DB
        if not db_client.connected:
            await db_client.connect()
        
        # Check if alert exists and is not already acknowledged
        alerts_data = await db_client.get_alerts(limit=1000)  # Get all to find the specific one
        alert_data = next((a for a in alerts_data if str(a["id"]) == alert_id), None)
        
        if not alert_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        if alert_data["acknowledged"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alert already acknowledged"
            )
        
        # Acknowledge the alert in database
        success = await db_client.acknowledge_alert(alert_id, current_user.username)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MSG_ACKNOWLEDGE_ALERT
            )
        
        # Get updated alert data
        updated_alerts = await db_client.get_alerts(limit=1000)
        updated_alert_data = next((a for a in updated_alerts if str(a["id"]) == alert_id), None)
        
        if updated_alert_data:
            alert = Alert(
                id=str(updated_alert_data["id"]),
                title=updated_alert_data["title"],
                message=updated_alert_data["message"],
                severity=SeverityLevel(updated_alert_data["severity"]),
                source=updated_alert_data["source"],
                created_at=updated_alert_data["created_at"],
                acknowledged=updated_alert_data["acknowledged"],
                acknowledged_by=updated_alert_data["acknowledged_by"],
                acknowledged_at=updated_alert_data["acknowledged_at"]
            )
        
        return APIResponse(
            status="success",
            message="Alert acknowledged successfully",
            data=alert
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(ERROR_MSG_ACKNOWLEDGE_ALERT, alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MSG_ACKNOWLEDGE_ALERT
        )

@router.get("/logs", response_model=APIResponse[List[LogEntry]])
async def get_logs(
    level: Optional[str] = Query(None, description="Filtrer par niveau (DEBUG, INFO, WARNING, ERROR)"),
    source: Optional[str] = Query(None, description="Filtrer par source"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """Récupère les logs système depuis la base de données avec filtres."""
    try:
        # Connexion DB
        if not db_client.connected:
            await db_client.connect()
        
        # Get logs from database (assuming a get_logs method exists)
        logs_data = await db_client.get_logs(level=level, source=source, limit=limit)
        
        # Convert to LogEntry objects
        logs = []
        for log_data in logs_data:
            log_entry = LogEntry(
                id=str(log_data["id"]),
                timestamp=log_data["timestamp"],
                level=log_data["level"],
                source=log_data["source"],
                message=log_data["message"],
                metadata=log_data.get("metadata")
            )
            logs.append(log_entry)
        
        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(logs)} log entries",
            data=logs
        )
        
    except Exception as e:
        logger.error("Failed to get logs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve logs"
        )

@router.get("/commands", response_model=APIResponse[List[Command]])
async def get_commands(
    agent_id: Optional[str] = Query(None, description="Filtrer par agent"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Liste l'historique des commandes exécutées depuis la base de données.
    """
    try:
        # Connexion DB
        if not db_client.connected:
            await db_client.connect()
        
        # Get commands from database with filters
        commands_data = await db_client.get_commands(
            agent_id=agent_id, 
            status=status, 
            limit=limit
        )
        
        # Convert to Command objects
        commands = []
        for cmd_data in commands_data:
            command = Command(
                id=str(cmd_data["id"]),
                agent_id=cmd_data["agent_id"],
                command=cmd_data["command"],
                status=cmd_data["status"],
                output=cmd_data.get("output"),
                error=cmd_data.get("error"),
                started_at=cmd_data["started_at"],
                completed_at=cmd_data.get("completed_at")
            )
            commands.append(command)
        
        # Sort by start date (most recent first)
        commands.sort(key=lambda x: x.started_at, reverse=True)
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(commands)} commands",
            data=commands
        )
        
    except Exception as e:
        logger.error("Failed to get commands", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve commands"
        )

@router.get("/commands/{command_id}", response_model=APIResponse[Command])
async def get_command(
    command_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Détails d'une commande spécifique depuis la base de données.
    """
    try:
        # Connexion DB
        if not db_client.connected:
            await db_client.connect()
        
        # Get specific command from database
        command_data = await db_client.get_command_by_id(command_id)
        
        if not command_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Command not found"
            )
        
        command = Command(
            id=str(command_data["id"]),
            agent_id=command_data["agent_id"],
            command=command_data["command"],
            status=command_data["status"],
            output=command_data.get("output"),
            error=command_data.get("error"),
            started_at=command_data["started_at"],
            completed_at=command_data.get("completed_at")
        )
        
        return APIResponse(
            status="success",
            message="Command retrieved successfully",
            data=command
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get command", command_id=command_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve command"
        )

@router.post("/commands", response_model=APIResponse[Command])
async def execute_command(
    agent_id: str,
    command: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Exécute une commande sur un agent spécifique.
    """
    # Validation basique
    if not agent_id or not command.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent ID and command are required"
        )
    
    try:
        # Utiliser AgentCommandService pour exécution réelle
        command_service = get_agent_command_service()
        
        # Parser command pour AgentCommandService
        command_parts = command.strip().split()
        main_command = command_parts[0] if command_parts else "status"
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        # Exécuter commande via service (avec timeout 30s par défaut)
        result = await command_service.execute_command(
            command=main_command,
            args=args,
            agent_name=agent_id,
            timeout_seconds=30
        )
        
        # Création Command enrichie avec résultat d'exécution
        command_id = result.get("request_id", str(uuid.uuid4()))
        
        executed_command = Command(
            id=command_id,
            agent_id=agent_id,
            command=command.strip(),
            status="completed" if result.get("success") else "failed",
            output=result.get("stdout", ""),
            error=result.get("stderr", ""),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        
        # Stockage résultat dans la base de données
        try:
            if not db_client.connected:
                await db_client.connect()
            await db_client.create_command(
                command_id=command_id,
                agent_id=agent_id,
                command=command.strip(),
                status=executed_command.status,
                output=executed_command.output,
                error=executed_command.error,
                started_at=executed_command.started_at,
                completed_at=executed_command.completed_at
            )
        except Exception as db_error:
            logger.warning("Failed to store command in database", error=str(db_error))
        
        logger.info("System command executed successfully", 
                   agent_id=agent_id, 
                   command=command.strip(),
                   success=result.get("success", False),
                   user=current_user.username)
        
        return APIResponse(
            status="success",
            message="Command executed successfully" if result.get("success") else "Command execution failed",
            data=executed_command
        )
        
    except Exception as e:
        # Fallback: créer commande avec erreur si service indisponible
        logger.error("Failed to execute system command", 
                    agent_id=agent_id, 
                    command=command, 
                    error=str(e))
        
        command_id = str(uuid.uuid4())
        failed_command = Command(
            id=command_id,
            agent_id=agent_id,
            command=command.strip(),
            status="failed",
            error=f"Execution failed: {str(e)}",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        
        # Stockage commande échouée dans la base de données
        try:
            if not db_client.connected:
                await db_client.connect()
            await db_client.create_command(
                command_id=command_id,
                agent_id=agent_id,
                command=command.strip(),
                status="failed",
                output=None,
                error=failed_command.error,
                started_at=failed_command.started_at,
                completed_at=failed_command.completed_at
            )
        except Exception as db_error:
            logger.warning("Failed to store failed command in database", error=str(db_error))
        
        return APIResponse(
            status="error",
            message="Command execution failed",
            data=failed_command
        )

# CLI Execute endpoint to match UI expectations
class CLIExecuteRequest(BaseModel):
    """CLI command execution request"""
    command: str = Field(..., description="Command to execute")
    args: List[str] = Field(default=[], description="Command arguments")
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")

class CLIExecuteResponse(BaseModel):
    """CLI command execution response"""
    success: bool = Field(..., description="Whether command succeeded")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    return_code: int = Field(..., description="Process return code")
    execution_time: float = Field(..., description="Execution time in seconds")

# Route at /api/system/cli/execute to match UI expectations without conflicts
@router.post("/cli/execute", response_model=CLIExecuteResponse)
async def cli_execute(
    request: CLIExecuteRequest,
    current_user: UserInfo = Depends(get_current_user)
) -> CLIExecuteResponse:
    """
    Execute NeuraOps CLI command for the dynamic terminal
    
    Simple implementation that routes to the existing command execution system
    """
    import time
    start_time = time.time()
    
    try:
        logger.info("CLI command execution requested", 
                   command=request.command, 
                   args=request.args,
                   user=current_user.username)
        
        # Use existing command service for execution
        command_service = get_agent_command_service()
        
        # Execute command (using 'system' as agent_id for CLI commands)
        result = await command_service.execute_command(
            command=request.command,
            args=request.args,
            agent_name="system",
            timeout_seconds=request.timeout
        )
        
        execution_time = time.time() - start_time
        success = result.get("success", False)
        
        response = CLIExecuteResponse(
            success=success,
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            return_code=0 if success else 1,
            execution_time=execution_time
        )
        
        logger.info("CLI command execution completed",
                   command=request.command,
                   success=success,
                   execution_time=execution_time)
        
        return response
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error("CLI command execution failed",
                    command=request.command,
                    error=str(e))
        
        return CLIExecuteResponse(
            success=False,
            stdout="",
            stderr=f"CLI execution error: {str(e)}",
            return_code=1,
            execution_time=execution_time
        )