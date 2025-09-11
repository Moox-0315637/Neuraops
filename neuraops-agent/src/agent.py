"""
Core NeuraOps Agent - Refactored with modular architecture

Main orchestrator with proper async exception handling.
Fixes SonarQube S7497, S7502 and Pylance errors through modular design.
Follows CLAUDE.md: < 200 lines, single responsibility, modular components.
"""
import asyncio
import logging
import os  # Added for Docker environment detection
import signal
import sys
from pathlib import Path
from typing import Optional

from .config import AgentConfig, load_config
from .connector import CoreConnector
from .collector import MetricsCollector
from .executor import CommandExecutor
from .modules import AsyncExceptionHandler, TaskManager, BackgroundLoops
from .daemon_utils import create_pid_file, is_agent_running, stop_agent, daemonize


class Agent:
    """
    Main NeuraOps Agent with modular architecture
    
    CLAUDE.md: < 200 lignes total avec architecture modulaire
    Fixes SonarQube S7497, S7502 via specialized modules
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize agent with modular components"""
        self.config = config or load_config()
        self.running = False
        
        # Setup logging first
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Modular components (fixes S7497, S7502)
        self.task_manager = TaskManager(self.logger)
        self.background_loops = BackgroundLoops()
        self.exception_handler = AsyncExceptionHandler()
        
        # Core components
        self.connector: Optional[CoreConnector] = None
        
        # Choose appropriate collector based on environment
        if self._is_docker_environment():
            from .docker_collector import DockerMetricsCollector
            self.collector = DockerMetricsCollector(self.config)
            self.logger.info("Using DockerMetricsCollector for containerized environment")
        else:
            from .collector import MetricsCollector
            self.collector = MetricsCollector(self.config)
            self.logger.info("Using standard MetricsCollector")
        
        self.executor = CommandExecutor(self.config)
        
        # Task references for proper shutdown (fixes S7502)
        self.metrics_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.command_task: Optional[asyncio.Task] = None
    
    def _setup_logging(self) -> None:
        """Configure logging for the agent - CLAUDE.md: < 20 lignes"""
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        handlers = [logging.StreamHandler(sys.stdout)]
        if self.config.log_file:
            handlers.append(logging.FileHandler(self.config.log_file))
        
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=handlers
        )

    def _is_docker_environment(self) -> bool:
        """
        Detect if agent is running in Docker environment with host access
        
        CLAUDE.md: < 15 lines - Simple Docker detection
        """
        # Check for Docker-specific environment variables
        if os.getenv('HOST_PROC') or os.getenv('HOST_SYS'):
            return True
        
        # Check for Docker container indicators
        if os.path.exists('/.dockerenv'):
            return True
        
        # Check if /proc/1/cgroup contains docker
        try:
            with open('/proc/1/cgroup', 'r') as f:
                return 'docker' in f.read()
        except (FileNotFoundError, PermissionError):
            pass
        
        return False
    
    async def start(self) -> None:
        """
        Start agent with modular architecture
        
        CLAUDE.md: < 50 lignes avec délégation aux modules
        Fixes S7502: Uses task_manager for proper task reference handling
        """
        if self.running:
            self.logger.warning("Agent is already running")
            return
        
        self.logger.info(f"Starting NeuraOps Agent '{self.config.agent_name}'")
        
        while self.running or not hasattr(self, '_initial_start_complete'):
            try:
                # Initialize core connector
                self.connector = CoreConnector(self.config)
                await self.connector.connect()
                self.logger.info(f"Connected to NeuraOps Core at {self.config.core_url}")
                
                # Start background services via modular loops
                self.running = True
                self.background_loops.start_all_loops(  # S7503: Remove await - function is now synchronous
                    self, self.collector, self.connector,
                    self._create_command_handler(), self.task_manager
                )
                
                # Setup signal handlers with proper task management
                self._setup_signal_handlers()
                
                self.logger.info("Agent started successfully")
                self._initial_start_complete = True
                
                # Keep main thread alive
                await self._wait_for_shutdown()
                break  # Exit loop if shutdown was clean
                
            except Exception as e:
                self.logger.error(f"Failed to start agent: {e}")
                
                # If this is the first connection attempt, fail fast
                if not hasattr(self, '_initial_start_complete'):
                    self.logger.error("Initial connection failed, stopping agent")
                    await self.stop()
                    raise
                
                # Otherwise, retry connection after a delay
                self.logger.info("Retrying connection in 30 seconds...")
                await asyncio.sleep(30)
    
    async def stop(self) -> None:
        """
        Stop agent with proper async exception handling
        
        CLAUDE.md: < 30 lignes avec gestion S7497 via modules
        Fixes S7497: Uses AsyncExceptionHandler for proper cancellation
        """
        if not self.running:
            return
        
        self.logger.info("Stopping NeuraOps Agent...")
        self.running = False
        
        # Cancel all tasks via task manager (fixes S7497 + S7502)
        await self.task_manager.cancel_all(timeout=10.0)
        
        # Disconnect from core
        if self.connector:
            await self.connector.disconnect()
        
        self.logger.info("Agent stopped successfully")
    
    def _setup_signal_handlers(self) -> None:
        """
        Setup graceful shutdown on signals
        
        CLAUDE.md: < 20 lignes avec task_manager pour S7502
        Fixes S7502: Uses task_manager.create_fire_and_forget_task
        """
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            
            # Fixes S7502: Save task reference via task_manager
            self.task_manager.create_fire_and_forget_task(
                self.stop(), 
                name=f"shutdown_signal_{signum}"
            )
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _create_command_handler(self):
        """
        Create command handler with proper task management
        
        CLAUDE.md: < 15 lignes - Factory pour command handler
        Fixes S7502: Command handling via task_manager
        Fixes S7503: Remove async keyword as no await is used
        """
        def handle_command(command: dict) -> None:
            command_id = command.get("id", "unknown")
            self.task_manager.create_fire_and_forget_task(
                self._handle_command(command),
                name=f"handle_command_{command_id}",
                error_callback=lambda e: self.logger.error(f"Command {command_id} failed: {e}")
            )
        
        return handle_command
    
    async def _handle_command(self, command: dict) -> None:
        """Handle command execution - CLAUDE.md: < 25 lignes"""
        try:
            self.logger.info(f"Executing command: {command.get('type', 'unknown')}")
            
            # Execute command
            result = await self.executor.execute(command)
            
            # Send result back to core
            if self.connector:
                await self.connector.send_command_result(command.get("id"), result)
            
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            
            # Send error result back
            if self.connector:
                await self.connector.send_command_result(
                    command.get("id"), 
                    {"error": str(e)}
                )
    
    async def _wait_for_shutdown(self) -> None:
        """Wait for shutdown signal - CLAUDE.md: < 10 lignes"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.debug("Wait for shutdown cancelled")
            raise 

# Note: daemonize, is_agent_running, stop_agent are now imported from daemon_utils
__all__ = ["Agent", "daemonize", "is_agent_running", "stop_agent"]