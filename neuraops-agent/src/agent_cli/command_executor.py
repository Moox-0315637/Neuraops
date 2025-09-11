# src/agent_cli/command_executor.py
"""
Agent Command Executor

CLAUDE.md: < 500 lignes, exécution sécurisée des commandes côté agent
Coordonne l'exécution des commandes locales sur l'hôte agent
"""
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging
import asyncio
import time
from abc import ABC, abstractmethod

from .health_commands import AgentHealthCommands
from .system_commands import AgentSystemCommands


class CommandExecutionError(Exception):
    """Exception raised when command execution fails"""
    pass


class UnsupportedCommandError(Exception):
    """Exception raised when command is not supported by agent"""
    pass


class AgentCommandExecutor:
    """
    Execute commands locally on agent host
    
    CLAUDE.md: Single responsibility pour exécution commandes agent
    """
    
    def __init__(self):
        """Initialize command executor"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize command modules
        self.health_commands = AgentHealthCommands()
        self.system_commands = AgentSystemCommands()
        
        # Command registry
        self._command_registry = self._build_command_registry()
    
    def _build_command_registry(self) -> Dict[str, Callable]:
        """Build registry of available commands"""
        return {
            # Health commands
            "health.disk": self.health_commands.check_disk_status,
            "health.cpu-memory": self.health_commands.check_cpu_memory,
            "health.network": self.health_commands.check_network_status,
            "health.processes": self.health_commands.list_processes,
            "health.monitor": self.health_commands.monitor_system,
            "health.check-disk-status": self.health_commands.check_disk_status,
            "health.check-cpu-memory": self.health_commands.check_cpu_memory,
            "health.check-network": self.health_commands.check_network_status,
            "health.list-processes": self.health_commands.list_processes,
            "health.system-health": self._execute_system_health,
            
            # System commands
            "system.info": self.system_commands.get_system_info,
            "system.environment": self.system_commands.show_environment,
            "system.show-environment": self.system_commands.show_environment,
            "system.system-info": self.system_commands.get_system_info,
            "system.get-system-info": self.system_commands.get_system_info,
            
            # Filesystem commands
            "fs.list": self._execute_filesystem_list,
            "filesystem.list": self._execute_filesystem_list,
        }
    
    async def execute(self, command: str, args: List[str], timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Execute command on agent host
        
        Args:
            command: Main command (e.g., 'health')
            args: Command arguments (e.g., ['disk'])
            timeout_seconds: Execution timeout
            
        Returns:
            Command execution result
        """
        start_time = time.time()
        
        try:
            # Build command key
            subcommand = args[0] if args else None
            command_key = f"{command}.{subcommand}" if subcommand else command
            
            self.logger.info(f"Executing agent command: {command_key}")
            
            # Check if command is supported
            if command_key not in self._command_registry:
                raise UnsupportedCommandError(f"Command '{command_key}' not supported by agent")
            
            # Get command function
            command_func = self._command_registry[command_key]
            
            # Prepare arguments
            func_args = self._prepare_arguments(command_func, args[1:] if len(args) > 1 else [])
            
            # Execute command with timeout
            try:
                if asyncio.iscoroutinefunction(command_func):
                    result = await asyncio.wait_for(
                        command_func(**func_args),
                        timeout=timeout_seconds
                    )
                else:
                    # Run sync function in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: command_func(**func_args)
                    )
            except asyncio.TimeoutError:
                raise CommandExecutionError(f"Command '{command_key}' timed out after {timeout_seconds}s")
            
            execution_time = time.time() - start_time
            
            # Wrap result in standard format
            return {
                "success": True,
                "return_code": 0,
                "command": command,
                "subcommand": subcommand,
                "agent_data": result,
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except (UnsupportedCommandError, CommandExecutionError) as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Command execution failed: {e}")
            
            return {
                "success": False,
                "return_code": 1,
                "command": command,
                "subcommand": subcommand,
                "error": str(e),
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Unexpected error executing command: {e}", exc_info=True)
            
            return {
                "success": False,
                "return_code": 2,
                "command": command,
                "subcommand": subcommand,
                "error": f"Unexpected error: {str(e)}",
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _prepare_arguments(self, command_func: Callable, args: List[str]) -> Dict[str, Any]:
        """
        Prepare arguments for command function with reduced complexity
        
        Args:
            command_func: Command function to call
            args: Raw command arguments
            
        Returns:
            Dictionary of prepared arguments
        """
        func_args = {}
        parser = ArgumentParser(args)
        handlers = self._get_argument_handlers()
        
        for param_name in command_func.__code__.co_varnames:
            if param_name in handlers:
                value = handlers[param_name].parse(parser)
                if value is not None:
                    func_args[param_name] = value
        
        return func_args
    
    def _get_argument_handlers(self) -> Dict[str, 'ArgumentHandlerBase']:
        """Get mapping of parameter names to their handlers"""
        return {
            "all_filesystems": BooleanArgumentHandler("--all-filesystems", "-a"),
            "detailed": BooleanArgumentHandler("--detailed", "-d"),
            "sensitive": BooleanArgumentHandler("--include-sensitive", "-s"),
            "limit": IntegerArgumentHandler("--limit"),
            "duration_seconds": IntegerArgumentHandler("--duration"),
            "pattern": StringArgumentHandler("--pattern"),
            "path": StringArgumentHandler("--path"),
            "sort_by": EnumArgumentHandler({
                "--sort-by-cpu": "cpu",
                "--sort-by-memory": "memory", 
                "--sort-by-name": "name"
            })
        }
    
    def _execute_system_health(self, **kwargs) -> Dict[str, Any]:
        """Execute comprehensive system health check"""
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "health_checks": {}
            }
            
            # Run multiple health checks
            result["health_checks"]["disk"] = self.health_commands.check_disk_status()
            result["health_checks"]["cpu_memory"] = self.health_commands.check_cpu_memory()
            result["health_checks"]["network"] = self.health_commands.check_network_status()
            result["health_checks"]["system_info"] = self.system_commands.get_system_info()
            
            # Determine overall health status
            has_errors = any(
                "error" in check for check in result["health_checks"].values()
            )
            
            result["overall_status"] = "healthy" if not has_errors else "degraded"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in system health check: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _execute_filesystem_list(self, path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute filesystem listing command"""
        try:
            from ..collector import MetricsCollector
            from ..docker_collector import DockerMetricsCollector
            
            # Get the collector from agent config
            collector = None
            if hasattr(self, 'collector'):
                collector = self.collector
            else:
                # Fallback: create collector based on environment
                from ..config import AgentConfig
                from ..agent import Agent
                
                # Try to get from current agent instance
                import os
                config = AgentConfig()
                
                # Check if we're in Docker environment
                if os.path.exists('/.dockerenv') or os.getenv('HOST_PROC'):
                    collector = DockerMetricsCollector(config)
                else:
                    collector = MetricsCollector(config)
            
            if not collector:
                return {"error": "No collector available", "timestamp": datetime.now().isoformat()}
            
            # Get filesystem information
            if hasattr(collector, 'collect_filesystem'):
                filesystems = collector.collect_filesystem()
            else:
                # Fallback to simple filesystem listing
                filesystems = self._get_simple_filesystem_info()
            
            # Filter by path if provided
            if path and path != "/":
                filtered_filesystems = []
                for fs in filesystems:
                    if fs.get('mountpoint', '').startswith(path):
                        filtered_filesystems.append(fs)
                filesystems = filtered_filesystems
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "path_requested": path or "/",
                "filesystems": filesystems,
                "total_filesystems": len(filesystems)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in filesystem list command: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _get_simple_filesystem_info(self) -> List[Dict[str, Any]]:
        """Simple filesystem info fallback"""
        try:
            import psutil
            filesystems = []
            
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    filesystem = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                    
                    filesystems.append(filesystem)
                    
                except OSError:
                    # Skip inaccessible mount points
                    continue
            
            return filesystems
        except Exception:
            return []
    
    def get_supported_commands(self) -> Dict[str, List[str]]:
        """Get list of supported commands"""
        commands = {}
        
        for command_key in self._command_registry.keys():
            if "." in command_key:
                module, cmd = command_key.split(".", 1)
                if module not in commands:
                    commands[module] = []
                if cmd not in commands[module]:
                    commands[module].append(cmd)
        
        return commands
    
    def is_supported(self, command: str, subcommand: Optional[str] = None) -> bool:
        """Check if command is supported by agent"""
        command_key = f"{command}.{subcommand}" if subcommand else command
        return command_key in self._command_registry


# Argument parsing classes for reduced complexity (SonarQube S3776)

class ArgumentParser:
    """Centralized argument parsing utilities"""
    
    def __init__(self, args: List[str]):
        self.args = args
    
    def has_flag(self, *flags: str) -> bool:
        """Check if any of the given flags exist"""
        return any(flag in self.args for flag in flags)
    
    def get_value_after_flag(self, flag: str) -> Optional[str]:
        """Get value after a flag, returns None if not found or no value"""
        try:
            flag_idx = self.args.index(flag)
            if flag_idx + 1 < len(self.args):
                return self.args[flag_idx + 1]
        except ValueError:
            pass
        return None
    
    def get_integer_after_flag(self, flag: str) -> Optional[int]:
        """Get integer value after a flag"""
        value = self.get_value_after_flag(flag)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None


class ArgumentHandlerBase(ABC):
    """Base class for argument handlers"""
    
    @abstractmethod
    def parse(self, parser: ArgumentParser) -> Any:
        """Parse arguments using the given parser"""
        pass


class BooleanArgumentHandler(ArgumentHandlerBase):
    """Handle boolean flag arguments"""
    
    def __init__(self, *flags: str):
        self.flags = flags
    
    def parse(self, parser: ArgumentParser) -> bool:
        return parser.has_flag(*self.flags)


class IntegerArgumentHandler(ArgumentHandlerBase):
    """Handle integer value arguments"""
    
    def __init__(self, flag: str, default: Optional[int] = None):
        self.flag = flag
        self.default = default
    
    def parse(self, parser: ArgumentParser) -> Optional[int]:
        value = parser.get_integer_after_flag(self.flag)
        return value if value is not None else self.default


class StringArgumentHandler(ArgumentHandlerBase):
    """Handle string value arguments"""
    
    def __init__(self, flag: str):
        self.flag = flag
    
    def parse(self, parser: ArgumentParser) -> Optional[str]:
        return parser.get_value_after_flag(self.flag)


class EnumArgumentHandler(ArgumentHandlerBase):
    """Handle enum/choice arguments"""
    
    def __init__(self, choices: Dict[str, str]):
        self.choices = choices  # {"--sort-by-cpu": "cpu", ...}
    
    def parse(self, parser: ArgumentParser) -> Optional[str]:
        for flag, value in self.choices.items():
            if parser.has_flag(flag):
                return value
        return None