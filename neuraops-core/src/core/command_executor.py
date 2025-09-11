"""
NeuraOps Secure Command Executor
Security-focused command execution with whitelisting, validation, and audit trails
"""

import os
import re
import asyncio
import logging
import threading
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from pathlib import Path
import shlex

from ..devops_commander.config import get_config, SecurityConfig
from ..devops_commander.exceptions import (
    SecurityViolationError,
    CommandExecutionError,
    ValidationError,
)
from .structured_output import DevOpsCommand, SafetyLevel

logger = logging.getLogger(__name__)


class CommandResult:
    """Result of command execution with metadata"""

    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        execution_time: float = 0.0,
        safety_level: SafetyLevel = SafetyLevel.SAFE,
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.execution_time = execution_time
        self.safety_level = safety_level
        self.executed_at = datetime.now(timezone.utc)
        self.success = exit_code == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time": self.execution_time,
            "safety_level": self.safety_level.value,
            "executed_at": self.executed_at.isoformat(),
        }


class SecurityValidator:
    """Security validation for command execution"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self._compiled_patterns = [re.compile(pattern) for pattern in config.dangerous_patterns]

    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Validate command against security policies"""

        if not self.config.validation_enabled:
            return True, None

        command = command.strip()

        # Check for empty command
        if not command:
            return False, "Empty command not allowed"

        # Parse command to get base command
        try:
            parsed_args = shlex.split(command)
            if not parsed_args:
                return False, "Invalid command format"

            base_command = parsed_args[0]

        except ValueError as e:
            return False, f"Command parsing failed: {str(e)}"

        # Check whitelist if enabled
        if self.config.whitelist_enabled:
            if base_command not in self.config.allowed_commands:
                return False, f"Command '{base_command}' is not in the whitelist"

        # Check blacklist
        if base_command in self.config.blocked_commands:
            return False, f"Command '{base_command}' is explicitly blocked"

        # Check dangerous patterns - include exact phrase "dangerous pattern"
        for pattern in self._compiled_patterns:
            if pattern.search(command):
                return False, "This command contains a dangerous pattern and cannot be executed for security reasons."

        # Check for command injection attempts - include exact phrase "command injection detected"
        if self._detect_injection_attempts(command):
            return False, "Potential command injection detected and blocked for security reasons."

        return True, None

    def _detect_injection_attempts(self, command: str) -> bool:
        """Detect potential command injection attempts"""

        injection_indicators = [
            ";",
            "&&",
            "||",
            "|",
            ">",
            ">>",
            "<",
            "$(",
            "`",
            "$((",
            "${",
            "\n",
            "\r",
            "\\n",
            "\\r",
        ]

        # Check for basic injection patterns
        for indicator in injection_indicators:
            if indicator in command:
                # Allow some safe cases
                if indicator in ["|"] and "grep" in command:
                    continue
                if indicator in [">", ">>"] and any(safe in command for safe in ["tee", "log", ".txt", ".log"]):
                    continue
                return True

        return False

    def assess_safety_level(self, command: str) -> SafetyLevel:
        """Assess the safety level of a command"""

        command_lower = command.lower()

        # Dangerous operations (highest priority)
        dangerous_commands = {"rm", "delete", "drop", "truncate", "format", "destroy", "mkfs"}
        if any(cmd in command_lower for cmd in dangerous_commands):
            return SafetyLevel.DANGEROUS

        # Moderate operations (services, containers, etc.)
        moderate_commands = {"systemctl", "service", "docker", "kubectl", "nginx", "apache"}
        if any(cmd in command_lower for cmd in moderate_commands):
            return SafetyLevel.MODERATE

        # Safe/Read-only operations (lowest risk)
        safe_commands = {"echo", "ls", "cat", "grep", "find", "head", "tail", "ps", "df", "free", "top", "pwd", "date", "whoami", "id", "env"}
        if any(cmd in command_lower for cmd in safe_commands):
            return SafetyLevel.SAFE

        # Default to moderate for unknown commands
        return SafetyLevel.MODERATE


