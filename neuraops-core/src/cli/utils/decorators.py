"""
CLI Decorators for NeuraOps

Provides decorators for error handling and common CLI patterns.
"""

import asyncio
import functools
import sys
import traceback
from typing import Any, Callable, TypeVar

from rich.console import Console

# Create console instance for error display
console = Console(stderr=True)

F = TypeVar("F", bound=Callable[..., Any])


def _handle_keyboard_interrupt() -> int:
    """Handle Ctrl+C gracefully"""
    console.print("\n[yellow]Operation cancelled by user[/yellow]")
    return 130


def _handle_file_errors(e: Exception) -> int:
    """Handle file-related errors"""
    if isinstance(e, FileNotFoundError):
        console.print(f"[red]✗ File not found:[/red] {str(e)}")
        return 2
    elif isinstance(e, PermissionError):
        console.print(f"[red]✗ Permission denied:[/red] {str(e)}")
        return 13
    return 1


def _handle_input_errors(e: ValueError) -> int:
    """Handle input validation errors"""
    console.print(f"[red]✗ Invalid input:[/red] {str(e)}")
    return 22


def _handle_network_errors(e: Exception) -> int:
    """Handle network-related errors"""
    if isinstance(e, ConnectionError):
        console.print(f"[red]✗ Connection error:[/red] {str(e)}")
        return 111
    elif isinstance(e, TimeoutError):
        console.print(f"[red]✗ Operation timed out:[/red] {str(e)}")
        return 124
    return 1


def _is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    import os

    return os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")


def _handle_generic_exception(e: Exception) -> int:
    """Handle unexpected exceptions with debug support"""
    console.print(f"[red]✗ Unexpected error:[/red] {str(e)}")

    if _is_debug_mode():
        console.print("\n[dim]Full traceback:[/dim]")
        console.print(traceback.format_exc())

    return 1


def _normalize_exit_code(result: Any) -> int:
    """Normalize function result to integer exit code"""
    if isinstance(result, int):
        return result
    elif result is None:
        return 0  # Success by default
    else:
        return 0 if result else 1


# Exception handlers mapping
EXCEPTION_HANDLERS = {
    KeyboardInterrupt: _handle_keyboard_interrupt,
    FileNotFoundError: _handle_file_errors,
    PermissionError: _handle_file_errors,
    ValueError: _handle_input_errors,
    ConnectionError: _handle_network_errors,
    TimeoutError: _handle_network_errors,
}


def _handle_exception_by_type(e: Exception) -> int:
    """Route exception to appropriate handler"""
    for exc_type, handler in EXCEPTION_HANDLERS.items():
        if isinstance(e, exc_type):
            if exc_type == KeyboardInterrupt:
                return handler()
            else:
                return handler(e)

    return _handle_generic_exception(e)


def handle_exceptions(func: F) -> F:
    """
    Decorator to handle exceptions in CLI commands with reduced complexity.

    Provides consistent error handling with Rich formatting.
    Returns appropriate exit codes for CLI commands.

    Args:
        func: The function to wrap

    Returns:
        Wrapped function with exception handling
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> int:
        try:
            result = func(*args, **kwargs)
            return _normalize_exit_code(result)

        except Exception as e:
            return _handle_exception_by_type(e)

    return wrapper

def handle_errors(func: F) -> F:
    """
    Alias for handle_exceptions to maintain compatibility
    
    CLAUDE.md: < 10 lines - Simple alias decorator
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with exception handling
    """
    return handle_exceptions(func)


def async_command(func: F) -> F:
    """
    Decorator to handle async commands in Typer CLI
    
    CLAUDE.md: < 15 lines - Convert async function to sync for Typer
    Converts async functions to synchronous ones for Typer compatibility
    
    Args:
        func: The async function to wrap
        
    Returns:
        Wrapped synchronous function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(func(*args, **kwargs))
    
    return wrapper
