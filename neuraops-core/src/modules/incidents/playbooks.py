"""
NeuraOps Incident Playbooks Library
AI-powered playbooks for automated incident response with gpt-oss-20b
Complete automation workflows with safety checks and rollback procedures
"""

import asyncio
import json
import logging
from enum import Enum
from dataclasses import field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass

from .detector import IncidentType, IncidentSeverity, DetectedIncident
from .responder import ResponseAction
from ...core.engine import DevOpsEngine
from ...core.structured_output import DevOpsCommand, SafetyLevel
from ...core.command_executor import SecureCommandExecutor as CommandExecutor
from ...devops_commander.config import NeuraOpsConfig
from ...devops_commander.exceptions import InfrastructureError

logger = logging.getLogger(__name__)


class PlaybookStatus(Enum):
    """Playbook execution status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class ExecutionStep(Enum):
    """Individual step execution phases"""

    PREPARATION = "preparation"
    EXECUTION = "execution"
    VALIDATION = "validation"
    ROLLBACK = "rollback"
    CLEANUP = "cleanup"


@pydantic_dataclass
class PlaybookStep:
    """Individual step in an incident response playbook"""

    name: str = Field(..., description="Step name for identification")
    description: str = Field(..., description="Human-readable step description")
    action: ResponseAction = Field(..., description="Type of response action")
    command: Optional[str] = Field(None, description="Command to execute")
    safety_level: SafetyLevel = Field(SafetyLevel.MODERATE, description="Safety level for execution")
    timeout: int = Field(300, description="Timeout in seconds", ge=1, le=3600)
    retry_count: int = Field(3, description="Number of retries on failure", ge=0, le=10)
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Execution conditions")
    rollback_command: Optional[str] = Field(None, description="Rollback command if step fails")
    validation_command: Optional[str] = Field(None, description="Command to validate step success")
    depends_on: List[str] = Field(default_factory=list, description="Dependencies on other steps")
    parallel_safe: bool = Field(False, description="Can be executed in parallel")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Ensure timeout is reasonable for DevOps operations"""
        if v < 5:
            raise ValueError("Timeout must be at least 5 seconds")
        if v > 3600:
            raise ValueError("Timeout cannot exceed 1 hour")
        return v


class PlaybookTemplate(BaseModel):
    """Template for incident response playbooks"""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, use_enum_values=True)

    name: str = Field(..., description="Playbook template name")
    version: str = Field("1.0", description="Playbook version")
    incident_type: IncidentType = Field(..., description="Type of incident this playbook handles")
    severity_levels: List[IncidentSeverity] = Field(..., description="Applicable severity levels")
    description: str = Field(..., description="Playbook purpose and scope")
    author: str = Field("NeuraOps AI", description="Playbook author")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Core playbook content
    steps: List[PlaybookStep] = Field(..., description="Ordered list of response steps")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites before execution")
    success_criteria: List[str] = Field(default_factory=list, description="Criteria for successful resolution")
    escalation_triggers: List[str] = Field(default_factory=list, description="When to escalate incident")

    # Execution configuration
    max_execution_time: int = Field(1800, description="Maximum total execution time in seconds")
    require_confirmation: bool = Field(True, description="Require human confirmation before execution")
    allow_parallel_execution: bool = Field(False, description="Allow parallel step execution")
    auto_rollback_on_failure: bool = Field(True, description="Automatically rollback on step failure")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    references: List[str] = Field(default_factory=list, description="Documentation references")

    @field_validator("steps")
    @classmethod
    def validate_steps_not_empty(cls, v: List[PlaybookStep]) -> List[PlaybookStep]:
        """Ensure playbook has at least one step"""
        if not v:
            raise ValueError("Playbook must have at least one step")
        return v

    @field_validator("severity_levels")
    @classmethod
    def validate_severity_levels(cls, v: List[IncidentSeverity]) -> List[IncidentSeverity]:
        """Ensure severity levels are not empty"""
        if not v:
            raise ValueError("Playbook must specify at least one severity level")
        return v


@pydantic_dataclass
class PlaybookExecution:
    """Runtime execution state for a playbook"""

    playbook_name: str
    incident_id: str
    execution_id: str = Field(default_factory=lambda: f"exec-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}")
    status: PlaybookStatus = PlaybookStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step_index: int = 0
    executed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    rollback_steps: List[str] = field(default_factory=list)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)