class AuditLogger:
    """Audit logging for command execution"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self._lock = threading.Lock()

        # Ensure audit log directory exists
        if self.config.audit_enabled:
            try:
                self.config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                # Failed to create directory - logging will be disabled silently
                pass

    def log_command_execution(
        self,
        command: str,
        result: CommandResult,
        user: str = "system",
        validation_result: Optional[Tuple[bool, Optional[str]]] = None,
    ) -> None:
        """Log command execution for audit trail"""

        if not self.config.audit_enabled:
            return

        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "command": command,
            "safety_level": result.safety_level.value,
            "exit_code": result.exit_code,
            "success": result.success,
            "execution_time": result.execution_time,
            "validation_passed": validation_result[0] if validation_result else True,
            "validation_message": validation_result[1] if validation_result else None,
        }

        try:
            with self._lock:
                with open(self.config.audit_log_path, "a") as f:
                    f.write(json.dumps(audit_entry) + "\n")

        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")

    def log_security_violation(self, command: str, violation_reason: str, user: str = "system") -> None:
        """Log security violations"""

        if not self.config.audit_enabled:
            return

        violation_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "SECURITY_VIOLATION",
            "user": user,
            "command": command,
            "violation_reason": violation_reason,
            "blocked": True,
        }

        try:
            with self._lock:
                with open(self.config.audit_log_path, "a") as f:
                    f.write(json.dumps(violation_entry) + "\n")

        except Exception as e:
            logger.error(f"Failed to log security violation: {str(e)}")


class SecureCommandExecutor:
    """Secure command executor with comprehensive safety checks"""

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or get_config().security
        self.validator = SecurityValidator(self.config)
        self.audit_logger = AuditLogger(self.config)
        self._execution_lock = asyncio.Lock()

    async def execute_command(
        self,
        command: str,
        timeout_seconds: int = 300,
        working_dir: Optional[Path] = None,
        env_vars: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
        user: str = "system",
    ) -> CommandResult:
        """Execute command with full security validation"""

        # Validate command security
        is_valid, validation_message = self.validator.validate_command(command)

        if not is_valid:
            self.audit_logger.log_security_violation(command, validation_message, user)
            raise SecurityViolationError(
                f"Command blocked: {validation_message}",
                command=command,
                violation_type="security_policy",
            )

        # Assess safety level
        safety_level = self.validator.assess_safety_level(command)

        # Handle dry run
        if dry_run:
            return CommandResult(
                command=command,
                exit_code=0,
                stdout=f"DRY RUN: Would execute '{command}' with safety level {safety_level.value}",
                stderr="",
                execution_time=0.0,
                safety_level=safety_level,
            )

        # Execute command with safety measures
        async with self._execution_lock:
            result = await self._execute_with_safety(
                command=command,
                timeout_seconds=timeout_seconds,
                working_dir=working_dir,
                env_vars=env_vars,
                safety_level=safety_level,
            )

        # Log execution
        self.audit_logger.log_command_execution(command, result, user, (is_valid, validation_message))

        return result

    async def execute_devops_command(self, devops_cmd: DevOpsCommand, user: str = "system", force_execute: bool = False) -> CommandResult:
        """Execute a structured DevOps command"""

        # Check if confirmation is required
        if devops_cmd.requires_confirmation and not force_execute:
            raise SecurityViolationError(
                f"Command requires explicit confirmation: {devops_cmd.command}",
                command=devops_cmd.command,
                violation_type="confirmation_required",
            )

        # Execute with structured command context
        result = await self.execute_command(command=devops_cmd.command, timeout_seconds=devops_cmd.timeout_seconds, user=user)

        # Run verification commands if provided
        if devops_cmd.verification_commands and result.success:
            for verification_cmd in devops_cmd.verification_commands:
                try:
                    await self.execute_command(verification_cmd, timeout_seconds=30, user=user)
                except Exception as e:
                    logger.warning(f"Verification command failed: {verification_cmd} - {str(e)}")

        return result

    async def _execute_with_safety(
        self,
        command: str,
        timeout_seconds: int,
        working_dir: Optional[Path],
        env_vars: Optional[Dict[str, str]],
        safety_level: SafetyLevel,
    ) -> CommandResult:
        """Execute command with appropriate safety measures"""

        start_time = datetime.now(timezone.utc)

        try:
            # Prepare environment
            env = dict(os.environ)
            if env_vars:
                env.update(env_vars)

            # Prepare working directory
            cwd = str(working_dir) if working_dir else None

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                async with asyncio.timeout(timeout_seconds):
                    stdout, stderr = await process.communicate()

                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

                return CommandResult(
                    command=command,
                    exit_code=process.returncode,
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    execution_time=execution_time,
                    safety_level=safety_level,
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                raise CommandExecutionError(f"Command timed out after {timeout_seconds} seconds", command=command, exit_code=-1)

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            if isinstance(e, CommandExecutionError):
                raise

            raise CommandExecutionError(f"Command execution failed: {str(e)}", command=command, exit_code=-1) from e

    async def execute_batch_commands(
        self,
        commands: List[str],
        fail_fast: bool = True,
        max_parallel: int = 3,
        user: str = "system",
    ) -> List[CommandResult]:
        """Execute multiple commands with controlled parallelism"""

        results = []
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_single(cmd: str) -> CommandResult:
            async with semaphore:
                return await self.execute_command(cmd, user=user)

        # Create tasks properly with asyncio.create_task
        tasks = [asyncio.create_task(execute_single(cmd)) for cmd in commands]

        if fail_fast:
            results = await self._execute_fail_fast(tasks)
        else:
            results = await self._execute_all_commands(tasks, commands)

        return results

    async def _execute_fail_fast(self, tasks: List[asyncio.Task]) -> List[CommandResult]:
        """Execute tasks with fail-fast behavior"""
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)

                if not result.success:
                    await self._cancel_remaining_tasks(tasks)
                    break

            except Exception as e:
                logger.error(f"Batch command execution failed: {str(e)}")
                await self._cancel_remaining_tasks(tasks)
                raise
        return results

    async def _execute_all_commands(self, tasks: List[asyncio.Task], commands: List[str]) -> List[CommandResult]:
        """Execute all commands regardless of failures"""
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                results[i] = CommandResult(
                    command=commands[i],
                    exit_code=-1,
                    stderr=str(result),
                    safety_level=SafetyLevel.SAFE,
                )
        return results

    async def _cancel_remaining_tasks(self, tasks: List[asyncio.Task]) -> None:
        """Cancel remaining tasks and wait for them to be cancelled"""
        # Annuler toutes les tâches non terminées
        cancelled_tasks = []
        for remaining_task in tasks:
            if not remaining_task.done():
                remaining_task.cancel()
                cancelled_tasks.append(remaining_task)

        # Attendre que les tâches annulées se terminent
        if cancelled_tasks:
            await asyncio.gather(*cancelled_tasks, return_exceptions=True)

    def validate_devops_command_structure(self, cmd: DevOpsCommand) -> bool:
        """Validate DevOps command structure and consistency"""

        try:
            # Basic validation
            if not cmd.command.strip():
                raise ValidationError("Command cannot be empty", field="command")

            if not cmd.description.strip():
                raise ValidationError("Description cannot be empty", field="description")

            # Safety level consistency
            if cmd.safety_level == SafetyLevel.DANGEROUS and not cmd.requires_confirmation:
                raise ValidationError("Dangerous commands must require confirmation", field="requires_confirmation")

            # Command security validation
            is_valid, message = self.validator.validate_command(cmd.command)
            if not is_valid:
                raise ValidationError(f"Command security validation failed: {message}", field="command")

            # Skip timeout validation as timeout_seconds is not part of DevOpsCommand model
            # Timeout is handled separately during command execution

            return True

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Command structure validation failed: {str(e)}")

    def test_command_safety(self, command: str) -> Dict[str, Any]:
        """Test command safety without execution"""
        safety_report = self._initialize_safety_report(command)
        
        try:
            self._perform_security_validation(safety_report, command)
            self._assess_command_safety_level(safety_report, command)
            self._evaluate_risk_factors(safety_report)
            
        except Exception as e:
            safety_report["error"] = str(e)
            safety_report["safe_to_execute"] = False
        
        return safety_report

    def _initialize_safety_report(self, command: str) -> Dict[str, Any]:
        """Helper: Initialize safety report structure"""
        return {
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "safety_assessment": {},
        }

    def _perform_security_validation(self, safety_report: Dict[str, Any], command: str) -> None:
        """Helper: Perform security validation and update report"""
        is_valid, validation_message = self.validator.validate_command(command)
        safety_report["security_validation"] = {
            "passed": is_valid,
            "message": validation_message,
        }

    def _assess_command_safety_level(self, safety_report: Dict[str, Any], command: str) -> None:
        """Helper: Assess safety level and update report"""
        safety_level = self.validator.assess_safety_level(command)
        safety_report["safety_level"] = safety_level.value

    def _evaluate_risk_factors(self, safety_report: Dict[str, Any]) -> None:
        """Helper: Evaluate risk factors and determine execution safety"""
        risk_factors = []
        safety_level = SafetyLevel(safety_report["safety_level"])
        is_valid = safety_report["security_validation"]["passed"]
        validation_message = safety_report["security_validation"]["message"]
        
        if safety_level in [SafetyLevel.MODERATE, SafetyLevel.DANGEROUS]:
            risk_factors.append(f"Command classified as {safety_level.value}")
        
        if not is_valid:
            risk_factors.append(f"Security validation failed: {validation_message}")
        
        safety_report["risk_factors"] = risk_factors
        safety_report["safe_to_execute"] = is_valid and safety_level != SafetyLevel.DANGEROUS

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get command execution statistics"""

        # This would typically read from audit logs
        # For now, return basic info
        stats = {
            "audit_enabled": self.config.audit_enabled,
            "whitelist_enabled": self.config.whitelist_enabled,
            "validation_enabled": self.config.validation_enabled,
            "allowed_commands_count": len(self.config.allowed_commands),
            "blocked_commands_count": len(self.config.blocked_commands),
            "dangerous_patterns_count": len(self.config.dangerous_patterns),
        }

        return stats


# Global executor instance
_executor_instance: Optional[SecureCommandExecutor] = None


def get_command_executor() -> SecureCommandExecutor:
    """Get the global command executor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SecureCommandExecutor()
    return _executor_instance


async def safe_execute(command: str, **kwargs) -> CommandResult:
    """Convenience function for safe command execution"""
    executor = get_command_executor()
    return await executor.execute_command(command, **kwargs)


def validate_command_safety(command: str) -> Dict[str, Any]:
    """Convenience function for command safety testing"""
    executor = get_command_executor()
    return executor.test_command_safety(command)


# Alias for backward compatibility
CommandExecutor = SecureCommandExecutor
