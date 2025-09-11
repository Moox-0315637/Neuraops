"""
NeuraOps Log Parser Engine
Multi-format log parsing with intelligent pattern recognition
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from ...devops_commander.exceptions import LogAnalysisError

logger = logging.getLogger(__name__)


class LogFormat(str, Enum):
    """Supported log formats"""

    SYSLOG = "syslog"
    JSON = "json"
    NGINX = "nginx"
    APACHE = "apache"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    WINDOWS_EVENT = "windows_event"
    CUSTOM = "custom"
    AUTO_DETECT = "auto"


@dataclass
class LogEntry:
    """Structured representation of a log entry"""

    timestamp: Optional[datetime]
    level: str
    message: str
    source: Optional[str] = None
    raw_line: str = ""
    line_number: int = 0
    parsed_fields: Dict[str, Any] = None

    def __post_init__(self):
        if self.parsed_fields is None:
            self.parsed_fields = {}


class LogPatterns:
    """Predefined patterns for common log formats"""

    # Syslog pattern
    SYSLOG = re.compile(
        r"(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<hostname>\S+)\s+"
        r"(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s*"
        r"(?P<message>.*)"
    )

    # JSON logs pattern (flexible)
    JSON_FIELDS = ["timestamp", "time", "ts", "datetime", "@timestamp"]
    MESSAGE_FIELDS = ["message", "msg", "log", "text"]
    LEVEL_FIELDS = ["level", "severity", "loglevel", "priority"]

    # Nginx access log pattern
    NGINX_ACCESS = re.compile(
        r"(?P<remote_addr>\S+)\s+"
        r"(?P<remote_user>\S+)\s+"
        r"(?P<time_local>\[[^\]]+\])\s+"
        r'"(?P<request>[^"]+)"\s+'
        r"(?P<status>\d+)\s+"
        r"(?P<body_bytes_sent>\d+)\s+"
        r'"(?P<http_referer>[^"]*)"\s+'
        r'"(?P<http_user_agent>[^"]*)"'
    )

    # Apache access log pattern
    APACHE_ACCESS = re.compile(
        r"(?P<remote_addr>\S+)\s+"
        r"(?P<remote_logname>\S+)\s+"
        r"(?P<remote_user>\S+)\s+"
        r"(?P<time_local>\[[^\]]+\])\s+"
        r'"(?P<request>[^"]+)"\s+'
        r"(?P<status>\d+)\s+"
        r"(?P<bytes_sent>\S+)"
    )

    # Docker container logs
    DOCKER = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+"
        r"(?P<stream>stdout|stderr)\s+"
        r"(?P<tag>\S+)\s+"
        r"(?P<message>.*)"
    )

    # Kubernetes logs
    KUBERNETES = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+"
        r"(?P<level>\w+)\s+"
        r"(?P<component>\S+)\s+"
        r"(?P<message>.*)"
    )


class LogParser:
    """Intelligent log parser supporting multiple formats"""

    def __init__(self):
        self.custom_patterns: Dict[str, re.Pattern] = {}
        self.format_detectors = {
            LogFormat.JSON: self._detect_json_format,
            LogFormat.SYSLOG: self._detect_syslog_format,
            LogFormat.NGINX: self._detect_nginx_format,
            LogFormat.APACHE: self._detect_apache_format,
            LogFormat.DOCKER: self._detect_docker_format,
            LogFormat.KUBERNETES: self._detect_kubernetes_format,
        }

    def parse_file(
        self,
        file_path: Path,
        format_type: LogFormat = LogFormat.AUTO_DETECT,
        max_lines: Optional[int] = None,
    ) -> List[LogEntry]:
        """Parse log file and return structured entries"""

        if not file_path.exists():
            raise LogAnalysisError(f"Log file not found: {file_path}", log_file=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if max_lines:
                lines = lines[:max_lines]

            # Auto-detect format if needed
            if format_type == LogFormat.AUTO_DETECT:
                format_type = self._auto_detect_format(
                    lines[:10]
                )  # Use first 10 lines for detection
                logger.info(f"Auto-detected log format: {format_type}")

            # Parse lines
            entries = []
            for line_num, line in enumerate(lines, 1):
                try:
                    entry = self._parse_line(line.rstrip("\n\r"), format_type, line_num)
                    if entry:
                        entries.append(entry)
                except Exception as e:
                    logger.debug(f"Failed to parse line {line_num}: {str(e)}")
                    # Create fallback entry
                    entries.append(
                        LogEntry(
                            timestamp=None,
                            level="UNKNOWN",
                            message=line.strip(),
                            raw_line=line,
                            line_number=line_num,
                        )
                    )

            logger.info(f"Parsed {len(entries)} log entries from {file_path}")
            return entries

        except Exception as e:
            raise LogAnalysisError(
                f"Failed to parse log file: {str(e)}",
                log_file=str(file_path),
                log_format=format_type.value,
            ) from e

    def parse_text(
        self, log_text: str, format_type: LogFormat = LogFormat.AUTO_DETECT
    ) -> List[LogEntry]:
        """Parse log text and return structured entries"""

        lines = log_text.split("\n")

        # Auto-detect format if needed
        if format_type == LogFormat.AUTO_DETECT:
            format_type = self._auto_detect_format(lines[:10])

        entries = []
        for line_num, line in enumerate(lines, 1):
            if line.strip():  # Skip empty lines
                try:
                    entry = self._parse_line(line, format_type, line_num)
                    if entry:
                        entries.append(entry)
                except Exception as e:
                    logger.debug(f"Failed to parse line {line_num}: {str(e)}")
                    # Create fallback entry
                    entries.append(
                        LogEntry(
                            timestamp=None,
                            level="UNKNOWN",
                            message=line.strip(),
                            raw_line=line,
                            line_number=line_num,
                        )
                    )

        return entries

    def _auto_detect_format(self, sample_lines: List[str]) -> LogFormat:
        """Auto-detect log format from sample lines"""

        format_scores = {}

        for format_type, detector in self.format_detectors.items():
            try:
                score = detector(sample_lines)
                format_scores[format_type] = score
            except Exception:
                format_scores[format_type] = 0.0

        # Return format with highest score
        best_format = max(format_scores, key=format_scores.get)
        best_score = format_scores[best_format]

        # Fallback to syslog if no format has good confidence
        if best_score < 0.3:
            return LogFormat.SYSLOG

        return best_format

    def _parse_line(
        self, line: str, format_type: LogFormat, line_number: int
    ) -> Optional[LogEntry]:
        """Parse a single log line based on format"""

        if not line.strip():
            return None

        try:
            if format_type == LogFormat.JSON:
                return self._parse_json_line(line, line_number)
            elif format_type == LogFormat.SYSLOG:
                return self._parse_syslog_line(line, line_number)
            elif format_type == LogFormat.NGINX:
                return self._parse_nginx_line(line, line_number)
            elif format_type == LogFormat.APACHE:
                return self._parse_apache_line(line, line_number)
            elif format_type == LogFormat.DOCKER:
                return self._parse_docker_line(line, line_number)
            elif format_type == LogFormat.KUBERNETES:
                return self._parse_kubernetes_line(line, line_number)
            else:
                return self._parse_generic_line(line, line_number)

        except Exception as e:
            logger.debug(f"Line parsing failed: {str(e)}")
            return None

    def _parse_json_line(self, line: str, line_number: int) -> LogEntry:
        """Parse JSON format log line"""

        try:
            data = json.loads(line)

            # Extract timestamp
            timestamp = None
            for field in LogPatterns.JSON_FIELDS:
                if field in data:
                    timestamp = self._parse_timestamp(str(data[field]))
                    break

            # Extract message
            message = ""
            for field in LogPatterns.MESSAGE_FIELDS:
                if field in data:
                    message = str(data[field])
                    break

            # Extract level
            level = "INFO"
            for field in LogPatterns.LEVEL_FIELDS:
                if field in data:
                    level = str(data[field]).upper()
                    break

            # Extract source
            source = data.get("service") or data.get("component") or data.get("logger")

            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=str(source) if source else None,
                raw_line=line,
                line_number=line_number,
                parsed_fields=data,
            )

        except json.JSONDecodeError:
            raise LogAnalysisError(f"Invalid JSON format at line {line_number}")

    def _parse_syslog_line(self, line: str, line_number: int) -> LogEntry:
        """Parse syslog format log line"""

        match = LogPatterns.SYSLOG.match(line)
        if not match:
            return LogEntry(
                timestamp=None,
                level="UNKNOWN",
                message=line,
                raw_line=line,
                line_number=line_number,
            )

        groups = match.groupdict()

        timestamp = self._parse_timestamp(groups["timestamp"])
        process = groups.get("process", "")

        # Extract log level from message if present
        message = groups["message"]
        level = self._extract_level_from_message(message)

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=process,
            raw_line=line,
            line_number=line_number,
            parsed_fields=groups,
        )

    def _parse_nginx_line(self, line: str, line_number: int) -> LogEntry:
        """Parse Nginx access log line"""

        match = LogPatterns.NGINX_ACCESS.match(line)
        if not match:
            return self._parse_generic_line(line, line_number)

        groups = match.groupdict()

        # Parse timestamp
        time_str = groups["time_local"].strip("[]")
        timestamp = self._parse_timestamp(time_str)

        # Determine level based on status code
        status = int(groups.get("status", 200))
        if status >= 500:
            level = "ERROR"
        elif status >= 400:
            level = "WARNING"
        else:
            level = "INFO"

        # Build message
        request = groups.get("request", "")
        message = f"{request} -> {status}"

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source="nginx",
            raw_line=line,
            line_number=line_number,
            parsed_fields=groups,
        )

    def _parse_apache_line(self, line: str, line_number: int) -> LogEntry:
        """Parse Apache access log line"""

        match = LogPatterns.APACHE_ACCESS.match(line)
        if not match:
            return self._parse_generic_line(line, line_number)

        groups = match.groupdict()

        # Parse timestamp
        time_str = groups["time_local"].strip("[]")
        timestamp = self._parse_timestamp(time_str)

        # Determine level based on status code
        status = int(groups.get("status", 200))
        if status >= 500:
            level = "ERROR"
        elif status >= 400:
            level = "WARNING"
        else:
            level = "INFO"

        # Build message
        request = groups.get("request", "")
        message = f"{request} -> {status}"

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source="apache",
            raw_line=line,
            line_number=line_number,
            parsed_fields=groups,
        )

    def _parse_docker_line(self, line: str, line_number: int) -> LogEntry:
        """Parse Docker container log line"""

        match = LogPatterns.DOCKER.match(line)
        if not match:
            return self._parse_generic_line(line, line_number)

        groups = match.groupdict()

        timestamp = self._parse_timestamp(groups["timestamp"])

        # Use stream as level indicator
        level = "ERROR" if groups["stream"] == "stderr" else "INFO"

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=groups["message"],
            source=f"docker:{groups.get('tag', 'unknown')}",
            raw_line=line,
            line_number=line_number,
            parsed_fields=groups,
        )

    def _parse_kubernetes_line(self, line: str, line_number: int) -> LogEntry:
        """Parse Kubernetes log line"""

        match = LogPatterns.KUBERNETES.match(line)
        if not match:
            return self._parse_generic_line(line, line_number)

        groups = match.groupdict()

        timestamp = self._parse_timestamp(groups["timestamp"])
        level = groups.get("level", "INFO").upper()

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=groups["message"],
            source=f"k8s:{groups.get('component', 'unknown')}",
            raw_line=line,
            line_number=line_number,
            parsed_fields=groups,
        )

    def _parse_generic_line(self, line: str, line_number: int) -> LogEntry:
        """Parse generic log line with basic pattern recognition"""

        # Try to extract timestamp from beginning
        timestamp = self._extract_timestamp_from_line(line)

        # Extract log level
        level = self._extract_level_from_message(line)

        return LogEntry(
            timestamp=timestamp, level=level, message=line, raw_line=line, line_number=line_number
        )

    def _extract_timestamp_from_line(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line using common patterns"""

        # Common timestamp patterns
        timestamp_patterns = [
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?",  # ISO format
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # Standard format
            r"\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",  # Syslog format
            r"\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}",  # Apache format
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return self._parse_timestamp(match.group())

        return None

    def _extract_level_from_message(self, message: str) -> str:
        """Extract log level from message content"""

        message_upper = message.upper()

        # Check for explicit level indicators
        level_patterns = {
            "CRITICAL": ["CRITICAL", "FATAL", "PANIC"],
            "ERROR": ["ERROR", "ERR", "FAIL", "EXCEPTION"],
            "WARNING": ["WARNING", "WARN", "ALERT"],
            "INFO": ["INFO", "INFORMATION"],
            "DEBUG": ["DEBUG", "TRACE"],
        }

        for level, patterns in level_patterns.items():
            for pattern in patterns:
                if pattern in message_upper:
                    return level

        # Default level based on content
        if any(word in message_upper for word in ["ERROR", "FAIL", "EXCEPTION", "CRASH"]):
            return "ERROR"
        elif any(word in message_upper for word in ["WARN", "ALERT", "DEPRECATED"]):
            return "WARNING"
        else:
            return "INFO"

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string into datetime object"""

        timestamp_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO with microseconds and Z
            "%Y-%m-%dT%H:%M:%SZ",  # ISO with Z
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
            "%Y-%m-%dT%H:%M:%S",  # ISO basic
            "%Y-%m-%d %H:%M:%S.%f",  # Standard with microseconds
            "%Y-%m-%d %H:%M:%S",  # Standard basic
            "%b %d %H:%M:%S",  # Syslog format
            "%d/%b/%Y:%H:%M:%S",  # Apache format
        ]

        for fmt in timestamp_formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        logger.debug(f"Could not parse timestamp: {timestamp_str}")
        return None

    # Format detection methods
    def _detect_json_format(self, lines: List[str]) -> float:
        """Detect JSON log format"""
        json_count = 0
        for line in lines:
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    json.loads(line)
                    json_count += 1
                except json.JSONDecodeError:
                    pass

        return json_count / len(lines) if lines else 0.0

    def _detect_syslog_format(self, lines: List[str]) -> float:
        """Detect syslog format"""
        match_count = 0
        for line in lines:
            if LogPatterns.SYSLOG.match(line):
                match_count += 1

        return match_count / len(lines) if lines else 0.0

    def _detect_nginx_format(self, lines: List[str]) -> float:
        """Detect Nginx access log format"""
        match_count = 0
        for line in lines:
            if LogPatterns.NGINX_ACCESS.match(line):
                match_count += 1

        return match_count / len(lines) if lines else 0.0

    def _detect_apache_format(self, lines: List[str]) -> float:
        """Detect Apache access log format"""
        match_count = 0
        for line in lines:
            if LogPatterns.APACHE_ACCESS.match(line):
                match_count += 1

        return match_count / len(lines) if lines else 0.0

    def _detect_docker_format(self, lines: List[str]) -> float:
        """Detect Docker log format"""
        match_count = 0
        for line in lines:
            if LogPatterns.DOCKER.match(line):
                match_count += 1

        return match_count / len(lines) if lines else 0.0

    def _detect_kubernetes_format(self, lines: List[str]) -> float:
        """Detect Kubernetes log format"""
        match_count = 0
        for line in lines:
            if LogPatterns.KUBERNETES.match(line):
                match_count += 1

        return match_count / len(lines) if lines else 0.0

    def add_custom_pattern(self, name: str, pattern: str) -> None:
        """Add custom regex pattern for log parsing"""
        try:
            self.custom_patterns[name] = re.compile(pattern)
            logger.info(f"Added custom pattern: {name}")
        except re.error as e:
            raise LogAnalysisError(f"Invalid regex pattern: {str(e)}")

    def get_parsing_stats(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Get statistics about parsed log entries"""

        if not entries:
            return {"total_entries": 0}

        # Count by level
        level_counts = {}
        sources = set()
        timestamps_parsed = 0

        for entry in entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
            if entry.source:
                sources.add(entry.source)
            if entry.timestamp:
                timestamps_parsed += 1

        # Time range
        time_range = None
        timestamps = [e.timestamp for e in entries if e.timestamp]
        if timestamps:
            time_range = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat(),
                "duration_minutes": (max(timestamps) - min(timestamps)).total_seconds() / 60,
            }

        return {
            "total_entries": len(entries),
            "level_distribution": level_counts,
            "unique_sources": len(sources),
            "sources": list(sources),
            "timestamps_parsed_percent": (timestamps_parsed / len(entries)) * 100,
            "time_range": time_range,
        }
