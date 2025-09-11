"""
NeuraOps Incident Response Engine
AI-powered incident response automation with gpt-oss-20b
Automated response plans, safety checks, rollback procedures
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .detector import DetectedIncident, IncidentType, IncidentSeverity, IncidentDetectionResult, IncidentDetector
from ...core.engine import DevOpsEngine
from ...core.structured_output import (
    SafetyLevel,
    DevOpsCommand,
    IncidentResponse,
)
from ...core.command_executor import SecureCommandExecutor as CommandExecutor
from ...devops_commander.config import NeuraOpsConfig

logger = logging.getLogger(__name__)


class ResponseAction(Enum):
    """Types of response actions"""

    INVESTIGATE = "investigate"
    RESTART_SERVICE = "restart_service"
    SCALE_RESOURCES = "scale_resources"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    ISOLATE_SYSTEM = "isolate_system"
    NOTIFY_TEAM = "notify_team"
    APPLY_PATCH = "apply_patch"
    EMERGENCY_MAINTENANCE = "emergency_maintenance"
    MONITOR_CLOSELY = "monitor_closely"
    ESCALATE = "escalate"


class ResponseMode(Enum):
    """Response execution modes"""

    MANUAL = "manual"  # Require manual confirmation for each action
    SEMI_AUTO = "semi_auto"  # Automatically execute safe actions, confirm risky ones
    FULL_AUTO = "full_auto"  # Execute all actions automatically (with safety limits)


@dataclass
class ResponseStep:
    """Individual step in incident response"""

    step_id: str
    action: ResponseAction
    description: str
    command: Optional[str] = None
    safety_level: SafetyLevel = SafetyLevel.MODERATE
    estimated_duration: str = "5 minutes"
    prerequisites: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    rollback_procedure: Optional[str] = None
    auto_executable: bool = False
    requires_confirmation: bool = True


@dataclass
class ResponseExecutionResult:
    """Result of executing a response step"""

    step_id: str
    success: bool
    execution_time: float
    output: Optional[str] = None
    error_message: Optional[str] = None
    rollback_available: bool = False
    next_steps: List[str] = field(default_factory=list)


@dataclass
class IncidentResponseResult:
    """Complete result of incident response"""

    success: bool
    incident_id: str
    response_plan: Optional[IncidentResponse] = None
    executed_steps: List[ResponseExecutionResult] = field(default_factory=list)
    resolution_time: Optional[float] = None
    incident_resolved: bool = False
    escalation_required: bool = False
    post_incident_actions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class IncidentResponder:
    """AI-powered incident response automation"""

    def __init__(self, config: Optional[NeuraOpsConfig] = None):
        self.config = config or NeuraOpsConfig()
        self.engine = DevOpsEngine(config=self.config.ollama)
# Removed StructuredOutputManager dependency
        self.command_executor = CommandExecutor(config=self.config.security)

        # Response templates and safety rules
        self.response_templates = self._load_response_templates()
        self.safety_rules = self._load_safety_rules()

    def _load_response_templates(self) -> Dict[IncidentType, Dict[str, Any]]:
        """Load response templates for different incident types"""
        return {
            IncidentType.SYSTEM_OUTAGE: {
                "immediate_actions": [
                    "Check service status and dependencies",
                    "Verify network connectivity",
                    "Review recent deployments or changes",
                    "Restart affected services if safe",
                ],
                "investigation_steps": [
                    "Analyze error logs for root cause",
                    "Check infrastructure health",
                    "Verify external dependencies",
                    "Review monitoring dashboards",
                ],
                "escalation_criteria": [
                    "Service down for >30 minutes",
                    "Multiple services affected",
                    "Data integrity concerns",
                ],
            },
            IncidentType.PERFORMANCE_DEGRADATION: {
                "immediate_actions": [
                    "Check system resource utilization",
                    "Review application performance metrics",
                    "Identify bottlenecks",
                    "Consider temporary scaling",
                ],
                "investigation_steps": [
                    "Analyze performance trends",
                    "Check database query performance",
                    "Review recent code changes",
                    "Monitor network latency",
                ],
            },
            IncidentType.SECURITY_BREACH: {
                "immediate_actions": [
                    "Isolate affected systems",
                    "Preserve evidence",
                    "Reset compromised credentials",
                    "Notify security team immediately",
                ],
                "investigation_steps": [
                    "Forensic analysis of logs",
                    "Identify attack vectors",
                    "Assess data exposure",
                    "Review access patterns",
                ],
            },
        }

    def _load_safety_rules(self) -> Dict[str, Any]:
        """Load safety rules for automated responses"""
        return {
            "auto_restart_limit": 3,  # Maximum auto-restarts per hour
            "max_concurrent_actions": 2,  # Max simultaneous actions
            "confirmation_required_commands": [
                "rm",
                "delete",
                "drop",
                "truncate",
                "format",
                "shutdown",
                "reboot",
                "kill -9",
            ],
            "forbidden_commands": ["rm -rf /", "dd if=", "mkfs", "fdisk"],
            "safe_actions": [
                ResponseAction.INVESTIGATE,
                ResponseAction.MONITOR_CLOSELY,
                ResponseAction.NOTIFY_TEAM,
            ],
        }

    async def generate_response_plan(self, incident: DetectedIncident, response_mode: ResponseMode = ResponseMode.SEMI_AUTO) -> IncidentResponseResult:
        """Generate AI-powered response plan for incident"""

        try:
            logger.info(f"Generating response plan for incident {incident.incident_id}")

            # Generate response plan with AI
            response_plan = await self._ai_generate_response_plan(incident, response_mode)

            return IncidentResponseResult(
                success=True,
                incident_id=incident.incident_id,
                response_plan=response_plan,
                incident_resolved=False,
            )

        except Exception as e:
            logger.error(f"Response plan generation failed: {str(e)}")
            return IncidentResponseResult(success=False, incident_id=incident.incident_id, error_message=str(e))

    async def _ai_generate_response_plan(self, incident: DetectedIncident, response_mode: ResponseMode) -> IncidentResponse:
        """Use AI to generate detailed response plan"""

        system_prompt = f"""You are an expert Site Reliability Engineer (SRE) specializing in incident response.

        Generate a comprehensive incident response plan with these requirements:

        SAFETY FIRST:
        - Prioritize system stability and data integrity
        - Include safety checks and confirmation steps
        - Provide rollback procedures for risky actions
        - Escalate if resolution is uncertain

        RESPONSE STRUCTURE:
        - Immediate actions (first 5 minutes)
        - Investigation steps (5-30 minutes)
        - Resolution actions (30+ minutes)
        - Communication plan
        - Post-incident activities

        RESPONSE MODE: {response_mode.value}
        - manual: All actions require confirmation
        - semi_auto: Safe actions auto, risky actions manual
        - full_auto: All actions auto with safety limits

        Return structured response plan with specific, executable steps."""

        # Prepare incident context
        evidence_summary = "\n".join([f"- {e.source}: {e.content[:100]}" for e in incident.evidence])

        user_prompt = f"""Generate incident response plan:

        INCIDENT DETAILS:
        - ID: {incident.incident_id}
        - Type: {incident.incident_type.value}
        - Severity: {incident.severity.value}
        - Title: {incident.title}
        - Description: {incident.description}
        - Affected Systems: {incident.affected_systems}
        - Root Cause: {incident.root_cause_analysis}
        - Impact: {incident.impact_assessment}

        EVIDENCE:
        {evidence_summary}

        Generate a response plan with:
        1. Immediate actions (0-5 min)
        2. Investigation steps (5-30 min)
        3. Resolution actions (30+ min)
        4. Communication requirements
        5. Rollback procedures
        6. Success criteria

        Consider safety, automation level, and escalation triggers."""

        try:
            # Use structured output for response plan
            response_plan = await self.output_manager.generate_structured(prompt=user_prompt, output_schema=IncidentResponse, system_prompt=system_prompt)

            return response_plan

        except Exception as e:
            logger.error(f"AI response plan generation failed: {str(e)}")
            # Fallback to template-based plan
            return self._generate_template_response_plan(incident)

    def _generate_template_response_plan(self, incident: DetectedIncident) -> IncidentResponse:
        """Generate response plan from templates as fallback"""

        template = self.response_templates.get(incident.incident_type, {})

        immediate_actions = template.get("immediate_actions", ["Investigate incident"])
        investigation_steps = template.get("investigation_steps", ["Analyze logs and metrics"])

        # Convert to DevOpsCommand objects
        commands = []

        for i, action in enumerate(immediate_actions):
            commands.append(
                DevOpsCommand(
                    action=f"immediate_{i}",
                    command="",  # No specific command
                    description=action,
                    safety_level=SafetyLevel.SAFE,
                    estimated_impact="Low risk action",
                    prerequisites=[],
                    verification_commands=[],
                )
            )

        return IncidentResponse(
            incident_id=incident.incident_id,
            severity=incident.severity.value,
            estimated_resolution_time="30 minutes",
            immediate_actions=commands,
            investigation_steps=investigation_steps,
            escalation_required=incident.severity in [IncidentSeverity.CRITICAL],
            communication_plan=[f"Notify team about {incident.incident_type.value}"],
            success_criteria=["System functionality restored", "No error logs for 10 minutes"],
            rollback_plan=["Revert to previous known good state if needed"],
        )

    async def execute_response_plan(
        self,
        response_plan: IncidentResponse,
        response_mode: ResponseMode = ResponseMode.SEMI_AUTO,
        confirm_risky: bool = True,
    ) -> IncidentResponseResult:
        """Execute incident response plan with safety checks"""

        start_time = datetime.now()
        executed_steps = []

        try:
            logger.info(f"Executing response plan for incident {response_plan.incident_id}")

            # Execute immediate actions
            for command in response_plan.immediate_actions:
                if await self._should_execute_command(command, response_mode, confirm_risky):
                    result = await self._execute_response_step(command)
                    executed_steps.append(result)

                    if not result.success and command.safety_level == SafetyLevel.RISKY:
                        logger.error(f"Critical step failed: {result.error_message}")
                        break

            # Check if incident is resolved
            incident_resolved = await self._check_incident_resolution(response_plan)

            resolution_time = (datetime.now() - start_time).total_seconds()

            return IncidentResponseResult(
                success=True,
                incident_id=response_plan.incident_id,
                response_plan=response_plan,
                executed_steps=executed_steps,
                resolution_time=resolution_time,
                incident_resolved=incident_resolved,
                escalation_required=response_plan.escalation_required and not incident_resolved,
            )

        except Exception as e:
            logger.error(f"Response plan execution failed: {str(e)}")
            return IncidentResponseResult(success=False, incident_id=response_plan.incident_id, error_message=str(e))

    async def _should_execute_command(self, command: DevOpsCommand, response_mode: ResponseMode, confirm_risky: bool) -> bool:
        """Determine if command should be executed based on safety and mode"""

        # Add async operation for proper async function
        await asyncio.sleep(0)

        # Always execute safe actions
        if command.safety_level == SafetyLevel.SAFE:
            return True

        # Full auto mode executes everything within safety limits
        if response_mode == ResponseMode.FULL_AUTO:
            return command.safety_level != SafetyLevel.DANGEROUS

        # Semi-auto mode requires confirmation for risky actions
        if response_mode == ResponseMode.SEMI_AUTO:
            if command.safety_level in [SafetyLevel.RISKY, SafetyLevel.DANGEROUS]:
                if confirm_risky:
                    # In real implementation, would prompt user
                    logger.warning(f"Risky action requires confirmation: {command.description}")
                    return False  # For demo, skip risky actions
                else:
                    return False
            return True

        # Manual mode requires confirmation for everything
        if response_mode == ResponseMode.MANUAL:
            return False  # For demo, don't execute in manual mode

        return False

    async def _execute_response_step(self, command: DevOpsCommand) -> ResponseExecutionResult:
        """Execute individual response step"""

        start_time = datetime.now()

        try:
            logger.info(f"Executing response step: {command.description}")

            # Check if command is safe to execute
            if not self._is_command_safe(command):
                return ResponseExecutionResult(
                    step_id=command.action,
                    success=False,
                    execution_time=0.0,
                    error_message="Command blocked by safety rules",
                )

            # Execute command if specified
            if command.command:
                result = await self.command_executor.execute_async(
                    command=command.command,
                    timeout=300,  # 5 minutes max
                    safety_level=command.safety_level,
                )

                execution_time = (datetime.now() - start_time).total_seconds()

                return ResponseExecutionResult(
                    step_id=command.action,
                    success=result.success,
                    execution_time=execution_time,
                    output=result.stdout,
                    error_message=result.stderr if not result.success else None,
                    rollback_available=bool(command.rollback_procedure),
                )
            else:
                # Manual step or investigation step
                execution_time = (datetime.now() - start_time).total_seconds()

                return ResponseExecutionResult(
                    step_id=command.action,
                    success=True,
                    execution_time=execution_time,
                    output=f"Manual step completed: {command.description}",
                    next_steps=["Verify step completion manually"],
                )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Response step execution failed: {str(e)}")

            return ResponseExecutionResult(
                step_id=command.action,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
            )

    def _is_command_safe(self, command: DevOpsCommand) -> bool:
        """Check if command is safe to execute"""

        if not command.command:
            return True  # Manual steps are always safe

        # Check forbidden commands
        forbidden = self.safety_rules["forbidden_commands"]
        for forbidden_cmd in forbidden:
            if forbidden_cmd in command.command.lower():
                logger.warning(f"Forbidden command detected: {forbidden_cmd}")
                return False

        # Check if confirmation required commands are present
        confirmation_required = self.safety_rules["confirmation_required_commands"]
        for risky_cmd in confirmation_required:
            if risky_cmd in command.command.lower():
                logger.info(f"Command requires confirmation: {risky_cmd}")
                # In production, would prompt user
                return command.safety_level == SafetyLevel.SAFE

        return True

    async def _check_incident_resolution(self, response_plan: IncidentResponse) -> bool:
        """Check if incident has been resolved"""

        try:
            # Use AI to verify resolution based on success criteria
            system_prompt = """You are monitoring incident resolution.
            Based on the success criteria and current system state, determine if the incident is resolved.

            Return JSON: {"resolved": boolean, "confidence": float, "reason": "string"}"""

            user_prompt = f"""Check if this incident is resolved:

            Incident ID: {response_plan.incident_id}
            Success Criteria: {response_plan.success_criteria}

            Verify resolution status."""

            resolution_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            resolution_data = json.loads(resolution_json)
            return resolution_data.get("resolved", False)

        except Exception as e:
            logger.error(f"Resolution check failed: {str(e)}")
            return False  # Conservative: assume not resolved if check fails

    async def generate_quick_response(self, incident: DetectedIncident) -> IncidentResponseResult:
        """Generate and execute quick response for urgent incidents"""

        try:
            # Generate response plan
            response_result = await self.generate_response_plan(incident, ResponseMode.SEMI_AUTO)

            if not response_result.success:
                return response_result

            # Execute plan automatically for critical incidents
            if incident.severity == IncidentSeverity.CRITICAL:
                execution_result = await self.execute_response_plan(
                    response_result.response_plan,
                    ResponseMode.SEMI_AUTO,
                    confirm_risky=False,  # Auto-execute for critical
                )
                return execution_result
            else:
                return response_result

        except Exception as e:
            logger.error(f"Quick response failed: {str(e)}")
            return IncidentResponseResult(success=False, incident_id=incident.incident_id, error_message=str(e))

    async def handle_system_outage(self, affected_service: str) -> IncidentResponseResult:
        """Handle system outage with predefined response"""

        # Create mock incident for system outage
        incident = DetectedIncident(
            incident_id=f"outage_{int(datetime.now().timestamp())}",
            incident_type=IncidentType.SYSTEM_OUTAGE,
            severity=IncidentSeverity.CRITICAL,
            title=f"System Outage: {affected_service}",
            description=f"Service {affected_service} is experiencing outage",
            affected_systems=[affected_service],
            root_cause_analysis="Investigation in progress",
            impact_assessment="Service unavailable to users",
            evidence=[],
            detection_timestamp=datetime.now(),
        )

        return await self.generate_quick_response(incident)

    async def handle_performance_issue(self, metric: str, value: float, threshold: float) -> IncidentResponseResult:
        """Handle performance degradation"""

        severity = IncidentSeverity.CRITICAL if value > threshold * 1.5 else IncidentSeverity.HIGH

        incident = DetectedIncident(
            incident_id=f"perf_{int(datetime.now().timestamp())}",
            incident_type=IncidentType.PERFORMANCE_DEGRADATION,
            severity=severity,
            title=f"Performance Issue: {metric}",
            description=f"{metric} at {value} exceeds threshold {threshold}",
            affected_systems=["performance"],
            root_cause_analysis="Performance threshold exceeded",
            impact_assessment="System performance degraded",
            evidence=[],
            detection_timestamp=datetime.now(),
        )

        return await self.generate_quick_response(incident)

    async def emergency_response(self, description: str) -> IncidentResponseResult:
        """Emergency response for user-reported incidents"""

        try:
            # Use AI to classify emergency
            system_prompt = """You are an emergency response coordinator.
            Classify the emergency and provide immediate response actions.

            Determine severity, type, and immediate actions needed.
            Prioritize safety and system stability."""

            user_prompt = f"""Emergency situation reported:
            "{description}"

            Provide immediate response as JSON:
            {{
              "incident_type": "string",
              "severity": "critical|high|medium|low",
              "immediate_actions": ["action1", "action2"],
              "escalation_required": boolean,
              "estimated_impact": "string"
            }}"""

            emergency_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            emergency_data = json.loads(emergency_json)

            # Create emergency incident
            incident = DetectedIncident(
                incident_id=f"emergency_{int(datetime.now().timestamp())}",
                incident_type=IncidentType(emergency_data.get("incident_type", "system_outage")),
                severity=IncidentSeverity(emergency_data.get("severity", "high")),
                title=f"Emergency: {description[:50]}...",
                description=description,
                affected_systems=["unknown"],
                root_cause_analysis="Emergency reported - investigation needed",
                impact_assessment=emergency_data.get("estimated_impact", "Investigation required"),
                evidence=[],
                detection_timestamp=datetime.now(),
                recommended_actions=emergency_data.get("immediate_actions", []),
            )

            # Generate and execute emergency response
            return await self.generate_quick_response(incident)

        except Exception as e:
            logger.error(f"Emergency response failed: {str(e)}")
            return IncidentResponseResult(success=False, incident_id="emergency_failed", error_message=str(e))

    async def rollback_failed_action(self, step_result: ResponseExecutionResult) -> ResponseExecutionResult:
        """Rollback a failed response action"""

        try:
            if not step_result.rollback_available:
                return ResponseExecutionResult(
                    step_id=f"{step_result.step_id}_rollback",
                    success=False,
                    execution_time=0.0,
                    error_message="No rollback procedure available",
                )

            logger.info(f"Rolling back failed step: {step_result.step_id}")

            # Generate rollback command with AI
            system_prompt = """Generate rollback procedure for failed DevOps action.
            Provide safe commands to undo the failed operation."""

            user_prompt = f"""Generate rollback for failed action:
            - Step: {step_result.step_id}
            - Error: {step_result.error_message}
            - Output: {step_result.output}

            Provide safe rollback commands."""

            rollback_cmd = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Execute rollback
            rollback_result = await self.command_executor.execute_async(command=rollback_cmd, timeout=120, safety_level=SafetyLevel.CAUTIOUS)

            return ResponseExecutionResult(
                step_id=f"{step_result.step_id}_rollback",
                success=rollback_result.success,
                execution_time=1.0,
                output=rollback_result.stdout,
                error_message=rollback_result.stderr if not rollback_result.success else None,
            )

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return ResponseExecutionResult(
                step_id=f"{step_result.step_id}_rollback",
                success=False,
                execution_time=0.0,
                error_message=str(e),
            )


# Convenience functions for CLI usage
async def quick_detect_incidents() -> IncidentDetectionResult:
    """Quick incident detection from all sources"""
    detector = IncidentDetector()
    return await detector.detect_incidents()


async def quick_respond_to_outage(service_name: str) -> IncidentResponseResult:
    """Quick response to service outage"""
    responder = IncidentResponder()
    return await responder.handle_system_outage(service_name)


async def emergency_incident_response(description: str) -> IncidentResponseResult:
    """Emergency incident response"""
    responder = IncidentResponder()
    return await responder.emergency_response(description)
