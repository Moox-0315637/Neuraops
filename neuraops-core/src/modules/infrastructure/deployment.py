"""
NeuraOps Deployment Management System
Multi-environment deployment orchestration with rollback capabilities and health monitoring
"""

import asyncio
import logging
import subprocess
import time
import json
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from ...core.engine import get_engine
from ...core.command_executor import CommandExecutor, SafetyLevel
from ...core.structured_output import DeploymentResult, SeverityLevel
from ...devops_commander.exceptions import DeploymentError, CommandExecutionError

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Deployment strategy types"""

    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"
    INSTANT = "instant"


class DeploymentStatus(Enum):
    """Deployment status states"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class HealthCheckType(Enum):
    """Types of health checks"""

    HTTP = "http"
    TCP = "tcp"
    COMMAND = "command"
    KUBERNETES = "kubernetes"
    DOCKER = "docker"


@dataclass
class DeploymentConfig:
    """Configuration for a deployment"""

    name: str
    environment: str
    strategy: DeploymentStrategy
    target_platform: str  # kubernetes, docker, docker-compose, etc.
    image_or_path: str
    replicas: int = 1
    timeout_seconds: int = 300
    health_check_enabled: bool = True
    rollback_on_failure: bool = True
    notifications_enabled: bool = True

    # Health check configuration
    health_check_type: HealthCheckType = HealthCheckType.HTTP
    health_check_endpoint: Optional[str] = "/health"
    health_check_timeout: int = 30
    health_check_retries: int = 3

    # Rolling deployment specific
    max_unavailable: str = "25%"
    max_surge: str = "25%"

    # Blue-green specific
    traffic_split_percentage: int = 10  # Initial traffic to new version

    # Canary specific
    canary_percentage: int = 10
    canary_duration_minutes: int = 15

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result["strategy"] = self.strategy.value
        result["health_check_type"] = self.health_check_type.value
        return result


@dataclass
class DeploymentExecution:
    """Track a deployment execution"""

    id: str
    config: DeploymentConfig
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_executed: bool = False
    health_checks_passed: bool = False
    deployment_logs: Optional[List[str]] = None

    def __post_init__(self):
        if self.deployment_logs is None:
            self.deployment_logs = []

    @property
    def duration(self) -> Optional[timedelta]:
        """Get deployment duration"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_complete(self) -> bool:
        """Check if deployment is complete"""
        return self.status in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED, DeploymentStatus.ROLLED_BACK, DeploymentStatus.CANCELLED]


class HealthChecker:
    """Perform health checks on deployed applications"""

    def __init__(self, command_executor: CommandExecutor):
        self.command_executor = command_executor
        self.default_timeout = 30  # Default timeout for all health checks

    async def _execute_with_timeout(self, command: str, timeout_seconds: int, safety_level: SafetyLevel) -> Any:
        """Execute command with timeout context manager"""
        try:
            # Use asyncio.wait_for for timeout context management
            result = await asyncio.wait_for(self.command_executor.execute_async(command=command, safety_level=safety_level), timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return type("Result", (), {"success": False, "stdout": "", "stderr": f"Command timed out after {timeout_seconds} seconds", "execution_time": timeout_seconds})()

    async def check_health(self, check_type: HealthCheckType, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check based on type"""

        # Set timeout from config or use default
        timeout = config.get("timeout", self.default_timeout)
        self.current_timeout = timeout  # Store for use in private methods

        try:
            if check_type == HealthCheckType.HTTP:
                return await self._check_http_health(config)
            elif check_type == HealthCheckType.TCP:
                return await self._check_tcp_health(config)
            elif check_type == HealthCheckType.COMMAND:
                return await self._check_command_health(config)
            elif check_type == HealthCheckType.KUBERNETES:
                return await self._check_kubernetes_health(config)
            elif check_type == HealthCheckType.DOCKER:
                return await self._check_docker_health(config)
            else:
                return {"healthy": False, "error": f"Unknown health check type: {check_type}"}
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"healthy": False, "error": str(e)}

    async def _check_http_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check HTTP endpoint health"""

        url = config.get("url", "http://localhost:8080/health")
        expected_status = config.get("expected_status", 200)

        try:
            # Use curl for HTTP health check
            cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout {self.current_timeout} {url}"

            result = await self._execute_with_timeout(cmd, self.current_timeout, SafetyLevel.LOW)

            if result.success and result.stdout:
                status_code = int(result.stdout.strip())
                healthy = status_code == expected_status
                return {"healthy": healthy, "status_code": status_code, "response_time": result.execution_time, "url": url}
            else:
                return {"healthy": False, "error": f"HTTP check failed: {result.stderr}", "url": url}

        except Exception as e:
            return {"healthy": False, "error": str(e), "url": url}

    async def _check_tcp_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check TCP port connectivity"""

        host = config.get("host", "localhost")
        port = config.get("port", 8080)

        try:
            # Use netcat or telnet for TCP check
            cmd = f"nc -z -w {self.current_timeout} {host} {port}"

            result = await self._execute_with_timeout(cmd, self.current_timeout, SafetyLevel.LOW)

            return {"healthy": result.success, "host": host, "port": port, "response_time": result.execution_time}

        except Exception as e:
            return {"healthy": False, "error": str(e), "host": host, "port": port}

    async def _check_command_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health using custom command"""

        command = config.get("command", 'echo "healthy"')
        expected_output = config.get("expected_output")

        try:
            result = await self._execute_with_timeout(command, self.current_timeout, SafetyLevel.MEDIUM)

            healthy = result.success
            if expected_output and result.stdout:
                healthy = expected_output in result.stdout

            return {"healthy": healthy, "command": command, "output": result.stdout, "error": result.stderr if not result.success else None}

        except Exception as e:
            return {"healthy": False, "error": str(e), "command": command}

    async def _check_kubernetes_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check Kubernetes deployment health"""

        namespace = config.get("namespace", "default")
        deployment = config.get("deployment")

        if not deployment:
            return {"healthy": False, "error": "No deployment name specified"}

        try:
            # Check deployment status
            cmd = f"kubectl get deployment {deployment} -n {namespace} -o json"

            result = await self._execute_with_timeout(cmd, self.current_timeout, SafetyLevel.LOW)

            if result.success and result.stdout:
                deployment_data = json.loads(result.stdout)
                status = deployment_data.get("status", {})

                ready_replicas = status.get("readyReplicas", 0)
                desired_replicas = status.get("replicas", 0)

                healthy = ready_replicas == desired_replicas and desired_replicas > 0

                return {
                    "healthy": healthy,
                    "deployment": deployment,
                    "namespace": namespace,
                    "ready_replicas": ready_replicas,
                    "desired_replicas": desired_replicas,
                    "conditions": status.get("conditions", []),
                }
            else:
                return {"healthy": False, "error": f"Failed to get deployment status: {result.stderr}", "deployment": deployment, "namespace": namespace}

        except Exception as e:
            return {"healthy": False, "error": str(e), "deployment": deployment, "namespace": namespace}

    async def _check_docker_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check Docker container health"""

        container_name = config.get("container_name")
        container_id = config.get("container_id")

        if not container_name and not container_id:
            return {"healthy": False, "error": "No container name or ID specified"}

        identifier = container_name or container_id

        try:
            # Check container status
            cmd = f"docker inspect {identifier} --format='{{{{.State.Health.Status}}}}'"

            result = await self._execute_with_timeout(cmd, self.current_timeout, SafetyLevel.LOW)

            if result.success and result.stdout:
                health_status = result.stdout.strip()
                healthy = health_status == "healthy"

                return {"healthy": healthy, "container": identifier, "health_status": health_status}
            else:
                # Fallback to checking if container is running
                cmd_running = f"docker inspect {identifier} --format='{{{{.State.Running}}}}'"

                result_running = await self._execute_with_timeout(cmd_running, self.current_timeout, SafetyLevel.LOW)

                if result_running.success:
                    is_running = result_running.stdout.strip().lower() == "true"
                    return {"healthy": is_running, "container": identifier, "running": is_running, "note": "Health status not available, checked running status"}
                else:
                    return {"healthy": False, "error": f"Container check failed: {result_running.stderr}", "container": identifier}

        except Exception as e:
            return {"healthy": False, "error": str(e), "container": identifier}


class DeploymentOrchestrator:
    """Orchestrate deployments across different platforms"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.health_checker = HealthChecker(self.command_executor)
        self.active_deployments: Dict[str, DeploymentExecution] = {}
        self.deployment_history: List[DeploymentExecution] = []

    async def _execute_with_timeout(self, command: str, timeout_seconds: int, safety_level: SafetyLevel) -> Any:
        """Execute command with timeout context manager"""
        try:
            result = await asyncio.wait_for(self.command_executor.execute_async(command=command, safety_level=safety_level), timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return type("Result", (), {"success": False, "stdout": "", "stderr": f"Command timed out after {timeout_seconds} seconds", "execution_time": timeout_seconds})()

    def _validate_and_prepare_deployment(self, config: DeploymentConfig, deployment_id: Optional[str] = None) -> tuple[str, DeploymentExecution]:
        """Validate and prepare deployment execution"""
        # Generate deployment ID if not provided
        if not deployment_id:
            deployment_id = f"{config.name}-{int(time.time())}"

        # Create deployment execution tracker
        execution = DeploymentExecution(id=deployment_id, config=config, status=DeploymentStatus.PENDING, started_at=datetime.now())

        # Add to active deployments
        self.active_deployments[deployment_id] = execution

        return deployment_id, execution

    async def _execute_deployment_by_strategy(self, config: DeploymentConfig, execution: DeploymentExecution) -> bool:
        """Execute deployment based on strategy"""
        if config.strategy == DeploymentStrategy.ROLLING:
            return await self._execute_rolling_deployment(execution)
        elif config.strategy == DeploymentStrategy.BLUE_GREEN:
            return await self._execute_blue_green_deployment(execution)
        elif config.strategy == DeploymentStrategy.CANARY:
            return await self._execute_canary_deployment(execution)
        elif config.strategy == DeploymentStrategy.RECREATE:
            return await self._execute_recreate_deployment(execution)
        else:  # INSTANT
            return await self._execute_instant_deployment(execution)

    async def _handle_health_checks_and_rollback(self, config: DeploymentConfig, execution: DeploymentExecution, success: bool) -> bool:
        """Handle health checks and rollback if necessary"""
        if config.health_check_enabled and success:
            execution.deployment_logs.append("Running health checks...")
            health_result = await self._perform_health_checks(execution)
            execution.health_checks_passed = health_result

            if not health_result and config.rollback_on_failure:
                execution.deployment_logs.append("Health checks failed, initiating rollback...")
                await self._rollback_deployment(execution)
                success = False

        return success

    def _finalize_deployment_execution(self, execution: DeploymentExecution, success: bool, deployment_id: str) -> None:
        """Finalize deployment execution status and cleanup"""
        # Update final status
        execution.status = DeploymentStatus.SUCCESS if success else DeploymentStatus.FAILED
        execution.completed_at = datetime.now()

        # Move from active to history
        self.deployment_history.append(execution)
        if deployment_id in self.active_deployments:
            del self.active_deployments[deployment_id]

        logger.info(f"Deployment {deployment_id} completed with status: {execution.status.value}")

    async def _handle_deployment_exception(self, config: DeploymentConfig, execution: DeploymentExecution, deployment_id: str, error: Exception) -> None:
        """Handle deployment exceptions with rollback if enabled"""
        execution.status = DeploymentStatus.FAILED
        execution.error_message = str(error)
        execution.completed_at = datetime.now()

        # Try rollback if enabled
        if config.rollback_on_failure:
            try:
                await self._rollback_deployment(execution)
            except Exception as rollback_error:
                execution.deployment_logs.append(f"Rollback also failed: {str(rollback_error)}")

        # Move to history
        self.deployment_history.append(execution)
        if deployment_id in self.active_deployments:
            del self.active_deployments[deployment_id]

    async def deploy(self, config: DeploymentConfig, deployment_id: Optional[str] = None) -> DeploymentExecution:
        """Execute a deployment"""

        # Validate and prepare deployment
        deployment_id, execution = self._validate_and_prepare_deployment(config, deployment_id)

        try:
            logger.info(f"Starting deployment {deployment_id} using {config.strategy.value} strategy")
            execution.status = DeploymentStatus.IN_PROGRESS

            # Execute deployment based on strategy
            success = await self._execute_deployment_by_strategy(config, execution)

            # Handle health checks and rollback if necessary
            success = await self._handle_health_checks_and_rollback(config, execution, success)

            # Finalize deployment execution
            self._finalize_deployment_execution(execution, success, deployment_id)

            return execution

        except Exception as e:
            # Handle deployment exception with rollback
            await self._handle_deployment_exception(config, execution, deployment_id, e)

            logger.error(f"Deployment {deployment_id} failed: {str(e)}")
            raise DeploymentError(f"Deployment {deployment_id} failed: {str(e)}", deployment_id=deployment_id, deployment_config=config.name) from e

    async def _execute_rolling_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute rolling deployment strategy"""

        config = execution.config
        execution.deployment_logs.append(f"Starting rolling deployment for {config.name}")

        try:
            if config.target_platform == "kubernetes":
                # Kubernetes rolling deployment
                commands = [f"kubectl set image deployment/{config.name} {config.name}={config.image_or_path}", f"kubectl rollout status deployment/{config.name} --timeout={config.timeout_seconds}s"]

                for cmd in commands:
                    execution.deployment_logs.append(f"Executing: {cmd}")
                    result = await self._execute_with_timeout(cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                    if not result.success:
                        execution.deployment_logs.append(f"Command failed: {result.stderr}")
                        return False

                    execution.deployment_logs.append(f"Command output: {result.stdout}")

                return True

            elif config.target_platform == "docker-compose":
                # Docker Compose rolling update
                cmd = f"docker-compose up -d --scale {config.name}={config.replicas}"

                execution.deployment_logs.append(f"Executing: {cmd}")
                result = await self._execute_with_timeout(cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                if result.success:
                    execution.deployment_logs.append(f"Rolling deployment completed: {result.stdout}")
                    return True
                else:
                    execution.deployment_logs.append(f"Rolling deployment failed: {result.stderr}")
                    return False

            else:
                execution.deployment_logs.append(f"Rolling deployment not supported for platform: {config.target_platform}")
                return False

        except Exception as e:
            execution.deployment_logs.append(f"Rolling deployment error: {str(e)}")
            return False

    async def _execute_blue_green_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute blue-green deployment strategy"""

        config = execution.config
        execution.deployment_logs.append(f"Starting blue-green deployment for {config.name}")

        try:
            if config.target_platform == "kubernetes":
                # Blue-green deployment with Kubernetes
                # 1. Deploy new version (green)
                green_name = f"{config.name}-green"

                deploy_cmd = f"kubectl create deployment {green_name} --image={config.image_or_path} --replicas={config.replicas}"
                execution.deployment_logs.append(f"Deploying green version: {deploy_cmd}")

                result = await self._execute_with_timeout(deploy_cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                if not result.success:
                    execution.deployment_logs.append(f"Green deployment failed: {result.stderr}")
                    return False

                # 2. Wait for green to be ready
                wait_cmd = f"kubectl wait --for=condition=available --timeout={config.timeout_seconds}s deployment/{green_name}"
                result = await self._execute_with_timeout(wait_cmd, config.timeout_seconds, SafetyLevel.LOW)

                if not result.success:
                    execution.deployment_logs.append(f"Green deployment not ready: {result.stderr}")
                    # Cleanup failed green deployment
                    await self._execute_with_timeout(f"kubectl delete deployment {green_name}", 30, SafetyLevel.MEDIUM)
                    return False

                # 3. Switch traffic (simplified - in production would use service selector)
                switch_cmd = f'kubectl patch service {config.name} -p \'{{\\"spec\\":{{\\"selector\\":{{\\"app\\":\\"{green_name}\\"}}}}}}\''
                result = await self._execute_with_timeout(switch_cmd, 30, SafetyLevel.MEDIUM)

                if result.success:
                    execution.deployment_logs.append("Traffic switched to green version")

                    # 4. Remove old blue deployment
                    cleanup_cmd = f"kubectl delete deployment {config.name}-blue --ignore-not-found=true"
                    await self._execute_with_timeout(cleanup_cmd, 30, SafetyLevel.MEDIUM)

                    return True
                else:
                    execution.deployment_logs.append(f"Traffic switch failed: {result.stderr}")
                    return False

            else:
                execution.deployment_logs.append(f"Blue-green deployment not fully supported for platform: {config.target_platform}")
                # Fallback to rolling deployment
                return await self._execute_rolling_deployment(execution)

        except Exception as e:
            execution.deployment_logs.append(f"Blue-green deployment error: {str(e)}")
            return False

    async def _execute_canary_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute canary deployment strategy"""

        config = execution.config
        execution.deployment_logs.append(f"Starting canary deployment for {config.name}")

        try:
            if config.target_platform == "kubernetes":
                # Canary deployment with gradual traffic increase
                canary_name = f"{config.name}-canary"
                canary_replicas = max(1, int(config.replicas * config.canary_percentage / 100))

                # 1. Deploy canary version
                deploy_cmd = f"kubectl create deployment {canary_name} --image={config.image_or_path} --replicas={canary_replicas}"
                execution.deployment_logs.append(f"Deploying canary version: {deploy_cmd}")

                result = await self._execute_with_timeout(deploy_cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                if not result.success:
                    execution.deployment_logs.append(f"Canary deployment failed: {result.stderr}")
                    return False

                # 2. Monitor canary for specified duration
                execution.deployment_logs.append(f"Monitoring canary for {config.canary_duration_minutes} minutes...")

                # Wait and monitor (simplified)
                await asyncio.sleep(min(config.canary_duration_minutes * 60, 300))  # Max 5 minutes for demo

                # 3. Check canary health
                health_config = {"deployment": canary_name, "namespace": "default", "timeout": config.health_check_timeout}

                health_result = await self.health_checker.check_health(HealthCheckType.KUBERNETES, health_config)

                if health_result.get("healthy", False):
                    # 4. Promote canary to full deployment
                    execution.deployment_logs.append("Canary healthy, promoting to full deployment")

                    # Scale down original, scale up canary
                    scale_original = f"kubectl scale deployment {config.name} --replicas=0"
                    scale_canary = f"kubectl scale deployment {canary_name} --replicas={config.replicas}"

                    for cmd in [scale_original, scale_canary]:
                        result = await self._execute_with_timeout(cmd, 60, SafetyLevel.MEDIUM)
                        if not result.success:
                            execution.deployment_logs.append(f"Scaling failed: {result.stderr}")

                    execution.deployment_logs.append("Canary deployment promoted successfully")
                    return True
                else:
                    # 5. Rollback canary
                    execution.deployment_logs.append("Canary health checks failed, rolling back")
                    await self._execute_with_timeout(f"kubectl delete deployment {canary_name}", 30, SafetyLevel.MEDIUM)
                    return False

            else:
                execution.deployment_logs.append(f"Canary deployment not supported for platform: {config.target_platform}")
                # Fallback to rolling deployment
                return await self._execute_rolling_deployment(execution)

        except Exception as e:
            execution.deployment_logs.append(f"Canary deployment error: {str(e)}")
            return False

    async def _execute_recreate_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute recreate deployment strategy"""

        config = execution.config
        execution.deployment_logs.append(f"Starting recreate deployment for {config.name}")

        try:
            if config.target_platform == "kubernetes":
                # Recreate deployment
                commands = [
                    f"kubectl delete deployment {config.name} --ignore-not-found=true",
                    f"kubectl create deployment {config.name} --image={config.image_or_path} --replicas={config.replicas}",
                    f"kubectl rollout status deployment/{config.name} --timeout={config.timeout_seconds}s",
                ]

                for cmd in commands:
                    execution.deployment_logs.append(f"Executing: {cmd}")
                    result = await self._execute_with_timeout(cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                    if not result.success:
                        execution.deployment_logs.append(f"Command failed: {result.stderr}")
                        return False

                    execution.deployment_logs.append(f"Command output: {result.stdout}")

                return True

            elif config.target_platform == "docker":
                # Docker container recreate
                commands = [f"docker stop {config.name} || true", f"docker rm {config.name} || true", f"docker run -d --name {config.name} {config.image_or_path}"]

                for cmd in commands:
                    execution.deployment_logs.append(f"Executing: {cmd}")
                    result = await self._execute_with_timeout(cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                    # For docker stop/rm, we allow failures (container might not exist)
                    if "||" not in cmd and not result.success:
                        execution.deployment_logs.append(f"Command failed: {result.stderr}")
                        return False

                    execution.deployment_logs.append(f"Command output: {result.stdout}")

                return True

            else:
                execution.deployment_logs.append(f"Recreate deployment not supported for platform: {config.target_platform}")
                return False

        except Exception as e:
            execution.deployment_logs.append(f"Recreate deployment error: {str(e)}")
            return False

    async def _execute_instant_deployment(self, execution: DeploymentExecution) -> bool:
        """Execute instant deployment (direct update)"""

        config = execution.config
        execution.deployment_logs.append(f"Starting instant deployment for {config.name}")

        try:
            if config.target_platform == "docker-compose":
                # Docker Compose instant deployment
                cmd = f"docker-compose up -d --force-recreate {config.name}"

                execution.deployment_logs.append(f"Executing: {cmd}")
                result = await self._execute_with_timeout(cmd, config.timeout_seconds, SafetyLevel.MEDIUM)

                if result.success:
                    execution.deployment_logs.append(f"Instant deployment completed: {result.stdout}")
                    return True
                else:
                    execution.deployment_logs.append(f"Instant deployment failed: {result.stderr}")
                    return False

            else:
                # Fallback to recreate for other platforms
                return await self._execute_recreate_deployment(execution)

        except Exception as e:
            execution.deployment_logs.append(f"Instant deployment error: {str(e)}")
            return False

    async def _perform_health_checks(self, execution: DeploymentExecution) -> bool:
        """Perform health checks on deployed application"""

        config = execution.config

        # Prepare health check configuration
        health_config = {"url": f"http://localhost:8080{config.health_check_endpoint}", "expected_status": 200, "timeout": config.health_check_timeout}

        # Override with platform-specific config
        if config.target_platform == "kubernetes":
            health_config = {"deployment": config.name, "namespace": "default", "timeout": config.health_check_timeout}
        elif config.target_platform == "docker":
            health_config = {"container_name": config.name, "timeout": config.health_check_timeout}

        # Perform health checks with retries
        for attempt in range(config.health_check_retries):
            execution.deployment_logs.append(f"Health check attempt {attempt + 1}/{config.health_check_retries}")

            health_result = await self.health_checker.check_health(config.health_check_type, health_config)

            if health_result.get("healthy", False):
                execution.deployment_logs.append("Health check passed")
                return True
            else:
                execution.deployment_logs.append(f"Health check failed: {health_result.get('error', 'Unknown error')}")

                # Wait before retry (except last attempt)
                if attempt < config.health_check_retries - 1:
                    await asyncio.sleep(10)

        execution.deployment_logs.append("All health check attempts failed")
        return False

    async def _rollback_deployment(self, execution: DeploymentExecution) -> bool:
        """Rollback a failed deployment"""

        config = execution.config
        execution.deployment_logs.append(f"Initiating rollback for {config.name}")

        try:
            if config.target_platform == "kubernetes":
                # Kubernetes rollback
                cmd = f"kubectl rollout undo deployment/{config.name}"

                execution.deployment_logs.append(f"Executing rollback: {cmd}")
                result = await self._execute_with_timeout(cmd, 120, SafetyLevel.MEDIUM)  # Rollbacks might take longer

                if result.success:
                    execution.deployment_logs.append("Rollback completed successfully")
                    execution.rollback_executed = True
                    execution.status = DeploymentStatus.ROLLED_BACK
                    return True
                else:
                    execution.deployment_logs.append(f"Rollback failed: {result.stderr}")
                    return False

            elif config.target_platform == "docker-compose":
                # Docker Compose rollback (restart previous version)
                cmd = "docker-compose down && docker-compose up -d"

                execution.deployment_logs.append(f"Executing rollback: {cmd}")
                result = await self._execute_with_timeout(cmd, 120, SafetyLevel.MEDIUM)

                if result.success:
                    execution.deployment_logs.append("Rollback completed")
                    execution.rollback_executed = True
                    execution.status = DeploymentStatus.ROLLED_BACK
                    return True
                else:
                    execution.deployment_logs.append(f"Rollback failed: {result.stderr}")
                    return False

            else:
                execution.deployment_logs.append(f"Rollback not supported for platform: {config.target_platform}")
                return False

        except Exception as e:
            execution.deployment_logs.append(f"Rollback error: {str(e)}")
            return False

    async def cancel_deployment(self, deployment_id: str) -> bool:
        """Cancel an active deployment"""

        if deployment_id not in self.active_deployments:
            logger.warning(f"Deployment {deployment_id} not found in active deployments")
            return False

        execution = self.active_deployments[deployment_id]
        execution.status = DeploymentStatus.CANCELLING
        execution.deployment_logs.append("Deployment cancellation requested")

        try:
            # Attempt to rollback/cleanup
            await self._rollback_deployment(execution)

            execution.status = DeploymentStatus.CANCELLED
            execution.completed_at = datetime.now()

            # Move to history
            self.deployment_history.append(execution)
            del self.active_deployments[deployment_id]

            logger.info(f"Deployment {deployment_id} cancelled successfully")
            return True

        except Exception as e:
            execution.deployment_logs.append(f"Cancellation error: {str(e)}")
            execution.status = DeploymentStatus.FAILED
            execution.error_message = f"Cancellation failed: {str(e)}"
            execution.completed_at = datetime.now()

            # Move to history
            self.deployment_history.append(execution)
            del self.active_deployments[deployment_id]

            logger.error(f"Failed to cancel deployment {deployment_id}: {str(e)}")
            return False

    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentExecution]:
        """Get status of a deployment"""

        # Check active deployments first
        if deployment_id in self.active_deployments:
            return self.active_deployments[deployment_id]

        # Check history
        for execution in self.deployment_history:
            if execution.id == deployment_id:
                return execution

        return None

    def list_active_deployments(self) -> List[DeploymentExecution]:
        """List all active deployments"""
        return list(self.active_deployments.values())

    def get_deployment_history(self, limit: Optional[int] = None, environment: Optional[str] = None, status: Optional[DeploymentStatus] = None) -> List[DeploymentExecution]:
        """Get deployment history with optional filtering"""

        history = self.deployment_history.copy()

        # Apply filters
        if environment:
            history = [d for d in history if d.config.environment == environment]

        if status:
            history = [d for d in history if d.status == status]

        # Sort by start time (most recent first)
        history.sort(key=lambda x: x.started_at, reverse=True)

        # Apply limit
        if limit:
            history = history[:limit]

        return history


class DeploymentPipeline:
    """Manage deployment pipelines with multiple stages"""

    def __init__(self):
        self.orchestrator = DeploymentOrchestrator()

    async def execute_pipeline(self, pipeline_config: Dict[str, Any], stages: List[DeploymentConfig]) -> Dict[str, DeploymentExecution]:
        """Execute a multi-stage deployment pipeline"""

        pipeline_name = pipeline_config.get("name", "pipeline")
        logger.info(f"Starting deployment pipeline: {pipeline_name}")

        results = {}

        try:
            for i, stage_config in enumerate(stages):
                stage_name = f"{pipeline_name}-stage-{i+1}"
                logger.info(f"Executing pipeline stage: {stage_name}")

                # Execute stage deployment
                execution = await self.orchestrator.deploy(stage_config, stage_name)
                results[stage_name] = execution

                # Check if stage failed
                if execution.status == DeploymentStatus.FAILED:
                    logger.error(f"Pipeline stage {stage_name} failed, stopping pipeline")
                    break

                # Wait between stages if configured
                wait_time = pipeline_config.get("stage_wait_seconds", 30)
                if i < len(stages) - 1:  # Don't wait after last stage
                    logger.info(f"Waiting {wait_time} seconds before next stage")
                    await asyncio.sleep(wait_time)

            logger.info(f"Pipeline {pipeline_name} completed")
            return results

        except Exception as e:
            logger.error(f"Pipeline {pipeline_name} failed: {str(e)}")
            raise DeploymentError(f"Pipeline {pipeline_name} failed: {str(e)}", pipeline_name=pipeline_name) from e


# Convenience functions for common deployment scenarios
async def quick_deploy_docker(image: str, name: str) -> DeploymentExecution:
    """Quickly deploy a Docker container"""

    config = DeploymentConfig(name=name, environment="development", strategy=DeploymentStrategy.RECREATE, target_platform="docker", image_or_path=image, health_check_type=HealthCheckType.DOCKER)

    orchestrator = DeploymentOrchestrator()
    return await orchestrator.deploy(config)


async def quick_deploy_k8s(deployment_name: str, image: str, replicas: int = 2) -> DeploymentExecution:
    """Quickly deploy to Kubernetes"""

    config = DeploymentConfig(
        name=deployment_name,
        environment="production",
        strategy=DeploymentStrategy.ROLLING,
        target_platform="kubernetes",
        image_or_path=image,
        replicas=replicas,
        health_check_type=HealthCheckType.KUBERNETES,
    )

    orchestrator = DeploymentOrchestrator()
    return await orchestrator.deploy(config)
