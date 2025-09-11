"""
NeuraOps System CLI Commands
CLI commands for system information and management
"""

import logging
import platform
import time
import json
import os
from typing import Optional, Annotated

import typer
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...cli.ui.components import create_header, print_error

# Create the system CLI app
system_app = typer.Typer(name="system", help="System information and management commands", short_help="System tools")

console = Console()
logger = logging.getLogger(__name__)


def _collect_platform_info():
    """Collect platform information"""
    return {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def _collect_cpu_info():
    """Collect CPU information including frequency"""
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "current_frequency": None,
        "max_frequency": None,
        "min_frequency": None,
    }

    # Get CPU frequency if available
    try:
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            cpu_info["current_frequency"] = f"{cpu_freq.current:.1f} MHz"
            cpu_info["max_frequency"] = f"{cpu_freq.max:.1f} MHz"
            cpu_info["min_frequency"] = f"{cpu_freq.min:.1f} MHz"
    except Exception:
        pass

    return cpu_info


def _collect_memory_info():
    """Collect memory information"""
    memory = psutil.virtual_memory()
    return {
        "total_gb": memory.total / (1024**3),
        "available_gb": memory.available / (1024**3),
        "used_gb": memory.used / (1024**3),
        "percent": memory.percent,
    }


def _collect_system_status():
    """Collect boot time and users"""
    return {
        "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time())),
        "users": [user.name for user in psutil.users()],
    }


def _display_platform_panel(platform_info):
    """Display platform information panel"""
    platform_panel = Panel(
        f"System: [bold]{platform_info['system']}[/bold]\n"
        f"Hostname: [bold]{platform_info['node']}[/bold]\n"
        f"Release: [bold]{platform_info['release']}[/bold]\n"
        f"Architecture: [bold]{platform_info['machine']}[/bold]\n"
        f"Processor: [bold]{platform_info['processor']}[/bold]\n"
        f"Python Version: [bold]{platform_info['python_version']}[/bold]",
        title="Platform Details",
        border_style="blue",
    )
    console.print(platform_panel)


def _display_cpu_panel(cpu_info):
    """Display CPU information panel"""
    cpu_panel = Panel(
        f"Physical Cores: [bold]{cpu_info['physical_cores']}[/bold]\n"
        f"Logical Cores: [bold]{cpu_info['logical_cores']}[/bold]\n"
        f"Current Frequency: [bold]{cpu_info['current_frequency'] or 'N/A'}[/bold]\n"
        f"Max Frequency: [bold]{cpu_info['max_frequency'] or 'N/A'}[/bold]\n"
        f"Min Frequency: [bold]{cpu_info['min_frequency'] or 'N/A'}[/bold]",
        title="CPU Information",
        border_style="green",
    )
    console.print(cpu_panel)


def _display_memory_panel(memory_info):
    """Display memory information panel with color coding"""
    memory_style = "green"
    if memory_info["percent"] > 80:
        memory_style = "yellow"
    elif memory_info["percent"] > 90:
        memory_style = "red"

    memory_panel = Panel(
        f"Total: [bold]{memory_info['total_gb']:.1f} GB[/bold]\n"
        f"Available: [bold green]{memory_info['available_gb']:.1f} GB[/bold green]\n"
        f"Used: [{memory_style}]{memory_info['used_gb']:.1f} GB[/{memory_style}]\n"
        f"Usage: [{memory_style}]{memory_info['percent']:.1f}%[/{memory_style}]",
        title="Memory Information",
        border_style="cyan",
    )
    console.print(memory_panel)


def _display_system_status_panel(system_status):
    """Display system status panel with boot time and users"""
    boot_and_users_text = f"Boot Time: [bold]{system_status['boot_time']}[/bold]\nLogged-in Users: [bold]{', '.join(system_status['users']) if system_status['users'] else 'None'}[/bold]"
    misc_panel = Panel(
        boot_and_users_text,
        title="System Status",
        border_style="yellow",
    )
    console.print(misc_panel)


def _collect_disk_info():
    """Collect disk information for detailed view"""
    disk_table = Table(title="Storage Information")
    disk_table.add_column("Mount Point", style="cyan")
    disk_table.add_column("Device", style="green")
    disk_table.add_column("Filesystem", style="blue")
    disk_table.add_column("Size", style="yellow", justify="right")
    disk_table.add_column("Usage", justify="right")

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            usage_color = "green"
            if usage.percent > 90:
                usage_color = "red"
            elif usage.percent > 75:
                usage_color = "yellow"

            disk_table.add_row(
                partition.mountpoint,
                partition.device,
                partition.fstype,
                f"{usage.total / (1024**3):.1f} GB",
                f"[{usage_color}]{usage.percent:.1f}%[/{usage_color}]",
            )
        except (PermissionError, FileNotFoundError):
            pass

    return disk_table


