"""
Daemon Utilities for NeuraOps Agent

Handles daemon process management with proper os import.
Fixes Pylance error by ensuring os module is properly imported.
Follows CLAUDE.md: < 100 lines, single responsibility.
"""
import os
import sys
import signal
import logging
from pathlib import Path
from typing import Optional
from .config import NEURAOPS_DIR_NAME


logger = logging.getLogger(__name__)


def daemonize() -> None:
    """
    Run agent as daemon process
    
    CLAUDE.md: < 30 lines - Standard daemon pattern
    Fixes Pylance: os module properly imported at module level
    """
    logger.info("Starting daemon process")
    
    # Fork process
    try:
        if os.fork() > 0:
            sys.exit(0)  # Parent process exits
    except OSError as e:
        logger.error(f"Fork failed: {e}")
        sys.exit(1)
    
    # Become session leader
    os.setsid()
    
    # Second fork
    try:
        if os.fork() > 0:
            sys.exit(0)
    except OSError as e:
        logger.error(f"Second fork failed: {e}")
        sys.exit(1)
    
    # Change working directory and file permissions
    os.chdir("/")
    os.umask(0o022)
    
    # Redirect standard streams
    _redirect_streams()
    
    logger.info("Daemon process started")


def _redirect_streams() -> None:
    """
    Redirect standard streams to /dev/null
    
    CLAUDE.md: < 15 lines - Stream redirection helper
    """
    with open("/dev/null", "r") as dev_null:
        os.dup2(dev_null.fileno(), sys.stdin.fileno())
    
    with open("/dev/null", "w") as dev_null:
        os.dup2(dev_null.fileno(), sys.stdout.fileno())
        os.dup2(dev_null.fileno(), sys.stderr.fileno())


def is_agent_running() -> bool:
    """
    Check if agent daemon is running
    
    CLAUDE.md: < 20 lines - PID file check with proper os import
    Fixes Pylance: os module available at module level (line 7)
    
    Returns:
        True if agent is running, False otherwise
    """
    pid_file = get_pid_file_path()
    
    if not pid_file.exists():
        logger.debug("PID file not found")
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        # Fixes Pylance error: os properly imported
        os.kill(pid, 0)  # Check if process exists (signal 0)
        logger.debug(f"Agent running with PID {pid}")
        return True
        
    except (ValueError, ProcessLookupError, PermissionError) as e:
        logger.debug(f"Process check failed: {e}")
        # Remove stale pid file
        pid_file.unlink(missing_ok=True)
        return False


def stop_agent() -> None:
    """
    Stop running agent daemon
    
    CLAUDE.md: < 25 lines - Graceful daemon shutdown
    """
    pid_file = get_pid_file_path()
    
    if not pid_file.exists():
        logger.info("No PID file found, agent not running")
        return
    
    try:
        pid = int(pid_file.read_text().strip())
        logger.info(f"Stopping agent with PID {pid}")
        
        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)
        
        # Remove PID file
        pid_file.unlink()
        logger.info("Agent stopped successfully")
        
    except (ValueError, ProcessLookupError, PermissionError) as e:
        logger.error(f"Failed to stop agent: {e}")
        # Clean up stale PID file
        pid_file.unlink(missing_ok=True)


def create_pid_file(pid: Optional[int] = None) -> Path:
    """
    Create PID file for daemon process
    
    CLAUDE.md: < 15 lines - PID file creation
    
    Args:
        pid: Process ID to write (defaults to current process)
        
    Returns:
        Path to created PID file
    """
    pid_file = get_pid_file_path()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    
    current_pid = pid or os.getpid()
    pid_file.write_text(str(current_pid))
    
    logger.debug(f"Created PID file: {pid_file} with PID {current_pid}")
    return pid_file


def get_pid_file_path() -> Path:
    """
    Get path to PID file
    
    CLAUDE.md: < 10 lines - Simple path helper
    
    Returns:
        Path to PID file
    """
    return Path.home() / NEURAOPS_DIR_NAME / "agent.pid"