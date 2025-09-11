"""
NeuraOps Incident Detection Engine
AI-powered incident detection with gpt-oss-20b
Multi-source correlation: logs, metrics, alerts
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from ...core.engine import DevOpsEngine
from ...core.structured_output import (
    IncidentResponse,
)
from ...core.command_executor import SecureCommandExecutor as CommandExecutor
from ...devops_commander.config import NeuraOpsConfig
from ...devops_commander.exceptions import IncidentDetectionError

logger = logging.getLogger(__name__)


class IncidentType(Enum):
    """Types of incidents that can be detected"""

    SYSTEM_OUTAGE = "system_outage"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SECURITY_BREACH = "security_breach"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_CONNECTIVITY = "network_connectivity"
    DATABASE_ISSUES = "database_issues"
    APPLICATION_ERROR = "application_error"
    DEPLOYMENT_FAILURE = "deployment_failure"
    CONFIGURATION_ERROR = "configuration_error"
    EXTERNAL_DEPENDENCY = "external_dependency"


class IncidentSeverity(Enum):
    """Incident severity levels"""

    CRITICAL = "critical"  # System down, data loss risk
    HIGH = "high"  # Major functionality impacted
    MEDIUM = "medium"  # Partial functionality affected
    LOW = "low"  # Minor issues, workarounds available
    INFO = "info"  # Informational, no action needed


@dataclass
class IncidentEvidence:
    """Evidence supporting incident detection"""

    source: str  # logs, metrics, alerts, user_reports
    timestamp: datetime
    content: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedIncident:
    """A detected incident with analysis"""

    incident_id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    title: str
    description: str
    affected_systems: List[str]
    root_cause_analysis: str
    impact_assessment: str
    evidence: List[IncidentEvidence]
    detection_timestamp: datetime
    estimated_resolution_time: Optional[str] = None
    similar_incidents: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentDetectionResult:
    """Result of incident detection analysis"""

    success: bool
    incidents: List[DetectedIncident] = field(default_factory=list)
    total_analyzed_sources: int = 0
    analysis_duration: float = 0.0
    confidence_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class IncidentDetector:
    """AI-powered incident detection engine"""

    def __init__(self, config: Optional[NeuraOpsConfig] = None):
        self.config = config or NeuraOpsConfig()
        self.engine = DevOpsEngine(config=self.config.ollama)
        self.command_executor = CommandExecutor(config=self.config.security)

        # Detection patterns
        self.error_patterns = self._load_error_patterns()
        self.performance_thresholds = self._load_performance_thresholds()

    def _load_error_patterns(self) -> Dict[IncidentType, List[str]]:
        """Load regex patterns for different incident types"""
        return {
            IncidentType.SYSTEM_OUTAGE: [
                r"service\s+unavailable",
                r"connection\s+refused",
                r"timeout\s+exceeded",
                r"502\s+bad\s+gateway",
                r"503\s+service\s+unavailable",
                r"504\s+gateway\s+timeout",
            ],
            IncidentType.APPLICATION_ERROR: [
                r"error|exception|failed|crash",
                r"500\s+internal\s+server\s+error",
                r"stack\s+trace",
                r"null\s+pointer",
                r"segmentation\s+fault",
            ],
            IncidentType.RESOURCE_EXHAUSTION: [
                r"out\s+of\s+memory",
                r"disk\s+space\s+full",
                r"cpu\s+usage\s+high",
                r"memory\s+leak",
                r"no\s+space\s+left",
            ],
            IncidentType.DATABASE_ISSUES: [
                r"database\s+connection\s+failed",
                r"query\s+timeout",
                r"deadlock\s+detected",
                r"table\s+lock",
                r"connection\s+pool\s+exhausted",
            ],
            IncidentType.SECURITY_BREACH: [
                r"unauthorized\s+access",
                r"authentication\s+failed",
                r"permission\s+denied",
                r"brute\s+force",
                r"suspicious\s+activity",
            ],
        }

    def _load_performance_thresholds(self) -> Dict[str, float]:
        """Load performance thresholds for detection"""
        return {
            "cpu_usage_critical": 90.0,
            "memory_usage_critical": 85.0,
            "disk_usage_critical": 90.0,
            "response_time_critical": 10.0,  # seconds
            "error_rate_critical": 5.0,  # percentage
            "availability_critical": 99.0,  # percentage
        }

    async def detect_incidents(self, sources: List[str] = None, time_window: int = 3600) -> IncidentDetectionResult:
        """Detect incidents from multiple sources"""

        if sources is None:
            sources = ["system_logs", "application_logs", "metrics", "alerts"]

        start_time = datetime.now()

        try:
            logger.info(f"Starting incident detection from {len(sources)} sources")

            all_incidents = []
            total_sources = 0

            # Analyze each source
            for source in sources:
                source_incidents = await self._analyze_source(source, time_window)
                all_incidents.extend(source_incidents)
                total_sources += 1

            # Correlate and deduplicate incidents
            correlated_incidents = await self._correlate_incidents(all_incidents)

            # Enrich incidents with AI analysis
            enriched_incidents = await self._enrich_incidents_with_ai(correlated_incidents)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(enriched_incidents)

            # Generate general recommendations
            recommendations = await self._generate_general_recommendations(enriched_incidents)

            analysis_duration = (datetime.now() - start_time).total_seconds()

            return IncidentDetectionResult(
                success=True,
                incidents=enriched_incidents,
                total_analyzed_sources=total_sources,
                analysis_duration=analysis_duration,
                confidence_score=confidence_score,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Incident detection failed: {str(e)}")
            return IncidentDetectionResult(success=False, error_message=str(e))

    async def _analyze_source(self, source: str, time_window: int) -> List[DetectedIncident]:
        """Analyze a specific source for incidents"""

        incidents = []

        try:
            if source == "system_logs":
                incidents.extend(await self._analyze_system_logs(time_window))
            elif source == "application_logs":
                incidents.extend(await self._analyze_application_logs(time_window))
            elif source == "metrics":
                incidents.extend(await self._analyze_metrics())
            elif source == "alerts":
                incidents.extend(await self._analyze_alerts())

        except Exception as e:
            logger.error(f"Source analysis failed for {source}: {str(e)}")

        return incidents

    async def _analyze_system_logs(self, time_window: int) -> List[DetectedIncident]:
        """Analyze system logs for incidents"""

        incidents = []

        try:
            # Get recent system logs
            cmd = f"journalctl --since '{time_window} seconds ago' --no-pager -p err"
            result = await self.command_executor.execute_command(
                command=cmd,
                timeout=60,
            )

            if result.success and result.stdout:
                # Use AI to analyze logs
                incidents.extend(await self._ai_analyze_logs(result.stdout, "system"))

        except Exception as e:
            logger.error(f"System logs analysis failed: {str(e)}")

        return incidents

    async def _find_log_files(self, log_pattern: str, time_window: int) -> List[str]:
        """Find recent log files matching a pattern"""
        log_files = []
        try:
            cmd = f"find {log_pattern} -type f -mmin -{time_window//60} 2>/dev/null | head -5"
            find_result = await self.command_executor.execute_command(
                command=cmd,
                timeout=30,
            )

            if find_result.success and find_result.stdout:
                log_files = [f.strip() for f in find_result.stdout.strip().split("\n") if f.strip()]
        except Exception as e:
            logger.debug(f"Log file search failed for {log_pattern}: {str(e)}")

        return log_files

    async def _analyze_single_log_file(self, log_file: str) -> List[DetectedIncident]:
        """Analyze a single log file for incidents"""
        incidents = []
        try:
            tail_cmd = f"tail -n 100 {log_file.strip()}"
            tail_result = await self.command_executor.execute_command(
                command=tail_cmd,
                timeout=30,
            )

            if tail_result.success and tail_result.stdout:
                log_incidents = await self._ai_analyze_logs(tail_result.stdout, "application")
                incidents.extend(log_incidents)
        except Exception as e:
            logger.debug(f"Single log file analysis failed for {log_file}: {str(e)}")

        return incidents

    async def _process_log_patterns(self, log_paths: List[str], time_window: int) -> List[DetectedIncident]:
        """Process all log patterns and extract incidents"""
        incidents = []

        for log_pattern in log_paths:
            try:
                log_files = await self._find_log_files(log_pattern, time_window)

                for log_file in log_files:
                    file_incidents = await self._analyze_single_log_file(log_file)
                    incidents.extend(file_incidents)

            except Exception as e:
                logger.debug(f"Log pattern processing failed for {log_pattern}: {str(e)}")

        return incidents

    async def _analyze_application_logs(self, time_window: int) -> List[DetectedIncident]:
        """Analyze application logs for incidents"""
        incidents = []

        try:
            # Check common application log locations
            log_paths = ["/var/log/app/*.log", "/app/logs/*.log", "./logs/*.log"]

            # Process all log patterns using helper function
            incidents = await self._process_log_patterns(log_paths, time_window)

        except Exception as e:
            logger.error(f"Application logs analysis failed: {str(e)}")

        return incidents

    async def _analyze_metrics(self) -> List[DetectedIncident]:
        """Analyze system metrics for incidents"""

        incidents = []

        try:
            # CPU usage check
            cpu_cmd = "top -l 1 | grep 'CPU usage' | awk '{print $3}' | sed 's/%//g'"
            cpu_result = await self.command_executor.execute_command(
                command=cpu_cmd,
                timeout=15,
            )

            if cpu_result.success and cpu_result.stdout:
                try:
                    cpu_usage = float(cpu_result.stdout.strip())
                    if cpu_usage > self.performance_thresholds["cpu_usage_critical"]:
                        incidents.append(
                            self._create_metric_incident(
                                "High CPU Usage",
                                f"CPU usage at {cpu_usage:.1f}%",
                                IncidentType.RESOURCE_EXHAUSTION,
                                IncidentSeverity.HIGH,
                            )
                        )
                except ValueError:
                    pass

            # Memory usage check (for future implementation)
            # memory_cmd = r"vm_stat | grep 'Pages free' | awk '{print $3}' | sed 's/\.//g'"

            # Disk usage check
            disk_cmd = "df -h / | awk 'NR==2 {print $5}' | sed 's/%//g'"
            disk_result = await self.command_executor.execute_command(
                command=disk_cmd,
                timeout=15,
            )

            if disk_result.success and disk_result.stdout:
                try:
                    disk_usage = float(disk_result.stdout.strip())
                    if disk_usage > self.performance_thresholds["disk_usage_critical"]:
                        incidents.append(
                            self._create_metric_incident(
                                "High Disk Usage",
                                f"Disk usage at {disk_usage:.1f}%",
                                IncidentType.RESOURCE_EXHAUSTION,
                                IncidentSeverity.MEDIUM,
                            )
                        )
                except ValueError:
                    pass

        except Exception as e:
            logger.error(f"Metrics analysis failed: {str(e)}")

        return incidents

    async def _analyze_alerts(self) -> List[DetectedIncident]:
        """Analyze external alerts for incidents"""
        # Make function truly async
        await asyncio.sleep(0)

        incidents = []

        try:
            # Check for monitoring alerts (Prometheus, Grafana, etc.)
            # This would typically connect to alerting systems
            logger.info("Alert analysis not implemented - would connect to external alerting systems")

        except Exception as e:
            logger.error(f"Alerts analysis failed: {str(e)}")

        return incidents

    async def _ai_analyze_logs(self, log_content: str, source_type: str) -> List[DetectedIncident]:
        """Use AI to analyze logs for incidents"""

        system_prompt = f"""You are an expert DevOps engineer specializing in incident detection and log analysis.

        Analyze the provided {source_type} logs and identify potential incidents or issues.

        Look for:
        - Error patterns and exceptions
        - Performance degradation indicators
        - Security anomalies
        - Resource exhaustion signs
        - Service connectivity issues
        - Database problems
        - Application failures

        For each incident found, provide:
        - Incident type (from: system_outage, performance_degradation, security_breach, resource_exhaustion, network_connectivity, database_issues, application_error, deployment_failure, configuration_error, external_dependency)
        - Severity (critical, high, medium, low, info)
        - Clear title and description
        - Affected systems/services
        - Root cause analysis
        - Impact assessment

        Return valid JSON array of incidents."""

        user_prompt = f"""Analyze these {source_type} logs for incidents:

        ```
        {log_content[:3000]}  # Limit log content to avoid token limits
        ```

        Return JSON array of detected incidents with format:
        [{{
          "incident_type": "string",
          "severity": "string",
          "title": "string",
          "description": "string",
          "affected_systems": ["list"],
          "root_cause_analysis": "string",
          "impact_assessment": "string",
          "confidence": 0.8
        }}]"""

        try:
            # Generate analysis with structured output
            incidents_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Parse JSON response
            incidents_data = json.loads(incidents_json)

            # Convert to DetectedIncident objects
            incidents = []
            for incident_data in incidents_data:
                if isinstance(incident_data, dict):
                    incident = self._convert_ai_incident_to_object(incident_data, log_content, source_type)
                    if incident:
                        incidents.append(incident)

            return incidents

        except json.JSONDecodeError as e:
            logger.warning(f"AI analysis JSON parsing failed: {str(e)}")
            # Fallback to pattern-based detection
            return await self._pattern_based_detection(log_content, source_type)

        except Exception as e:
            logger.error(f"AI log analysis failed: {str(e)}")
            return []

    def _convert_ai_incident_to_object(self, incident_data: Dict[str, Any], log_content: str, source_type: str) -> Optional[DetectedIncident]:
        """Convert AI-generated incident data to DetectedIncident object"""

        try:
            # Parse incident type
            incident_type_str = incident_data.get("incident_type", "application_error")
            try:
                incident_type = IncidentType(incident_type_str)
            except ValueError:
                incident_type = IncidentType.APPLICATION_ERROR

            # Parse severity
            severity_str = incident_data.get("severity", "medium")
            try:
                severity = IncidentSeverity(severity_str)
            except ValueError:
                severity = IncidentSeverity.MEDIUM

            # Create evidence
            evidence = [
                IncidentEvidence(
                    source=source_type,
                    timestamp=datetime.now(),
                    content=log_content[:500],  # Truncate for storage
                    confidence=incident_data.get("confidence", 0.7),
                    metadata={"ai_generated": True},
                )
            ]

            # Generate incident ID
            incident_id = f"{incident_type.value}_{int(datetime.now().timestamp())}"

            return DetectedIncident(
                incident_id=incident_id,
                incident_type=incident_type,
                severity=severity,
                title=incident_data.get("title", "Detected Issue"),
                description=incident_data.get("description", "Issue detected in logs"),
                affected_systems=incident_data.get("affected_systems", ["unknown"]),
                root_cause_analysis=incident_data.get("root_cause_analysis", "Analysis pending"),
                impact_assessment=incident_data.get("impact_assessment", "Impact assessment pending"),
                evidence=evidence,
                detection_timestamp=datetime.now(),
                recommended_actions=incident_data.get("recommended_actions", []),
            )

        except Exception as e:
            logger.error(f"Incident conversion failed: {str(e)}")
            return None

    async def _pattern_based_detection(self, log_content: str, source_type: str) -> List[DetectedIncident]:
        """Fallback pattern-based incident detection"""
        # Make function truly async
        await asyncio.sleep(0)

        incidents = []

        for incident_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, log_content, re.IGNORECASE)
                    if matches:
                        # Create incident based on pattern match
                        incident = DetectedIncident(
                            incident_id=f"{incident_type.value}_{int(datetime.now().timestamp())}",
                            incident_type=incident_type,
                            severity=self._determine_severity_from_pattern(pattern),
                            title=f"{incident_type.value.replace('_', ' ').title()} Detected",
                            description=f"Pattern '{pattern}' found {len(matches)} times in {source_type}",
                            affected_systems=[source_type],
                            root_cause_analysis="Pattern-based detection - requires manual analysis",
                            impact_assessment="Impact assessment needed",
                            evidence=[
                                IncidentEvidence(
                                    source=source_type,
                                    timestamp=datetime.now(),
                                    content=str(matches[:3]),  # First 3 matches
                                    confidence=0.6,
                                    metadata={"pattern": pattern, "matches": len(matches)},
                                )
                            ],
                            detection_timestamp=datetime.now(),
                        )
                        incidents.append(incident)
                        break  # One incident per type to avoid duplicates

                except re.error as e:
                    logger.warning(f"Pattern error for {pattern}: {str(e)}")

        return incidents

    def _determine_severity_from_pattern(self, pattern: str) -> IncidentSeverity:
        """Determine severity based on pattern type"""

        critical_keywords = ["outage", "unavailable", "crash", "segmentation fault"]
        high_keywords = ["error", "exception", "failed", "timeout"]
        medium_keywords = ["warning", "degradation", "slow"]

        pattern_lower = pattern.lower()

        if any(keyword in pattern_lower for keyword in critical_keywords):
            return IncidentSeverity.CRITICAL
        elif any(keyword in pattern_lower for keyword in high_keywords):
            return IncidentSeverity.HIGH
        elif any(keyword in pattern_lower for keyword in medium_keywords):
            return IncidentSeverity.MEDIUM
        else:
            return IncidentSeverity.LOW

    def _create_metric_incident(self, title: str, description: str, incident_type: IncidentType, severity: IncidentSeverity) -> DetectedIncident:
        """Create incident from metric threshold violation"""

        return DetectedIncident(
            incident_id=f"{incident_type.value}_{int(datetime.now().timestamp())}",
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            affected_systems=["system"],
            root_cause_analysis="Metric threshold exceeded - investigation needed",
            impact_assessment="Performance impact likely",
            evidence=[
                IncidentEvidence(
                    source="metrics",
                    timestamp=datetime.now(),
                    content=description,
                    confidence=0.8,
                    metadata={"metric_based": True},
                )
            ],
            detection_timestamp=datetime.now(),
        )

    async def _correlate_incidents(self, incidents: List[DetectedIncident]) -> List[DetectedIncident]:
        """Correlate similar incidents to avoid duplicates"""
        # Make function truly async
        await asyncio.sleep(0)

        if not incidents:
            return incidents

        # Group by incident type and time proximity
        correlated = []
        processed_ids = set()

        for incident in incidents:
            if incident.incident_id in processed_ids:
                continue

            # Find similar incidents within 10 minutes
            similar = [incident]
            for other in incidents:
                if (
                    other.incident_id != incident.incident_id
                    and other.incident_id not in processed_ids
                    and other.incident_type == incident.incident_type
                    and abs((other.detection_timestamp - incident.detection_timestamp).total_seconds()) < 600
                ):
                    similar.append(other)
                    processed_ids.add(other.incident_id)

            # Merge similar incidents
            if len(similar) > 1:
                merged = self._merge_incidents(similar)
                correlated.append(merged)
            else:
                correlated.append(incident)

            processed_ids.add(incident.incident_id)

        return correlated

    def _merge_incidents(self, incidents: List[DetectedIncident]) -> DetectedIncident:
        """Merge similar incidents into one"""

        primary = incidents[0]

        # Combine evidence
        all_evidence = []
        for incident in incidents:
            all_evidence.extend(incident.evidence)

        # Combine affected systems
        all_systems = set()
        for incident in incidents:
            all_systems.update(incident.affected_systems)

        # Use highest severity
        max_severity = max(incidents, key=lambda x: list(IncidentSeverity).index(x.severity)).severity

        # Update description
        description_parts = [primary.description]
        if len(incidents) > 1:
            description_parts.append(f"(Merged from {len(incidents)} similar incidents)")

        return DetectedIncident(
            incident_id=primary.incident_id,
            incident_type=primary.incident_type,
            severity=max_severity,
            title=primary.title,
            description=" ".join(description_parts),
            affected_systems=list(all_systems),
            root_cause_analysis=primary.root_cause_analysis,
            impact_assessment=primary.impact_assessment,
            evidence=all_evidence,
            detection_timestamp=primary.detection_timestamp,
            metadata={"merged_count": len(incidents)},
        )

    async def _enrich_incidents_with_ai(self, incidents: List[DetectedIncident]) -> List[DetectedIncident]:
        """Enrich incidents with additional AI analysis"""

        enriched = []

        for incident in incidents:
            try:
                # Generate enhanced analysis
                system_prompt = """You are an expert SRE analyzing an incident.
                Provide enhanced incident analysis with:
                - Detailed root cause analysis
                - Impact assessment with business context
                - Estimated resolution time
                - Step-by-step recommended actions
                - Similar incident patterns to watch for

                Return JSON with these fields."""

                user_prompt = f"""Analyze this incident:

                Type: {incident.incident_type.value}
                Severity: {incident.severity.value}
                Title: {incident.title}
                Description: {incident.description}
                Affected Systems: {incident.affected_systems}
                Evidence: {[e.content[:100] for e in incident.evidence]}

                Provide enhanced analysis as JSON:
                {{
                  "root_cause_analysis": "detailed analysis",
                  "impact_assessment": "business impact",
                  "estimated_resolution_time": "time estimate",
                  "recommended_actions": ["action1", "action2"],
                  "similar_incidents": ["pattern1", "pattern2"]
                }}"""

                enhancement_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.2)

                # Parse and apply enhancements
                enhancement_data = json.loads(enhancement_json)

                incident.root_cause_analysis = enhancement_data.get("root_cause_analysis", incident.root_cause_analysis)
                incident.impact_assessment = enhancement_data.get("impact_assessment", incident.impact_assessment)
                incident.estimated_resolution_time = enhancement_data.get("estimated_resolution_time")
                incident.recommended_actions = enhancement_data.get("recommended_actions", [])
                incident.similar_incidents = enhancement_data.get("similar_incidents", [])

                enriched.append(incident)

            except Exception as e:
                logger.warning(f"Incident enrichment failed for {incident.incident_id}: {str(e)}")
                enriched.append(incident)  # Keep original

        return enriched

    def _calculate_confidence_score(self, incidents: List[DetectedIncident]) -> float:
        """Calculate overall confidence score for detection"""

        if not incidents:
            return 0.0

        # Calculate weighted confidence based on evidence
        total_confidence = 0.0
        total_weight = 0.0

        for incident in incidents:
            # Weight by severity
            severity_weights = {
                IncidentSeverity.CRITICAL: 1.0,
                IncidentSeverity.HIGH: 0.8,
                IncidentSeverity.MEDIUM: 0.6,
                IncidentSeverity.LOW: 0.4,
                IncidentSeverity.INFO: 0.2,
            }

            weight = severity_weights.get(incident.severity, 0.5)

            # Average evidence confidence
            evidence_confidence = sum(e.confidence for e in incident.evidence) / len(incident.evidence)

            total_confidence += evidence_confidence * weight
            total_weight += weight

        return total_confidence / total_weight if total_weight > 0 else 0.0

    async def _generate_general_recommendations(self, incidents: List[DetectedIncident]) -> List[str]:
        """Generate general recommendations based on detected incidents"""
        # Make function truly async
        await asyncio.sleep(0)

        if not incidents:
            return ["No incidents detected - system appears healthy"]

        recommendations = []

        # Count incidents by type
        incident_counts = {}
        for incident in incidents:
            incident_counts[incident.incident_type] = incident_counts.get(incident.incident_type, 0) + 1

        # Generate recommendations based on patterns
        if incident_counts.get(IncidentType.RESOURCE_EXHAUSTION, 0) > 0:
            recommendations.append("Consider implementing resource monitoring and auto-scaling")

        if incident_counts.get(IncidentType.APPLICATION_ERROR, 0) > 2:
            recommendations.append("Review application error handling and logging")

        if incident_counts.get(IncidentType.SECURITY_BREACH, 0) > 0:
            recommendations.append("Immediate security audit and access review required")

        if incident_counts.get(IncidentType.DATABASE_ISSUES, 0) > 0:
            recommendations.append("Database performance tuning and connection pooling review needed")

        # Critical incidents need immediate attention
        critical_incidents = [i for i in incidents if i.severity == IncidentSeverity.CRITICAL]
        if critical_incidents:
            recommendations.insert(
                0,
                f"URGENT: {len(critical_incidents)} critical incidents require immediate attention",
            )

        return recommendations

    async def detect_from_file(self, log_file_path: str) -> IncidentDetectionResult:
        """Detect incidents from specific log file"""

        try:
            # Read log file
            log_content = Path(log_file_path).read_text()

            # Analyze with AI
            incidents = await self._ai_analyze_logs(log_content, "file")

            # Calculate metrics
            confidence_score = self._calculate_confidence_score(incidents)
            recommendations = await self._generate_general_recommendations(incidents)

            return IncidentDetectionResult(
                success=True,
                incidents=incidents,
                total_analyzed_sources=1,
                analysis_duration=0.0,
                confidence_score=confidence_score,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"File-based incident detection failed: {str(e)}")
            return IncidentDetectionResult(success=False, error_message=str(e))

    async def detect_from_description(self, incident_description: str) -> IncidentDetectionResult:
        """Detect and classify incident from user description"""

        system_prompt = """You are an incident management expert.
        Based on the user's description, classify and analyze the incident.

        Determine:
        - Incident type and severity
        - Affected systems
        - Potential root causes
        - Impact assessment
        - Recommended immediate actions

        Return structured incident information."""

        user_prompt = f"""Analyze this incident description:
        "{incident_description}"

        Classify the incident and provide analysis as JSON:
        {{
          "incident_type": "string",
          "severity": "string",
          "title": "string",
          "description": "enhanced description",
          "affected_systems": ["list"],
          "root_cause_analysis": "analysis",
          "impact_assessment": "assessment",
          "recommended_actions": ["actions"],
          "estimated_resolution_time": "time estimate"
        }}"""

        try:
            incident_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            incident_data = json.loads(incident_json)
            incident = self._convert_ai_incident_to_object(incident_data, incident_description, "user_report")

            if incident:
                return IncidentDetectionResult(
                    success=True,
                    incidents=[incident],
                    total_analyzed_sources=1,
                    confidence_score=0.8,
                    recommendations=incident.recommended_actions,
                )
            else:
                raise IncidentDetectionError("Failed to create incident object")

        except Exception as e:
            logger.error(f"Description-based detection failed: {str(e)}")
            return IncidentDetectionResult(success=False, error_message=str(e))


# Convenience functions for CLI usage
async def quick_detect_system_incidents() -> IncidentDetectionResult:
    """Quick system incident detection"""
    detector = IncidentDetector()
    return await detector.detect_incidents(["system_logs", "metrics"])


async def detect_from_log_file(file_path: str) -> IncidentDetectionResult:
    """Detect incidents from log file"""
    detector = IncidentDetector()
    return await detector.detect_from_file(file_path)


async def classify_incident_description(description: str) -> IncidentDetectionResult:
    """Classify incident from description"""
    detector = IncidentDetector()
    return await detector.detect_from_description(description)