class PlaybookLibrary:
    """
    Central library for managing incident response playbooks
    Provides CRUD operations, template management, and execution orchestration
    """

    def __init__(self, config: NeuraOpsConfig):
        self.config = config
        self.engine = DevOpsEngine(config.ollama)
        self.command_executor = CommandExecutor(config.security)
        self.playbooks: Dict[str, PlaybookTemplate] = {}
        self.executions: Dict[str, PlaybookExecution] = {}
        self.library_path = Path(config.data_dir) / "knowledge_base" / "incident_playbooks"

        # Ensure playbook directory exists
        self.library_path.mkdir(parents=True, exist_ok=True)

        # Load built-in playbooks
        self._initialize_builtin_playbooks()
        
        # Load previously saved custom playbooks
        self._load_saved_playbooks()

    def _initialize_builtin_playbooks(self) -> None:
        """Initialize built-in playbooks for common incidents"""

        # Network connectivity issues playbook
        network_playbook = self._create_network_connectivity_playbook()
        self.add_playbook(network_playbook)

        # Database performance playbook
        database_playbook = self._create_database_performance_playbook()
        self.add_playbook(database_playbook)

        # Application deployment failure playbook
        deployment_playbook = self._create_deployment_failure_playbook()
        self.add_playbook(deployment_playbook)

        # Resource exhaustion playbook
        resource_playbook = self._create_resource_exhaustion_playbook()
        self.add_playbook(resource_playbook)

        # Security breach response playbook
        security_playbook = self._create_security_breach_playbook()
        self.add_playbook(security_playbook)

        logger.info(f"Initialized {len(self.playbooks)} built-in playbooks")

    def _load_saved_playbooks(self) -> None:
        """Load previously saved custom playbooks from disk"""
        try:
            if not self.library_path.exists():
                return
                
            json_files = list(self.library_path.glob("*.json"))
            loaded_count = 0
            
            for json_file in json_files:
                try:
                    with open(json_file, "r") as f:
                        playbook_data = json.load(f)
                    
                    # Skip if already loaded (built-in playbooks)
                    playbook_name = playbook_data.get("name")
                    if playbook_name and playbook_name in self.playbooks:
                        continue
                    
                    # Create PlaybookTemplate from saved data
                    playbook = PlaybookTemplate.model_validate(playbook_data)
                    self.playbooks[playbook.name] = playbook
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to load playbook from {json_file}: {e}")
                    continue
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} saved custom playbooks from disk")
                
        except Exception as e:
            logger.error(f"Error loading saved playbooks: {e}")

    def _create_network_connectivity_playbook(self) -> PlaybookTemplate:
        """Create playbook for network connectivity issues"""

        steps = [
            PlaybookStep(
                name="network_diagnostics",
                description="Run comprehensive network diagnostics",
                action=ResponseAction.INVESTIGATE,
                command="ping -c 4 8.8.8.8 && traceroute 8.8.8.8 && nslookup google.com",
                safety_level=SafetyLevel.SAFE,
                timeout=60,
                validation_command="ping -c 1 8.8.8.8",
            ),
            PlaybookStep(
                name="check_interfaces",
                description="Check network interface status",
                action=ResponseAction.INVESTIGATE,
                command="ip addr show && ip route show",
                safety_level=SafetyLevel.SAFE,
                timeout=30,
            ),
            PlaybookStep(
                name="restart_networking",
                description="Restart network services",
                action=ResponseAction.RESTART_SERVICE,
                command="sudo systemctl restart networking",
                safety_level=SafetyLevel.MODERATE,
                timeout=120,
                rollback_command="sudo systemctl stop networking && sudo systemctl start networking",
                validation_command="systemctl is-active networking",
                depends_on=["network_diagnostics"],
            ),
            PlaybookStep(
                name="verify_connectivity",
                description="Verify network connectivity restored",
                action=ResponseAction.MONITOR_CLOSELY,
                command="for i in {1..5}; do ping -c 1 8.8.8.8 && echo 'Success' || echo 'Failed'; sleep 2; done",
                safety_level=SafetyLevel.SAFE,
                timeout=60,
                depends_on=["restart_networking"],
            ),
        ]

        return PlaybookTemplate(
            name="network_connectivity_issues",
            incident_type=IncidentType.NETWORK_CONNECTIVITY,
            severity_levels=[IncidentSeverity.HIGH, IncidentSeverity.CRITICAL],
            description="Automated response for network connectivity issues",
            steps=steps,
            prerequisites=[
                "Sudo access available",
                "Network diagnostic tools installed",
                "Backup connectivity method available",
            ],
            success_criteria=[
                "Network interfaces are up",
                "External connectivity restored",
                "DNS resolution working",
            ],
            escalation_triggers=[
                "Network restart fails",
                "Hardware failure detected",
                "Multiple interface failures",
            ],
            max_execution_time=600,
            tags=["network", "connectivity", "infrastructure"],
        )

    def _create_database_performance_playbook(self) -> PlaybookTemplate:
        """Create playbook for database performance issues"""

        steps = [
            PlaybookStep(
                name="check_connections",
                description="Check active database connections",
                action=ResponseAction.INVESTIGATE,
                command="mysql -e 'SHOW PROCESSLIST;' || psql -c 'SELECT * FROM pg_stat_activity;'",
                safety_level=SafetyLevel.SAFE,
                timeout=30,
            ),
            PlaybookStep(
                name="analyze_slow_queries",
                description="Identify slow running queries",
                action=ResponseAction.INVESTIGATE,
                command="mysqldumpslow /var/log/mysql/slow.log | head -20",
                safety_level=SafetyLevel.SAFE,
                timeout=60,
            ),
            PlaybookStep(
                name="kill_long_queries",
                description="Kill queries running longer than 5 minutes",
                action=ResponseAction.APPLY_PATCH,
                command="mysql -e \"SELECT CONCAT('KILL ',id,';') FROM information_schema.processlist WHERE time > 300;\"",
                safety_level=SafetyLevel.MODERATE,
                timeout=120,
                require_confirmation=True,
            ),
            PlaybookStep(
                name="restart_database",
                description="Restart database service if performance doesn't improve",
                action=ResponseAction.RESTART_SERVICE,
                command="sudo systemctl restart mysql || sudo systemctl restart postgresql",
                safety_level=SafetyLevel.MODERATE,
                timeout=180,
                rollback_command="sudo systemctl stop mysql && sudo systemctl start mysql",
                validation_command="systemctl is-active mysql || systemctl is-active postgresql",
                depends_on=["kill_long_queries"],
            ),
        ]

        return PlaybookTemplate(
            name="database_performance_issues",
            incident_type=IncidentType.DATABASE_ISSUES,
            severity_levels=[
                IncidentSeverity.MEDIUM,
                IncidentSeverity.HIGH,
                IncidentSeverity.CRITICAL,
            ],
            description="Automated response for database performance degradation",
            steps=steps,
            prerequisites=[
                "Database admin access",
                "Query monitoring enabled",
                "Database backup recent",
            ],
            success_criteria=[
                "Query response times normalized",
                "Connection count within limits",
                "Database service stable",
            ],
            escalation_triggers=[
                "Database restart fails",
                "Persistent connection issues",
                "Data corruption detected",
            ],
            tags=["database", "performance", "mysql", "postgresql"],
        )

    def _create_deployment_failure_playbook(self) -> PlaybookTemplate:
        """Create playbook for application deployment failures"""

        steps = [
            PlaybookStep(
                name="check_logs",
                description="Examine deployment and application logs",
                action=ResponseAction.INVESTIGATE,
                command="tail -100 /var/log/app/deploy.log && journalctl -u app-service -n 50",
                safety_level=SafetyLevel.SAFE,
                timeout=60,
            ),
            PlaybookStep(
                name="rollback_deployment",
                description="Rollback to previous stable version",
                action=ResponseAction.ROLLBACK_DEPLOYMENT,
                command="kubectl rollout undo deployment/app-deployment || docker-compose down && docker-compose up -d",
                safety_level=SafetyLevel.MODERATE,
                timeout=300,
                validation_command="kubectl get pods | grep Running || docker-compose ps | grep Up",
            ),
            PlaybookStep(
                name="verify_rollback",
                description="Verify application health after rollback",
                action=ResponseAction.MONITOR_CLOSELY,
                command="curl -f http://localhost:8080/health || curl -f http://app.local/healthcheck",
                safety_level=SafetyLevel.SAFE,
                timeout=120,
                retry_count=5,
                depends_on=["rollback_deployment"],
            ),
            PlaybookStep(
                name="notify_team",
                description="Notify development team of rollback",
                action=ResponseAction.NOTIFY_TEAM,
                command="echo 'Deployment rolled back due to failure. Check logs for details.' | mail -s 'Deployment Rollback Alert' dev-team@company.com",
                safety_level=SafetyLevel.SAFE,
                timeout=30,
                depends_on=["verify_rollback"],
            ),
        ]

        return PlaybookTemplate(
            name="deployment_failure_response",
            incident_type=IncidentType.DEPLOYMENT_FAILURE,
            severity_levels=[IncidentSeverity.HIGH, IncidentSeverity.CRITICAL],
            description="Automated response for application deployment failures",
            steps=steps,
            prerequisites=[
                "Deployment automation access",
                "Previous version available",
                "Health check endpoints configured",
            ],
            success_criteria=[
                "Previous version running stable",
                "All health checks passing",
                "No service disruption",
            ],
            escalation_triggers=[
                "Rollback fails",
                "Health checks continue failing",
                "Data migration issues",
            ],
            tags=["deployment", "rollback", "kubernetes", "docker"],
        )

    def _create_resource_exhaustion_playbook(self) -> PlaybookTemplate:
        """Create playbook for resource exhaustion (CPU, Memory, Disk)"""

        steps = [
            PlaybookStep(
                name="identify_resource_usage",
                description="Identify current resource utilization",
                action=ResponseAction.INVESTIGATE,
                command="top -b -n 1 | head -20 && df -h && free -h",
                safety_level=SafetyLevel.SAFE,
                timeout=30,
            ),
            PlaybookStep(
                name="find_resource_hogs",
                description="Find processes consuming most resources",
                action=ResponseAction.INVESTIGATE,
                command="ps aux --sort=-%cpu | head -10 && ps aux --sort=-%mem | head -10",
                safety_level=SafetyLevel.SAFE,
                timeout=30,
            ),
            PlaybookStep(
                name="clean_temp_files",
                description="Clean temporary files and logs",
                action=ResponseAction.APPLY_PATCH,
                command="find /tmp -type f -atime +7 -delete && journalctl --vacuum-time=7d",
                safety_level=SafetyLevel.MODERATE,
                timeout=120,
            ),
            PlaybookStep(
                name="restart_heavy_processes",
                description="Restart processes consuming excessive resources",
                action=ResponseAction.RESTART_SERVICE,
                command='pkill -f "heavy-process" && systemctl restart resource-intensive-service',
                safety_level=SafetyLevel.MODERATE,
                timeout=180,
                validation_command="pgrep -f \"resource-intensive-service\" && echo 'Service restarted'",
                depends_on=["find_resource_hogs"],
            ),
            PlaybookStep(
                name="scale_resources",
                description="Scale up resources if possible",
                action=ResponseAction.SCALE_RESOURCES,
                command="kubectl scale deployment app-deployment --replicas=5 || echo 'Manual scaling required'",
                safety_level=SafetyLevel.MODERATE,
                timeout=300,
                depends_on=["restart_heavy_processes"],
            ),
        ]

        return PlaybookTemplate(
            name="resource_exhaustion_response",
            incident_type=IncidentType.RESOURCE_EXHAUSTION,
            severity_levels=[
                IncidentSeverity.MEDIUM,
                IncidentSeverity.HIGH,
                IncidentSeverity.CRITICAL,
            ],
            description="Automated response for system resource exhaustion",
            steps=steps,
            prerequisites=[
                "System monitoring enabled",
                "Admin access to processes",
                "Scaling capabilities available",
            ],
            success_criteria=[
                "Resource utilization below 80%",
                "System responsive",
                "Services running normally",
            ],
            escalation_triggers=[
                "Resource cleanup ineffective",
                "Hardware limitations reached",
                "Multiple service failures",
            ],
            tags=["resources", "performance", "scaling", "cleanup"],
        )

    def _create_security_breach_playbook(self) -> PlaybookTemplate:
        """Create playbook for security breach response"""

        steps = [
            PlaybookStep(
                name="isolate_affected_systems",
                description="Immediately isolate potentially compromised systems",
                action=ResponseAction.ISOLATE_SYSTEM,
                command="iptables -A INPUT -j DROP && iptables -A OUTPUT -j DROP",
                safety_level=SafetyLevel.DANGEROUS,
                timeout=60,
                rollback_command="iptables -F",
            ),
            PlaybookStep(
                name="collect_evidence",
                description="Collect forensic evidence",
                action=ResponseAction.INVESTIGATE,
                command="netstat -an > /tmp/connections.log && ps aux > /tmp/processes.log && last > /tmp/logins.log",
                safety_level=SafetyLevel.SAFE,
                timeout=120,
            ),
            PlaybookStep(
                name="check_integrity",
                description="Check system and file integrity",
                action=ResponseAction.INVESTIGATE,
                command="aide --check || rkhunter --check --skip-keypress",
                safety_level=SafetyLevel.SAFE,
                timeout=600,
            ),
            PlaybookStep(
                name="notify_security_team",
                description="Immediately notify security team",
                action=ResponseAction.NOTIFY_TEAM,
                command="echo 'SECURITY BREACH DETECTED - Systems isolated for investigation' | mail -s 'CRITICAL: Security Incident' security@company.com",
                safety_level=SafetyLevel.SAFE,
                timeout=30,
            ),
            PlaybookStep(
                name="emergency_maintenance",
                description="Enable emergency maintenance mode",
                action=ResponseAction.EMERGENCY_MAINTENANCE,
                command="systemctl stop all-services && echo 'System under maintenance' > /var/www/html/index.html",
                safety_level=SafetyLevel.MODERATE,
                timeout=300,
                depends_on=["isolate_affected_systems", "collect_evidence"],
            ),
        ]

        return PlaybookTemplate(
            name="security_breach_response",
            incident_type=IncidentType.SECURITY_BREACH,
            severity_levels=[IncidentSeverity.CRITICAL],
            description="Immediate response protocol for security breaches",
            steps=steps,
            prerequisites=[
                "Security tools installed",
                "Incident response plan documented",
                "Security team contacts current",
            ],
            success_criteria=[
                "Affected systems isolated",
                "Evidence collected",
                "Security team notified",
                "Further damage prevented",
            ],
            escalation_triggers=[
                "Multiple systems affected",
                "Data exfiltration detected",
                "Persistence mechanisms found",
            ],
            require_confirmation=False,  # Security incidents need immediate action
            auto_rollback_on_failure=False,  # Don't rollback security measures
            tags=["security", "breach", "forensics", "isolation"],
        )

    def add_playbook(self, playbook: PlaybookTemplate) -> None:
        """Add a playbook to the library"""
        self.playbooks[playbook.name] = playbook

        # Save to disk with proper enum serialization
        playbook_file = self.library_path / f"{playbook.name}.json"
        with open(playbook_file, "w") as f:
            # Use mode='json' to properly serialize enums
            json.dump(playbook.model_dump(mode='json'), f, indent=2, default=str)

        logger.info(f"Added playbook: {playbook.name}")

    def delete_playbook(self, playbook_name: str) -> bool:
        """Delete a playbook from the library and remove its file from disk"""
        try:
            # Check if playbook exists in memory
            if playbook_name not in self.playbooks:
                logger.warning(f"Playbook not found in memory: {playbook_name}")
                return False
            
            # Remove from memory
            del self.playbooks[playbook_name]
            
            # Remove file from disk
            playbook_file = self.library_path / f"{playbook_name}.json"
            if playbook_file.exists():
                playbook_file.unlink()
                logger.info(f"Deleted playbook file: {playbook_file}")
            else:
                logger.warning(f"Playbook file not found on disk: {playbook_file}")
            
            logger.info(f"Successfully deleted playbook: {playbook_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete playbook {playbook_name}: {e}")
            return False

    def get_playbook(self, name: str) -> Optional[PlaybookTemplate]:
        """Retrieve a playbook by name"""
        return self.playbooks.get(name)

    def list_playbooks(
        self,
        incident_type: Optional[IncidentType] = None,
        severity: Optional[IncidentSeverity] = None,
    ) -> List[PlaybookTemplate]:
        """List available playbooks, optionally filtered"""
        playbooks = list(self.playbooks.values())

        if incident_type:
            playbooks = [p for p in playbooks if p.incident_type == incident_type]

        if severity:
            playbooks = [p for p in playbooks if severity in p.severity_levels]

        return playbooks

    def find_suitable_playbooks(self, incident: DetectedIncident) -> List[PlaybookTemplate]:
        """Find playbooks suitable for a detected incident"""
        suitable_playbooks = []

        for playbook in self.playbooks.values():
            # Match incident type
            if playbook.incident_type == incident.incident_type:
                # Check severity compatibility
                if incident.severity in playbook.severity_levels:
                    suitable_playbooks.append(playbook)

        # Sort by relevance (prefer exact matches and higher coverage)
        suitable_playbooks.sort(
            key=lambda p: (
                len(p.severity_levels),  # More comprehensive playbooks first
                p.updated_at,  # Newer playbooks first
            ),
            reverse=True,
        )

        return suitable_playbooks

    async def execute_playbook(
        self,
        playbook_name: str,
        incident_id: str,
        variables: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> PlaybookExecution:
        """Execute a playbook for an incident"""

        playbook = self.get_playbook(playbook_name)
        if not playbook:
            raise ValueError(f"Playbook not found: {playbook_name}")

        # Create execution tracking
        execution = PlaybookExecution(playbook_name=playbook_name, incident_id=incident_id, variables=variables or {})

        self.executions[execution.execution_id] = execution

        try:
            execution.status = PlaybookStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)

            logger.info(f"Starting playbook execution: {execution.execution_id}")

            # Execute steps in sequence
            for step_index, step in enumerate(playbook.steps):
                execution.current_step_index = step_index

                # Check dependencies
                if not self._check_step_dependencies(step, execution):
                    execution.error_messages.append(f"Step {step.name} dependencies not met")
                    continue

                # Execute step
                success = await self._execute_step(step, execution, dry_run)

                if success:
                    execution.executed_steps.append(step.name)
                    logger.info(f"Step {step.name} completed successfully")
                else:
                    execution.failed_steps.append(step.name)
                    logger.error(f"Step {step.name} failed")

                    # Handle failure
                    if playbook.auto_rollback_on_failure:
                        await self._rollback_execution(execution, playbook)
                        execution.status = PlaybookStatus.ROLLED_BACK
                        break
                    else:
                        execution.status = PlaybookStatus.FAILED
                        break

            # Mark as successful if all steps completed
            if execution.status == PlaybookStatus.RUNNING:
                execution.status = PlaybookStatus.SUCCESS

            execution.completed_at = datetime.now(timezone.utc)

            logger.info(f"Playbook execution completed: {execution.execution_id} - {execution.status.value}")

        except Exception as e:
            execution.status = PlaybookStatus.FAILED
            execution.error_messages.append(f"Execution error: {str(e)}")
            execution.completed_at = datetime.now(timezone.utc)
            logger.error(f"Playbook execution failed: {e}")

        return execution

    def _check_step_dependencies(self, step: PlaybookStep, execution: PlaybookExecution) -> bool:
        """Check if step dependencies are satisfied"""
        if not step.depends_on:
            return True

        for dependency in step.depends_on:
            if dependency not in execution.executed_steps:
                return False

        return True

    def _prepare_step_execution(self, step: PlaybookStep, execution: PlaybookExecution, dry_run: bool = False) -> Dict[str, Any]:
        """Prepare step execution context and logging"""
        step_log = {
            "step_name": step.name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "action": step.action.value,
            "dry_run": dry_run,
        }

        if dry_run:
            step_log["status"] = "simulated"
            step_log["message"] = "Dry run - step not executed"
            execution.execution_log.append(step_log)
            return step_log

        return step_log

    def _create_devops_command(self, step: PlaybookStep, execution: PlaybookExecution) -> DevOpsCommand:
        """Create DevOps command from playbook step"""
        return DevOpsCommand(
            action=step.action,
            command=step.command,
            description=step.description,
            safety_level=step.safety_level,
            estimated_impact=f"Step {step.name} in playbook {execution.playbook_name}",
            prerequisites=[],
            rollback_procedure=step.rollback_command,
            verification_commands=([step.validation_command] if step.validation_command else []),
        )

    async def _execute_command_with_result(self, command: DevOpsCommand, step_log: Dict[str, Any], timeout_seconds: int) -> bool:
        """Execute command and handle result"""
        try:
            async with asyncio.timeout(timeout_seconds):
                result = await self.command_executor.execute_command(command=command.command, timeout_seconds=timeout_seconds, dry_run=False)
        except asyncio.TimeoutError:
            step_log["status"] = "timeout"
            step_log["error"] = f"Command timed out after {timeout_seconds} seconds"
            return False

        if result.success:
            step_log["status"] = "success"
            step_log["output"] = result.stdout[:1000]  # Limit log size
            return True
        else:
            step_log["status"] = "failed"
            step_log["error"] = result.stderr[:500] if result.stderr else result.stdout[:500]
            return False

    async def _handle_command_retry(self, attempt: int, retry_count: int) -> bool:
        """Handle command retry logic with exponential backoff"""
        if attempt < retry_count:
            await asyncio.sleep(2**attempt)  # Exponential backoff
            return True
        return False

    def _handle_command_failure(self, step_log: Dict[str, Any], error: str) -> None:
        """Handle command execution failure"""
        step_log["status"] = "failed"
        step_log["error"] = error[:500]

    async def _execute_command_step(self, step: PlaybookStep, execution: PlaybookExecution, step_log: Dict[str, Any]) -> bool:
        """Execute a command step with retry logic"""
        if not step.command:
            return True

        command = self._create_devops_command(step, execution)

        # Execute with retry logic
        for attempt in range(step.retry_count + 1):
            try:
                success = await self._execute_command_with_result(command, step_log, step.timeout)

                if success:
                    return True

                if not await self._handle_command_retry(attempt, step.retry_count):
                    return False

            except Exception as e:
                if not await self._handle_command_retry(attempt, step.retry_count):
                    self._handle_command_failure(step_log, str(e))
                    return False

        return False

    async def _execute_validation_step(self, step: PlaybookStep, execution: PlaybookExecution, step_log: Dict[str, Any]) -> bool:
        """Execute validation for a step"""
        if not step.validation_command:
            return True

        validation_success = await self._validate_step(step, execution)
        if not validation_success:
            step_log["status"] = "validation_failed"
            return False

        return True

    def _handle_step_completion(self, step_log: Dict[str, Any], execution: PlaybookExecution, success: bool) -> None:
        """Handle step completion logging"""
        step_log["completed_at"] = datetime.now(timezone.utc).isoformat()
        if success:
            step_log["status"] = "success"
        execution.execution_log.append(step_log)

    async def _execute_step(self, step: PlaybookStep, execution: PlaybookExecution, dry_run: bool = False) -> bool:
        """Execute an individual playbook step"""

        # Prepare step execution context
        step_log = self._prepare_step_execution(step, execution, dry_run)

        if dry_run:
            return True

        try:
            # Execute the command step
            command_success = await self._execute_command_step(step, execution, step_log)
            if not command_success:
                self._handle_step_completion(step_log, execution, False)
                return False

            # Execute validation step
            validation_success = await self._execute_validation_step(step, execution, step_log)
            if not validation_success:
                self._handle_step_completion(step_log, execution, False)
                return False

            # Handle successful completion
            self._handle_step_completion(step_log, execution, True)
            return True

        except Exception as e:
            step_log["status"] = "error"
            step_log["error"] = str(e)[:500]
            await self._handle_step_completion(step_log, execution, False)
            return False

    async def _validate_step(self, step: PlaybookStep, execution: PlaybookExecution) -> bool:
        """Validate step execution using validation command"""

        if not step.validation_command:
            return True

        try:
            validation_command = DevOpsCommand(
                action=ResponseAction.INVESTIGATE,
                command=step.validation_command,
                description=f"Validate {step.name}",
                safety_level=SafetyLevel.SAFE,
                estimated_impact="Validation check",
                prerequisites=[],
                verification_commands=[],
            )

            async with asyncio.timeout(60):
                result = await self.command_executor.execute_command(command=validation_command.command, timeout_seconds=60, dry_run=False)

            return result.success

        except asyncio.TimeoutError:
            logger.error(f"Step validation timed out for {step.name}")
            return False
        except Exception as e:
            logger.error(f"Step validation failed for {step.name}: {e}")
            return False

    async def _rollback_execution(self, execution: PlaybookExecution, playbook: PlaybookTemplate) -> None:
        """Rollback executed steps in reverse order"""

        logger.info(f"Starting rollback for execution: {execution.execution_id}")

        # Rollback steps in reverse order
        for step_name in reversed(execution.executed_steps):
            # Find the step definition
            step = next((s for s in playbook.steps if s.name == step_name), None)
            if not step or not step.rollback_command:
                continue

            try:
                rollback_command = DevOpsCommand(
                    action=ResponseAction.ROLLBACK_DEPLOYMENT,
                    command=step.rollback_command,
                    description=f"Rollback {step.name}",
                    safety_level=SafetyLevel.MODERATE,
                    estimated_impact=f"Rollback step {step.name}",
                    prerequisites=[],
                    verification_commands=[],
                )

                async with asyncio.timeout(step.timeout):
                    result = await self.command_executor.execute_command(command=rollback_command.command, timeout_seconds=step.timeout, dry_run=False)

                if result.success:
                    execution.rollback_steps.append(step_name)
                    logger.info(f"Rolled back step: {step_name}")
                else:
                    logger.error(f"Failed to rollback step {step_name}: {result.stderr or result.stdout}")

            except asyncio.TimeoutError:
                logger.error(f"Rollback timed out for {step_name} after {step.timeout} seconds")
            except Exception as e:
                logger.error(f"Error during rollback of {step_name}: {e}")

    def get_execution_status(self, execution_id: str) -> Optional[PlaybookExecution]:
        """Get status of a playbook execution"""
        return self.executions.get(execution_id)

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running playbook execution"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        if execution.status == PlaybookStatus.RUNNING:
            execution.status = PlaybookStatus.CANCELLED
            execution.completed_at = datetime.now(timezone.utc)
            logger.info(f"Cancelled execution: {execution_id}")
            return True

        return False

    async def generate_playbook_from_incident(self, incident: DetectedIncident, context: Optional[str] = None) -> PlaybookTemplate:
        """Generate a custom playbook for a specific incident using AI"""

        # Create AI prompt for playbook generation
        prompt = f"""Generate a comprehensive incident response playbook for the following incident:

Incident Type: {incident.incident_type.value}
Severity: {incident.severity.value}
Description: {incident.description}
Affected Systems: {', '.join(incident.affected_systems)}

Context: {context or 'None provided'}

Create a playbook with the following requirements:
1. 3-8 specific, actionable steps
2. Appropriate safety levels for each step
3. Dependencies between steps where logical
4. Rollback commands for destructive operations
5. Validation commands to verify success
6. Realistic timeouts for each step

Focus on practical, executable commands for this specific incident type.
Provide the response in JSON format matching the PlaybookTemplate schema."""

        try:
            # Generate playbook using AI
            generated_data = await self.engine.generate_structured(
                prompt=prompt,
                output_schema=PlaybookTemplate,
                system_prompt="You are an expert DevOps engineer creating incident response playbooks.",
            )

            # Enhance the generated playbook
            generated_data.name = f"ai_generated_{incident.incident_type.value}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            generated_data.author = "NeuraOps AI Assistant"
            generated_data.tags.extend(["ai_generated", incident.incident_type.value.lower()])

            logger.info(f"Generated custom playbook: {generated_data.name}")

            return generated_data

        except Exception as e:
            logger.error(f"Failed to generate playbook: {e}")
            raise InfrastructureError(f"Playbook generation failed: {e}")


# Factory function for easy creation
def create_playbook_library(config: NeuraOpsConfig) -> PlaybookLibrary:
    """Factory function to create a playbook library instance"""
    return PlaybookLibrary(config)


# Export key classes and functions
__all__ = [
    "PlaybookLibrary",
    "PlaybookTemplate",
    "PlaybookStep",
    "PlaybookExecution",
    "PlaybookStatus",
    "ExecutionStep",
    "ResponseAction",
    "create_playbook_library",
]
