"""Utility functions for NeuraOps Agent."""

import os
import signal
import sys
import psutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from .config import NEURAOPS_DIR_NAME


def setup_logger(name: str, level: str = "INFO", file_path: Optional[str] = None) -> logging.Logger:
    """Setup a logger with consistent formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler if specified
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Console formatter
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def ensure_directory(path: str | Path) -> Path:
    """Ensure directory exists, create if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """Get process information by PID."""
    try:
        process = psutil.Process(pid)
        return {
            "pid": pid,
            "name": process.name(),
            "status": process.status(),
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "create_time": process.create_time(),
            "cmdline": process.cmdline()
        }
    except psutil.NoSuchProcess:
        return None
    except Exception:
        return {"pid": pid, "error": "Access denied or process error"}


def is_process_running(pid: int) -> bool:
    """Check if a process is running by PID."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_process_tree(pid: int, timeout: int = 5) -> bool:
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Terminate children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        # Terminate parent
        parent.terminate()
        
        # Wait for graceful termination
        _, alive = psutil.wait_procs(children + [parent], timeout=timeout)
        
        # Force kill if still alive
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
        
        return True
        
    except psutil.NoSuchProcess:
        return True  # Already gone
    except Exception:
        return False


def safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string, return None on error."""
    try:
        import json
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


def truncate_string(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate string to maximum length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_bytes(bytes_count: int) -> str:
    """Format bytes count in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def get_system_username() -> str:
    """Get current system username safely."""
    return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def get_home_directory() -> Path:
    """Get user home directory safely."""
    return Path.home()


def create_pid_file(pid_file: str | Path, pid: Optional[int] = None) -> None:
    """Create PID file with current or specified PID."""
    pid_file = Path(pid_file)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    
    current_pid = pid or os.getpid()
    pid_file.write_text(str(current_pid))


def remove_pid_file(pid_file: str | Path) -> None:
    """Remove PID file if it exists."""
    pid_file = Path(pid_file)
    pid_file.unlink(missing_ok=True)


def read_pid_file(pid_file: str | Path) -> Optional[int]:
    """Read PID from file, return None if not found or invalid."""
    try:
        pid_file = Path(pid_file)
        if not pid_file.exists():
            return None
        
        pid_str = pid_file.read_text().strip()
        return int(pid_str)
    except (ValueError, FileNotFoundError, PermissionError):
        return None


def validate_url(url: str) -> bool:
    """Validate if URL format is correct."""
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_agent_data_dir() -> Path:
    """Get agent data directory, create if necessary."""
    data_dir = Path.home() / NEURAOPS_DIR_NAME
    data_dir.mkdir(exist_ok=True)
    return data_dir


def clean_environment_for_subprocess() -> Dict[str, str]:
    """Get a clean environment for subprocess execution."""
    safe_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(Path.home()),
        "USER": get_system_username(),
        "SHELL": "/bin/bash",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8"
    }
    
    # Add timezone if available
    if "TZ" in os.environ:
        safe_env["TZ"] = os.environ["TZ"]
    
    return safe_env


class SignalHandler:
    """Context manager for handling OS signals gracefully."""
    
    def __init__(self, signals=None):
        """Initialize with signals to handle."""
        self.signals = signals or [signal.SIGINT, signal.SIGTERM]
        self.original_handlers = {}
        self.received_signal = None
        self.should_exit = False
    
    def __enter__(self):
        """Setup signal handlers."""
        def handler(signum, frame):
            self.received_signal = signum
            self.should_exit = True
        
        for sig in self.signals:
            self.original_handlers[sig] = signal.signal(sig, handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original signal handlers."""
        for sig, original_handler in self.original_handlers.items():
            signal.signal(sig, original_handler)
    
    def check_signal(self) -> bool:
        """Check if signal was received."""
        return self.should_exit


def retry_async(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for async function retry logic."""
    def decorator(func):
        import asyncio
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    continue
            
            # All attempts failed
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator