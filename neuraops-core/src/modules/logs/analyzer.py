"""
NeuraOps Intelligent Log Analyzer
AI-powered log analysis with pattern recognition and root cause analysis
"""

import logging
import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from ...core.engine import get_engine
from ...core.structured_output import LogAnalysisResult, SeverityLevel
from ...core.cache import get_cache_manager
from ...devops_commander.exceptions import LogAnalysisError
from .parser import LogParser, LogEntry, LogFormat

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Intelligent log analyzer with AI-powered insights"""

    def __init__(self):
        self.parser = LogParser()
        self.cache_manager = get_cache_manager()

        # Error patterns for quick identification
        self.error_patterns = {
            "connection_refused": r"connection refused|connection reset|connection timed out",
            "memory_error": r"out of memory|memory allocation|segmentation fault|oom",
            "disk_error": r"disk full|no space left|filesystem full|disk error",
            "network_error": r"network unreachable|host unreachable|dns resolution",
            "authentication_error": r"authentication failed|login failed|access denied",
            "database_error": r"database connection|sql error|deadlock|timeout",
            "service_down": r"service unavailable|service down|service not found",
            "performance_issue": r"timeout|slow query|high latency|response time",
        }

        # Warning patterns
        self.warning_patterns = {
            "deprecated": r"deprecated|legacy|obsolete",
            "resource_warning": r"high cpu|high memory|disk usage|load average",
            "configuration_warning": r"configuration warning|config mismatch|invalid config",
            "security_warning": r"security warning|suspicious activity|failed login",
        }

    async def analyze_file(
        self,
        file_path: Path,
        format_type: LogFormat = LogFormat.AUTO_DETECT,
        use_ai: bool = True,
        context: Optional[str] = None,
    ) -> LogAnalysisResult:
        """Analyze log file with comprehensive AI-powered analysis"""

        if not file_path.exists():
            raise LogAnalysisError(f"Log file not found: {file_path}")

        try:
            # Check cache first
            log_content = file_path.read_text(encoding="utf-8", errors="replace")
            # Generate cache key for log analysis
            import hashlib
            cache_key = f"log_analysis_{hashlib.md5(log_content.encode()).hexdigest()}"
            cached_analysis = await self.cache_manager.get(cache_key)

            if cached_analysis and use_ai:
                logger.info(f"Using cached analysis for {file_path}")
                return LogAnalysisResult.model_validate(cached_analysis)

            # Parse log file
            entries = self.parser.parse_file(file_path, format_type)

            if not entries:
                return LogAnalysisResult(
                    severity=SeverityLevel.INFO,
                    error_count=0,
                    warning_count=0,
                    recommendations=["Log file appears to be empty or unparseable"],
                )

            # Perform analysis
            analysis = await self._analyze_entries(entries, use_ai, context)

            # Cache results if AI was used
            if use_ai:
                # Cache the analysis result
                import hashlib
                cache_key = f"log_analysis_{hashlib.md5(log_content.encode()).hexdigest()}"
                await self.cache_manager.set(cache_key, analysis.model_dump())

            logger.info(
                f"Completed analysis of {file_path}: {analysis.severity} severity, {analysis.error_count} errors"
            )
            return analysis

        except Exception as e:
            raise LogAnalysisError(f"Log analysis failed: {str(e)}") from e

    async def analyze_text(
        self,
        log_text: str,
        format_type: LogFormat = LogFormat.AUTO_DETECT,
        use_ai: bool = True,
        context: Optional[str] = None,
    ) -> LogAnalysisResult:
        """Analyze log text with AI-powered insights"""

        try:
            # Check cache first
            if use_ai:
                # Generate cache key for log analysis
                import hashlib
                cache_key = f"log_analysis_{hashlib.md5(log_text.encode()).hexdigest()}"
                cached_analysis = await self.cache_manager.get(cache_key)
                if cached_analysis:
                    logger.info("Using cached analysis for log text")
                    return LogAnalysisResult.model_validate(cached_analysis)

            # Parse log text
            entries = self.parser.parse_text(log_text, format_type)

            if not entries:
                return LogAnalysisResult(
                    severity=SeverityLevel.INFO,
                    error_count=0,
                    warning_count=0,
                    recommendations=["Log text appears to be empty or unparseable"],
                )

            # Perform analysis
            analysis = await self._analyze_entries(entries, use_ai, context)

            # Cache results if AI was used
            if use_ai:
                # Cache the analysis result
                import hashlib
                cache_key = f"log_analysis_{hashlib.md5(log_text.encode()).hexdigest()}"
                await self.cache_manager.set(cache_key, analysis.model_dump())

            return analysis

        except Exception as e:
            raise LogAnalysisError(f"Log text analysis failed: {str(e)}") from e

    async def _analyze_entries(
        self, entries: List[LogEntry], use_ai: bool, context: Optional[str]
    ) -> LogAnalysisResult:
        """Analyze parsed log entries"""

        # Basic statistical analysis
        basic_stats = self._perform_basic_analysis(entries)

        if not use_ai:
            # Return basic analysis without AI enhancement
            return LogAnalysisResult(
                severity=basic_stats["severity"],
                error_count=basic_stats["error_count"],
                warning_count=basic_stats["warning_count"],
                error_patterns=basic_stats["error_patterns"],
                affected_services=basic_stats["affected_services"],
                recommendations=basic_stats["basic_recommendations"],
            )

        # AI-enhanced analysis
        ai_analysis = await self._perform_ai_analysis(entries, basic_stats, context)

        # Combine basic and AI analysis
        return LogAnalysisResult(
            severity=ai_analysis.get("severity", basic_stats["severity"]),
            error_count=basic_stats["error_count"],
            warning_count=basic_stats["warning_count"],
            critical_issues=ai_analysis.get("critical_issues", []),
            error_patterns=basic_stats["error_patterns"],
            affected_services=basic_stats["affected_services"],
            root_causes=ai_analysis.get("root_causes", []),
            recommendations=ai_analysis.get(
                "recommendations", basic_stats["basic_recommendations"]
            ),
            performance_metrics=ai_analysis.get("performance_metrics", {}),
            incident_timeline=ai_analysis.get("incident_timeline", []),
            security_issues=ai_analysis.get("security_issues", []),
        )

    def _perform_basic_analysis(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Perform basic statistical analysis of log entries"""

        # Count by level
        level_counts = Counter(entry.level for entry in entries)
        error_count = sum(
            count
            for level, count in level_counts.items()
            if level in ["ERROR", "CRITICAL", "FATAL"]
        )
        warning_count = level_counts.get("WARNING", 0) + level_counts.get("WARN", 0)

        # Determine overall severity
        if level_counts.get("CRITICAL", 0) > 0 or level_counts.get("FATAL", 0) > 0:
            severity = SeverityLevel.CRITICAL
        elif error_count > 10:
            severity = SeverityLevel.HIGH
        elif error_count > 0:
            severity = SeverityLevel.MEDIUM
        elif warning_count > 5:
            severity = SeverityLevel.LOW
        else:
            severity = SeverityLevel.INFO

        # Find error patterns
        error_patterns = self._find_error_patterns(entries)

        # Identify affected services
        affected_services = list({
            entry.source
            for entry in entries
            if entry.source and entry.level in ["ERROR", "CRITICAL", "FATAL"]
        })

        # Basic recommendations
        basic_recommendations = self._generate_basic_recommendations(
            error_count, warning_count, error_patterns, affected_services
        )

        return {
            "severity": severity,
            "error_count": error_count,
            "warning_count": warning_count,
            "error_patterns": error_patterns,
            "affected_services": affected_services,
            "basic_recommendations": basic_recommendations,
            "level_distribution": dict(level_counts),
        }

    def _find_error_patterns(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Find common error patterns in log entries"""

        pattern_counts = defaultdict(int)

        # Check error and warning entries
        error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL", "FATAL", "WARNING"]]

        for entry in error_entries:
            message = entry.message.lower()

            # Check predefined patterns
            for pattern_name, pattern_regex in self.error_patterns.items():
                if re.search(pattern_regex, message, re.IGNORECASE):
                    pattern_counts[pattern_name] += 1

            # Check warning patterns
            for pattern_name, pattern_regex in self.warning_patterns.items():
                if re.search(pattern_regex, message, re.IGNORECASE):
                    pattern_counts[f"warning_{pattern_name}"] += 1

        return dict(pattern_counts)

    def _generate_basic_recommendations(
        self,
        error_count: int,
        warning_count: int,
        error_patterns: Dict[str, int],
        affected_services: List[str],
    ) -> List[str]:
        """Generate basic recommendations based on analysis"""

        recommendations = []

        # Error-based recommendations
        if error_count > 0:
            recommendations.append(f"Investigate {error_count} error(s) found in logs")

        if warning_count > 5:
            recommendations.append(f"Review {warning_count} warning(s) that may indicate issues")

        # Pattern-based recommendations
        if "connection_refused" in error_patterns:
            recommendations.append("Check network connectivity and service availability")

        if "memory_error" in error_patterns:
            recommendations.append("Monitor memory usage and consider increasing allocation")

        if "disk_error" in error_patterns:
            recommendations.append("Check disk space and clean up if necessary")

        if "authentication_error" in error_patterns:
            recommendations.append("Review authentication configuration and credentials")

        # Service-based recommendations
        if affected_services:
            recommendations.append(
                f"Focus attention on services: {', '.join(affected_services[:3])}"
            )

        if not recommendations:
            recommendations.append("Logs appear healthy with no critical issues detected")

        return recommendations

    async def _perform_ai_analysis(
        self, entries: List[LogEntry], basic_stats: Dict[str, Any], context: Optional[str]
    ) -> Dict[str, Any]:
        """Perform AI-enhanced analysis of log entries"""

        try:
            engine = get_engine()

            # Prepare log sample for AI analysis
            log_sample = self._prepare_log_sample(entries)

            # Build analysis prompt
            prompt = f"""Analyze these system logs for errors, patterns, and issues:

{log_sample}

Basic Statistics:
- Total entries: {len(entries)}
- Error count: {basic_stats['error_count']}
- Warning count: {basic_stats['warning_count']}
- Level distribution: {basic_stats['level_distribution']}

{f"Additional context: {context}" if context else ""}

Provide comprehensive analysis including:
1. Critical issues requiring immediate attention
2. Root cause analysis for errors
3. Security concerns or anomalies
4. Performance-related issues
5. Actionable recommendations for resolution
6. Timeline of significant events"""

            # Generate structured analysis
            ai_result = await engine.generate_structured(
                prompt=prompt,
                output_schema=LogAnalysisResult,
                system_prompt="""You are an expert DevOps engineer and SRE with deep experience in log analysis.
                Analyze the provided logs systematically and identify:
                - Critical issues that need immediate attention
                - Root causes of errors and failures
                - Security concerns or suspicious activities
                - Performance bottlenecks and optimization opportunities
                - Actionable recommendations prioritized by impact""",
            )

            return ai_result.model_dump()

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            # Return basic analysis with error note
            return {
                "severity": basic_stats["severity"],
                "recommendations": basic_stats["basic_recommendations"]
                + [f"AI analysis failed: {str(e)}"],
                "root_causes": [],
                "critical_issues": [],
                "security_issues": [],
                "performance_metrics": {},
                "incident_timeline": [],
            }

    def _prepare_log_sample(self, entries: List[LogEntry], max_entries: int = 50) -> str:
        """Prepare a representative sample of log entries for AI analysis"""

        # Prioritize error and warning entries
        priority_entries = [
            e for e in entries if e.level in ["ERROR", "CRITICAL", "FATAL", "WARNING"]
        ]

        # If we have many priority entries, take a sample
        if len(priority_entries) > max_entries // 2:
            priority_entries = priority_entries[: max_entries // 2]

        # Fill remaining slots with other entries
        remaining_slots = max_entries - len(priority_entries)
        other_entries = [
            e for e in entries if e.level not in ["ERROR", "CRITICAL", "FATAL", "WARNING"]
        ]

        if other_entries and remaining_slots > 0:
            # Take evenly distributed sample
            step = max(1, len(other_entries) // remaining_slots)
            other_entries = other_entries[::step][:remaining_slots]

        # Combine and sort by timestamp
        sample_entries = priority_entries + other_entries
        sample_entries.sort(key=lambda x: x.timestamp or datetime.min)

        # Format for AI analysis
        log_lines = []
        for entry in sample_entries:
            timestamp_str = (
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "UNKNOWN"
            )
            source_str = f"[{entry.source}]" if entry.source else ""
            log_lines.append(f"{timestamp_str} {entry.level} {source_str} {entry.message}")

        return "\n".join(log_lines)

    def analyze_real_time(self, log_stream: str) -> Dict[str, Any]:
        """Analyze log stream in real-time"""

        # Parse new entries
        new_entries = self.parser.parse_text(log_stream)

        if not new_entries:
            return {"status": "no_new_entries"}

        # Basic analysis for real-time
        error_entries = [e for e in new_entries if e.level in ["ERROR", "CRITICAL", "FATAL"]]
        warning_entries = [e for e in new_entries if e.level == "WARNING"]

        # Quick pattern matching
        error_patterns = self._find_error_patterns(new_entries)

        # Determine if immediate attention needed
        needs_attention = (
            len(error_entries) > 0
            or len(warning_entries) > 5
            or any(count > 3 for count in error_patterns.values())
        )

        return {
            "status": "analyzed",
            "new_entries_count": len(new_entries),
            "error_count": len(error_entries),
            "warning_count": len(warning_entries),
            "error_patterns": error_patterns,
            "needs_attention": needs_attention,
            "latest_errors": [e.message for e in error_entries[-3:]] if error_entries else [],
        }

    def _calculate_hourly_counts(self, entries: List[LogEntry]) -> Dict:
        """Group entries by hour for anomaly detection"""
        hourly_counts = defaultdict(int)
        for entry in entries:
            if entry.timestamp:
                hour_key = entry.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_counts[hour_key] += 1
        return hourly_counts

    def _calculate_statistics(self, counts: List[int]) -> tuple:
        """Calculate mean and standard deviation for anomaly detection"""
        if not counts:
            return 0, 0
        avg_count = sum(counts) / len(counts)
        variance = sum((x - avg_count) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5
        return avg_count, std_dev

    def _find_time_anomalies(self, hourly_counts: Dict, avg_count: float, std_dev: float, threshold: float) -> List[Dict[str, Any]]:
        """Find time-based anomalies (high activity periods)"""
        anomalies = []
        for hour, count in hourly_counts.items():
            if count > avg_count + (threshold * std_dev):
                anomalies.append({
                    "type": "high_activity",
                    "timestamp": hour.isoformat(),
                    "count": count,
                    "average": round(avg_count, 1),
                    "deviation": round((count - avg_count) / std_dev, 1),
                })
        return anomalies

    def _find_error_spike_anomalies(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Find error burst anomalies (many errors in short time)"""
        anomalies = []
        error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL", "FATAL"]]
        
        if len(error_entries) <= 5:
            return anomalies

        # Check for error bursts (many errors in short time)
        sorted_errors = sorted(error_entries, key=lambda x: x.timestamp or datetime.min)

        for i in range(len(sorted_errors) - 4):
            window_entries = sorted_errors[i : i + 5]
            if all(e.timestamp for e in window_entries):
                time_span = (window_entries[-1].timestamp - window_entries[0].timestamp).total_seconds()
                if time_span < 60:  # 5 errors in less than 1 minute
                    anomalies.append({
                        "type": "error_burst",
                        "start_time": window_entries[0].timestamp.isoformat(),
                        "end_time": window_entries[-1].timestamp.isoformat(),
                        "error_count": len(window_entries),
                        "time_span_seconds": time_span,
                    })
        return anomalies

    def identify_anomalies(
        self, entries: List[LogEntry], threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Identify anomalous log patterns"""

        anomalies = []

        # Time-based anomaly detection
        if len(entries) > 10:
            hourly_counts = self._calculate_hourly_counts(entries)

            if len(hourly_counts) > 1:
                counts = list(hourly_counts.values())
                avg_count, std_dev = self._calculate_statistics(counts)
                
                # Find time-based anomalies
                time_anomalies = self._find_time_anomalies(hourly_counts, avg_count, std_dev, threshold)
                anomalies.extend(time_anomalies)

        # Error burst detection
        error_spike_anomalies = self._find_error_spike_anomalies(entries)
        anomalies.extend(error_spike_anomalies)

        return anomalies

    def _extract_response_times(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Extract response time metrics from log entries"""
        response_times = []
        response_time_pattern = re.compile(
            r"(?:response time|duration|took|elapsed)[:\s]*(\d+(?:\.\d+)?)\s*(ms|s|seconds?|milliseconds?)",
            re.IGNORECASE,
        )

        for entry in entries:
            match = response_time_pattern.search(entry.message)
            if match:
                time_value = float(match.group(1))
                unit = match.group(2).lower()

                # Convert to milliseconds
                if unit.startswith("s"):
                    time_value *= 1000

                response_times.append({
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "value_ms": time_value,
                    "source": entry.source,
                })
        return response_times

    def _calculate_error_rates(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Calculate error rates by time window"""
        error_rates = {}
        
        if not entries:
            return error_rates

        # Group by hour
        hourly_stats = defaultdict(lambda: {"total": 0, "errors": 0})

        for entry in entries:
            if entry.timestamp:
                hour_key = entry.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
                hourly_stats[hour_key]["total"] += 1
                if entry.level in ["ERROR", "CRITICAL", "FATAL"]:
                    hourly_stats[hour_key]["errors"] += 1

        # Calculate error rates
        for hour, stats in hourly_stats.items():
            error_rate = (stats["errors"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            error_rates[hour] = {
                "error_rate_percent": round(error_rate, 2),
                "total_entries": stats["total"],
                "error_count": stats["errors"],
            }
        
        return error_rates

    def _extract_resource_usage(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Extract resource usage metrics from log entries"""
        resource_usage = {}
        
        cpu_pattern = re.compile(r"cpu[:\s]*(\d+(?:\.\d+)?)%", re.IGNORECASE)
        memory_pattern = re.compile(r"memory[:\s]*(\d+(?:\.\d+)?)%", re.IGNORECASE)

        for entry in entries:
            cpu_match = cpu_pattern.search(entry.message)
            if cpu_match:
                resource_usage["cpu_percent"] = float(cpu_match.group(1))

            memory_match = memory_pattern.search(entry.message)
            if memory_match:
                resource_usage["memory_percent"] = float(memory_match.group(1))
        
        return resource_usage

    def extract_performance_metrics(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Extract performance-related metrics from logs"""

        metrics = {
            "response_times": self._extract_response_times(entries),
            "error_rates": self._calculate_error_rates(entries),
            "resource_usage": self._extract_resource_usage(entries),
            "throughput": {}
        }

        return metrics

    def create_incident_timeline(self, entries: List[LogEntry]) -> List[Dict[str, str]]:
        """Create timeline of significant events"""

        timeline = []

        # Focus on errors and critical events
        significant_entries = [
            e for e in entries if e.level in ["ERROR", "CRITICAL", "FATAL", "WARNING"]
        ]

        # Sort by timestamp
        significant_entries.sort(key=lambda x: x.timestamp or datetime.min)

        # Group nearby events
        for entry in significant_entries[:20]:  # Limit to most recent/significant
            timeline.append(
                {
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else "unknown",
                    "level": entry.level,
                    "source": entry.source or "unknown",
                    "event": (
                        entry.message[:100] + "..." if len(entry.message) > 100 else entry.message
                    ),
                }
            )

        return timeline

    def get_analysis_summary(self, analysis: LogAnalysisResult) -> str:
        """Generate human-readable summary of analysis"""

        summary_parts = []

        # Overall status
        summary_parts.append(f"Overall severity: {analysis.severity.value.upper()}")

        # Issue counts
        if analysis.error_count > 0:
            summary_parts.append(f"{analysis.error_count} errors detected")

        if analysis.warning_count > 0:
            summary_parts.append(f"{analysis.warning_count} warnings found")

        # Critical issues
        if analysis.critical_issues:
            summary_parts.append(
                f"{len(analysis.critical_issues)} critical issues require attention"
            )

        # Affected services
        if analysis.affected_services:
            services_text = ", ".join(analysis.affected_services[:3])
            if len(analysis.affected_services) > 3:
                services_text += f" (+{len(analysis.affected_services) - 3} more)"
            summary_parts.append(f"Affected services: {services_text}")

        # Recommendations count
        if analysis.recommendations:
            summary_parts.append(f"{len(analysis.recommendations)} recommendations provided")

        return ". ".join(summary_parts) + "."