def _collect_network_info():
    """Collect network interfaces information for detailed view"""
    net_table = Table(title="Network Interfaces")
    net_table.add_column("Interface", style="cyan")
    net_table.add_column("IP Address", style="green")
    net_table.add_column("Status", style="yellow")

    interfaces = psutil.net_if_addrs()
    interface_stats = psutil.net_if_stats()

    for interface, addrs in interfaces.items():
        ipv4_addr = "N/A"
        for addr in addrs:
            if addr.family == 2:  # AF_INET (IPv4)
                ipv4_addr = addr.address
                break

        status = "UP" if interface_stats.get(interface, {}).get("isup", False) else "DOWN"
        status_color = "green" if status == "UP" else "red"
        net_table.add_row(interface, ipv4_addr, f"[{status_color}]{status}[/{status_color}]")

    return net_table


def _display_detailed_info():
    """Display detailed information (disk and network)"""
    disk_table = _collect_disk_info()
    console.print(disk_table)

    net_table = _collect_network_info()
    console.print(net_table)


@system_app.command("info")
def system_info(
    detailed: Annotated[bool, typer.Option(help="Show detailed system information")] = False,
    json_output: Annotated[bool, typer.Option(help="Output results in JSON format")] = False,
):
    """
    Display comprehensive system information
    """
    try:
        # Collect system information using helper functions
        info = {
            "platform": _collect_platform_info(),
            "cpu": _collect_cpu_info(),
            "memory": _collect_memory_info(),
            **_collect_system_status(),
        }

        # Output results
        if json_output:
            console.print_json(json.dumps(info))
        else:
            # Display formatted system information
            console.print(create_header("System Information"))
            _display_platform_panel(info["platform"])
            _display_cpu_panel(info["cpu"])
            _display_memory_panel(info["memory"])
            _display_system_status_panel(info)

            if detailed:
                _display_detailed_info()

        return info

    except Exception as e:
        print_error(f"Error getting system information: {str(e)}")
        logger.error(f"Error getting system information: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


def _filter_sensitive_env_vars(env_vars, sensitive):
    """Filter out sensitive environment variables"""
    if sensitive:
        return env_vars

    sensitive_patterns = ["password", "secret", "key", "token", "credential"]
    filtered_vars = {}

    for key, value in env_vars.items():
        if not any(sensitive_word in key.lower() for sensitive_word in sensitive_patterns):
            filtered_vars[key] = value
        else:
            filtered_vars[key] = "[REDACTED]"

    return filtered_vars


def _apply_pattern_filter(env_vars, pattern):
    """Apply pattern filter to environment variables"""
    if not pattern:
        return env_vars

    filtered_vars = {}
    for key, value in env_vars.items():
        if pattern.lower() in key.lower():
            filtered_vars[key] = value

    return filtered_vars


def _format_env_value(value):
    """Format environment variable value with truncation"""
    if len(value) > 80:
        return value[:77] + "..."
    return value


def _create_env_table(env_vars):
    """Create formatted table for environment variables"""
    table = Table(title=f"Environment Variables ({len(env_vars)} found)")
    table.add_column("Variable", style="cyan")
    table.add_column("Value", style="white")

    # Sort variables alphabetically and add to table
    for key in sorted(env_vars.keys()):
        value = _format_env_value(env_vars[key])
        table.add_row(key, value)

    return table


@system_app.command("env")
def show_environment(
    pattern: Annotated[Optional[str], typer.Option(help="Filter environment variables by name pattern")] = None,
    sensitive: Annotated[bool, typer.Option(help="Include potentially sensitive variables")] = False,
):
    """
    Display environment variables
    """
    try:
        # Get and filter environment variables
        env_vars = dict(os.environ)
        env_vars = _filter_sensitive_env_vars(env_vars, sensitive)
        env_vars = _apply_pattern_filter(env_vars, pattern)

        # Create and display table
        table = _create_env_table(env_vars)
        console.print(table)

        return env_vars

    except Exception as e:
        print_error(f"Error displaying environment: {str(e)}")
        logger.error(f"Error displaying environment: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)
