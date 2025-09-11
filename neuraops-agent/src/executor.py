"""Secure command executor for NeuraOps Agent."""

import asyncio
import json
import os
import subprocess
import shlex
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

from .config import AgentConfig


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    command_type: str
    error_message: Optional[str] = None


class CommandExecutor:
    """Executes commands received from NeuraOps Core securely."""
    
    def __init__(self, config: AgentConfig):
        """Initialize executor with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Command whitelist for security
        self.allowed_command_patterns = [
            # System info commands
            "systemctl status", "ps", "df", "free", "uptime", "whoami",
            "uname", "lscpu", "lsblk", "mount", "netstat", "ss",
            
            # Log reading (safe paths only)
            "tail", "head", "cat", "less", "grep",
            
            # Service management (read-only by default)
            "journalctl",
        ]
        
        # Update from config
        if hasattr(self.config, 'allowed_commands'):
            self.allowed_command_patterns.extend(self.config.allowed_commands)
    
    async def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command based on its type."""
        if not self.config.enable_command_execution:
            return {"error": "Command execution is disabled in agent configuration"}
        
        cmd_type = command.get("type", "unknown")
        cmd_id = command.get("id", "unknown")
        
        self.logger.info(f"Executing command {cmd_id}: {cmd_type}")
        
        try:
            if cmd_type == "shell":
                result = await self._execute_shell(command)
            elif cmd_type == "file_read":
                result = self._read_file(command)  # Sync call - no await needed
            elif cmd_type == "file_list":
                result = self._list_directory(command)  # Sync call - no await needed
            elif cmd_type == "service_status":
                result = await self._service_status(command)
            elif cmd_type == "system_info":
                result = self._system_info()  # S1172: No command parameter needed
            else:
                result = CommandResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    execution_time=0.0,
                    command_type=cmd_type,
                    error_message=f"Unknown command type: {cmd_type}"
                )
            
            return self._serialize_result(result)
            
        except Exception as e:
            self.logger.error(f"Error executing command {cmd_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "command_type": cmd_type,
                "command_id": cmd_id
            }
    
    async def _execute_shell(self, command: Dict[str, Any]) -> CommandResult:
        """Execute a shell command with security checks."""
        cmd = command.get("cmd", "")
        timeout = command.get("timeout", self.config.command_timeout)
        
        # Security check - validate command against whitelist
        if not self._is_command_allowed(cmd):
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=0.0,
                command_type="shell",
                error_message=f"Command not allowed: {cmd}"
            )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Use shell=False for security, parse command properly
            cmd_parts = shlex.split(cmd)
            
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=command.get("cwd", "/tmp"),
                env=self._get_safe_env()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                return CommandResult(
                    success=proc.returncode == 0,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace'),
                    return_code=proc.returncode,
                    execution_time=execution_time,
                    command_type="shell"
                )
                
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    execution_time=timeout,
                    command_type="shell",
                    error_message=f"Command timed out after {timeout}s"
                )
        
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=execution_time,
                command_type="shell",
                error_message=str(e)
            )
    
    def _read_file(self, command: Dict[str, Any]) -> CommandResult:  # S7503: Remove async - no await used
        """Read a file safely."""
        file_path = command.get("path", "")
        max_size = command.get("max_size", 1024 * 1024)  # 1MB default
        
        if not file_path or not self._is_path_safe(file_path):
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=0.0,
                command_type="file_read",
                error_message=f"Path not allowed or invalid: {file_path}"
            )
        
        start_time = time.time()  # Use time.time() for sync function
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr="File not found",
                    return_code=2,
                    execution_time=0.0,
                    command_type="file_read"
                )
            
            if path.stat().st_size > max_size:
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr=f"File too large (>{max_size} bytes)",
                    return_code=1,
                    execution_time=0.0,
                    command_type="file_read"
                )
            
            content = path.read_text(encoding='utf-8', errors='replace')
            execution_time = time.time() - start_time  # Use time.time() for sync function
            
            return CommandResult(
                success=True,
                stdout=content,
                stderr="",
                return_code=0,
                execution_time=execution_time,
                command_type="file_read"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time  # Use time.time() for sync function
            
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=execution_time,
                command_type="file_read",
                error_message=str(e)
            )
    
    def _list_directory(self, command: Dict[str, Any]) -> CommandResult:  # S7503: Remove async - no await used
        """List directory contents safely."""
        dir_path = command.get("path", "")
        
        if not dir_path or not self._is_path_safe(dir_path):
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=0.0,
                command_type="file_list",
                error_message=f"Path not allowed: {dir_path}"
            )
        
        start_time = time.time()  # Use time.time() for sync function
        
        try:
            path = Path(dir_path)
            
            if not path.exists() or not path.is_dir():
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr="Directory not found",
                    return_code=2,
                    execution_time=0.0,
                    command_type="file_list"
                )
            
            items = []
            for item in path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            execution_time = time.time() - start_time  # Use time.time() for sync function
            
            return CommandResult(
                success=True,
                stdout=json.dumps(items, indent=2),
                stderr="",
                return_code=0,
                execution_time=execution_time,
                command_type="file_list"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time  # Use time.time() for sync function
            
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=execution_time,
                command_type="file_list",
                error_message=str(e)
            )
    
    async def _service_status(self, command: Dict[str, Any]) -> CommandResult:
        """Get service status using systemctl."""
        service_name = command.get("service", "")
        
        if not service_name.replace("-", "").replace("_", "").isalnum():
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                execution_time=0.0,
                command_type="service_status",
                error_message="Invalid service name"
            )
        
        # Use the shell executor for systemctl
        return await self._execute_shell({
            "cmd": f"systemctl status {service_name}",
            "timeout": 10
        })
    
    def _system_info(self) -> CommandResult:  # S7503: Remove async - no await used, S1172: Remove unused command parameter
        """Gather system information."""
        # Use collector for system info
        from .collector import MetricsCollector
        
        collector = MetricsCollector(self.config)
        info = collector.collect_basic()
        
        return CommandResult(
            success=True,
            stdout=json.dumps(info, indent=2),
            stderr="",
            return_code=0,
            execution_time=0.1,
            command_type="system_info"
        )
    
    def _is_command_allowed(self, cmd: str) -> bool:
        """Check if command is allowed based on whitelist."""
        cmd = cmd.strip().lower()
        
        for pattern in self.allowed_command_patterns:
            if cmd.startswith(pattern.lower()):
                return True
        
        return False
    
    def _is_path_safe(self, path: str) -> bool:
        """Check if path is safe to access."""
        # Resolve path to prevent directory traversal
        try:
            resolved = Path(path).resolve()
            
            # Dangerous paths
            dangerous_paths = [
                "/etc/passwd", "/etc/shadow", "/etc/sudoers",
                "/root/.ssh", "/home/*/.ssh", "*.key", "*.pem"
            ]
            
            path_str = str(resolved)
            for danger in dangerous_paths:
                if danger in path_str:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _get_safe_env(self) -> Dict[str, str]:
        """Get a safe environment for command execution."""
        safe_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "USER": "neuraops-agent",
            "SHELL": "/bin/bash"
        }
        
        # Add some safe variables from current env
        for var in ["LANG", "LC_ALL", "TZ"]:
            if var in os.environ:
                safe_env[var] = os.environ[var]
        
        return safe_env
    
    def _serialize_result(self, result: CommandResult) -> Dict[str, Any]:
        """Convert CommandResult to dictionary."""
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "execution_time": result.execution_time,
            "command_type": result.command_type,
            "error_message": result.error_message
        }