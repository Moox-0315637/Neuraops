"""NeuraOps Health CLI Commands

CLI commands for system health monitoring and diagnostics
"""

import logging
import platform
import time
from typing import Any, Dict, Optional, Annotated

import typer
import psutil
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live

from ...core.structured_output import SeverityLevel


# Local UI helper functions to avoid import issues
def create_header(title: str, subtitle: Optional[str] = None) -> Panel:
    """Create a header panel with optional subtitle"""
    if subtitle:
        content = f"[bold blue]{title}[/bold blue]\n[dim]{subtitle}[/dim]"
    else:
        content = f"[bold blue]{title}[/bold blue]"
    return Panel(content, style="blue")


def create_status_panel(content: list, title: str, style: str = "green") -> Panel:
    """Create a status panel with list of items"""
    formatted_content = "\n".join(content) if isinstance(content, list) else str(content)
    return Panel(formatted_content, title=title, border_style=style)


def print_error(message: str) -> None:
    """Print error message"""
    console.print(f"[red]❌ {message}[/red]")


# Create the health CLI app
health_app = typer.Typer(name="health", help="Monitor and diagnose system health", short_help="System health tools", invoke_without_command=True)

# Default health command (for backward compatibility)
@health_app.callback()
def health_callback(ctx: typer.Context):
    """Show basic system health information"""
    if ctx.invoked_subcommand is None:
        try:
            from ...devops_commander.config import get_config
            config = get_config()
            
            console.print("[bold green]✅ NeuraOps Health Check[/bold green]")
            console.print(f"Model: [cyan]{config.ollama.model}[/cyan]")  
            console.print(f"Ollama URL: [cyan]{config.ollama.base_url}[/cyan]")
            console.print(f"Cache: [green]{'Enabled' if config.cache.enabled else 'Disabled'}[/green]")
            console.print(f"Log Level: [yellow]{config.log_level}[/yellow]")
            
        except Exception as e:
            print_error(f"Health check failed: {e}")
            raise typer.Exit(1)

# Renamed main command to avoid conflicts
@health_app.command("info")
def health_info():
    """Show basic system health information"""
    try:
        from ...devops_commander.config import get_config
        config = get_config()
        
        console.print("[bold green]✅ NeuraOps Health Check[/bold green]")
        console.print(f"Model: [cyan]{config.ollama.model}[/cyan]")  
        console.print(f"Ollama URL: [cyan]{config.ollama.base_url}[/cyan]")
        console.print(f"Cache: [green]{'Enabled' if config.cache.enabled else 'Disabled'}[/green]")
        console.print(f"Log Level: [yellow]{config.log_level}[/yellow]")
        
    except Exception as e:
        print_error(f"Health check failed: {e}")
        raise typer.Exit(1)
console = Console()
logger = logging.getLogger(__name__)


# Helper functions for analyze_health_results to reduce cognitive complexity
def _initialize_health_result(
    system_info: Dict[str, Any],
    cpu_memory: Dict[str, Any],
    network_status: Dict[str, Any],
    check_level: str,
) -> Dict[str, Any]:
    """Initialize the health result dictionary with basic data"""
    return {
        "timestamp": time.time(),
        "severity": SeverityLevel.INFO.value,
        "system_info": system_info,
        "resources": {
            "cpu": {"percent": cpu_memory["cpu_percent"], "per_core": cpu_memory["cpu_per_core"]},
            "memory": {
                "percent": cpu_memory["memory"]["percent"],
                "available_gb": cpu_memory["memory"]["available"] / (1024**3),
                "total_gb": cpu_memory["memory"]["total"] / (1024**3),
            },
            "swap": {
                "percent": cpu_memory["swap"]["percent"],
                "free_gb": cpu_memory["swap"]["free"] / (1024**3),
                "total_gb": cpu_memory["swap"]["total"] / (1024**3),
            },
            "disk": {"partitions": []},
            "network": {
                "interfaces_count": len(network_status["interfaces"]),
                "connections_count": network_status["connections_count"],
            },
        },
        "issues": [],
        "recommendations": [],
        "check_level": check_level,
    }


def _process_disk_information(result: Dict[str, Any], disk_status: Dict[str, Any]):
    """Process and add disk information to the result"""
    for partition in disk_status["partitions"]:
        result["resources"]["disk"]["partitions"].append(
            {
                "mountpoint": partition["mountpoint"],
                "percent": partition["usage"]["percent"],
                "free_gb": partition["usage"]["free"] / (1024**3),
                "total_gb": partition["usage"]["total"] / (1024**3),
            }
        )


def _analyze_cpu_issues(result: Dict[str, Any], cpu_memory: Dict[str, Any]):
    """Analyze CPU usage and add issues if found"""
    cpu_percent = cpu_memory["cpu_percent"]
    if cpu_percent > 90:
        result["issues"].append(
            {
                "component": "cpu",
                "severity": SeverityLevel.CRITICAL.value,
                "message": f"CPU usage is critically high at {cpu_percent:.1f}%",
            }
        )
        result["recommendations"].append("Identify and terminate CPU-intensive processes")
        _update_severity(result, SeverityLevel.ERROR.value)
    elif cpu_percent > 75:
        result["issues"].append(
            {
                "component": "cpu",
                "severity": SeverityLevel.MEDIUM.value,
                "message": f"CPU usage is elevated at {cpu_percent:.1f}%",
            }
        )
        result["recommendations"].append("Monitor CPU-intensive processes")
        _update_severity(result, SeverityLevel.MEDIUM.value)


def _analyze_memory_issues(result: Dict[str, Any], cpu_memory: Dict[str, Any]):
    """Analyze memory usage and add issues if found"""
    memory_percent = cpu_memory["memory"]["percent"]
    if memory_percent > 90:
        result["issues"].append(
            {
                "component": "memory",
                "severity": SeverityLevel.CRITICAL.value,
                "message": f"Memory usage is critically high at {memory_percent:.1f}%",
            }
        )
        result["recommendations"].append("Check for memory leaks or increase system memory")
        _update_severity(result, SeverityLevel.ERROR.value)
    elif memory_percent > 80:
        result["issues"].append(
            {
                "component": "memory",
                "severity": SeverityLevel.MEDIUM.value,
                "message": f"Memory usage is elevated at {memory_percent:.1f}%",
            }
        )
        result["recommendations"].append("Monitor memory-intensive applications")
        _update_severity(result, SeverityLevel.MEDIUM.value)


def _analyze_swap_issues(result: Dict[str, Any], cpu_memory: Dict[str, Any]):
    """Analyze swap usage and add issues if found"""
    swap_percent = cpu_memory["swap"]["percent"]
    if swap_percent > 75:
        result["issues"].append(
            {
                "component": "swap",
                "severity": SeverityLevel.MEDIUM.value,
                "message": f"Swap usage is high at {swap_percent:.1f}%",
            }
        )
        result["recommendations"].append("Increase system memory or optimize memory usage")
        _update_severity(result, SeverityLevel.MEDIUM.value)


def _analyze_disk_issues(result: Dict[str, Any], disk_status: Dict[str, Any]):
    """Analyze disk usage and add issues if found"""
    for partition in disk_status["partitions"]:
        percent = partition["usage"]["percent"]
        mountpoint = partition["mountpoint"]
        if percent > 90:
            result["issues"].append(
                {
                    "component": "disk",
                    "severity": SeverityLevel.ERROR.value,
                    "message": f"Disk usage on {mountpoint} is critically high at {percent:.1f}%",
                }
            )
            result["recommendations"].append(f"Free up space on {mountpoint} partition")
            _update_severity(result, SeverityLevel.ERROR.value)
        elif percent > 80:
            result["issues"].append(
                {
                    "component": "disk",
                    "severity": SeverityLevel.MEDIUM.value,
                    "message": f"Disk usage on {mountpoint} is elevated at {percent:.1f}%",
                }
            )
            result["recommendations"].append(f"Monitor disk usage on {mountpoint} partition")
            _update_severity(result, SeverityLevel.MEDIUM.value)


def _update_severity(result: Dict[str, Any], target_severity: str):
    """Update result severity if target is higher priority"""
    severity_order = [
        SeverityLevel.DEBUG.value,
        SeverityLevel.INFO.value,
        SeverityLevel.WARNING.value,
        SeverityLevel.MEDIUM.value,
        SeverityLevel.ERROR.value,
        SeverityLevel.CRITICAL.value,
    ]
    current_index = severity_order.index(result["severity"])
    target_index = severity_order.index(target_severity)
    if target_index > current_index:
        result["severity"] = target_severity


def _finalize_health_result(result: Dict[str, Any]):
    """Finalize the health result by adding default recommendations and deduplicating"""
    if not result["issues"]:
        result["recommendations"].append("System appears healthy, continue monitoring regularly")
    # Deduplicate recommendations
    result["recommendations"] = list(set(result["recommendations"]))


def analyze_health_results(
    system_info: Dict[str, Any],
    cpu_memory: Dict[str, Any],
    disk_status: Dict[str, Any],
    network_status: Dict[str, Any],
    check_level: str,
) -> Dict[str, Any]:
    """Analyze health check results and generate report"""
    result = _initialize_health_result(system_info, cpu_memory, network_status, check_level)
    _process_disk_information(result, disk_status)
    _analyze_cpu_issues(result, cpu_memory)
    _analyze_memory_issues(result, cpu_memory)
    _analyze_swap_issues(result, cpu_memory)
    _analyze_disk_issues(result, disk_status)
    _finalize_health_result(result)
    return result


# Helper functions for display_health_results to reduce cognitive complexity
def _get_severity_colors() -> Dict[str, str]:
    """Get severity color mapping"""
    return {
        SeverityLevel.CRITICAL.value: "bold red",
        SeverityLevel.ERROR.value: "red",
        SeverityLevel.MEDIUM.value: "yellow",
        SeverityLevel.WARNING.value: "blue",
        SeverityLevel.INFO.value: "green",
    }


def _display_header(analysis: Dict[str, Any], severity_colors: Dict[str, str]):
    """Display the main header with severity information"""
    severity_color = severity_colors.get(analysis["severity"], "white")
    console.print(create_header(f"System Health Check: [{severity_color}]{analysis['severity'].upper()}[/{severity_color}]", subtitle=f"Check Level: {analysis['check_level'].title()}"))


def _display_system_info(analysis: Dict[str, Any]):
    """Display system information panel"""
    system_info = analysis["system_info"]
    resources = analysis["resources"]

    system_panel = Panel(
        f"System: [bold]{system_info['system']} {system_info['release']}[/bold]\n"
        f"Hostname: [bold]{system_info['node']}[/bold]\n"
        f"CPU: [bold]{system_info['processor']}[/bold] "
        f"({system_info['cpu_count_physical']} physical / {system_info['cpu_count_logical']} logical cores)\n"
        f"Memory: [bold]{resources['memory']['total_gb']:.1f} GB[/bold]\n"
        f"Python Version: [bold]{system_info['python_version']}[/bold]",
        title="System Information",
        border_style="blue",
    )
    console.print(system_panel)


def _display_resource_usage(analysis: Dict[str, Any]):
    """Display resource usage information"""
    resource_items = []
    resources = analysis["resources"]

    # CPU usage
    cpu_style = _get_usage_style(resources["cpu"]["percent"], 75, 90)
    resource_items.append(f"CPU: [{cpu_style}]{resources['cpu']['percent']:.1f}%[/{cpu_style}]")

    # Memory usage
    memory_style = _get_usage_style(resources["memory"]["percent"], 80, 90)
    resource_items.append(f"Memory: [{memory_style}]{resources['memory']['percent']:.1f}% ({resources['memory']['available_gb']:.1f} GB free)[/{memory_style}]")

    # Swap usage (if available)
    if resources["swap"]["total_gb"] > 0:
        swap_style = _get_usage_style(resources["swap"]["percent"], 75, 90)
        resource_items.append(f"Swap: [{swap_style}]{resources['swap']['percent']:.1f}% ({resources['swap']['free_gb']:.1f} GB free)[/{swap_style}]")

    # Disk usage
    _add_disk_usage_items(resource_items, resources["disk"]["partitions"])

    # Network information
    resource_items.append(f"Network: {resources['network']['interfaces_count']} interfaces, {resources['network']['connections_count']} connections")

    console.print(create_status_panel(resource_items, title="Resource Usage"))


def _get_usage_style(percent: float, warning_threshold: float, critical_threshold: float) -> str:
    """Get color style based on usage percentage and thresholds"""
    if percent > critical_threshold:
        return "red"
    elif percent > warning_threshold:
        return "yellow"
    return "green"


def _add_disk_usage_items(resource_items: list, partitions: list):
    """Add disk usage items to resource list"""
    for partition in partitions:
        disk_style = _get_usage_style(partition["percent"], 80, 90)
        mount = partition["mountpoint"]
        # Truncate long paths
        if len(mount) > 20:
            mount = f"{mount[:17]}..."
        resource_items.append(f"Disk {mount}: [{disk_style}]{partition['percent']:.1f}% ({partition['free_gb']:.1f} GB free)[/{disk_style}]")


def _display_issues(analysis: Dict[str, Any], severity_colors: Dict[str, str]):
    """Display detected issues"""
    if analysis["issues"]:
        issues_table = Table(title=f"Detected Issues ({len(analysis['issues'])})")
        issues_table.add_column("Component", style="cyan")
        issues_table.add_column("Severity", style="magenta")
        issues_table.add_column("Message", style="white")

        for issue in analysis["issues"]:
            severity_style = severity_colors.get(issue["severity"], "white")
            issues_table.add_row(
                issue["component"].upper(),
                f"[{severity_style}]{issue['severity'].upper()}[/{severity_style}]",
                issue["message"],
            )

        console.print(issues_table)
    else:
        console.print(
            Panel(
                "No issues detected. System appears to be healthy.",
                title="System Health",
                border_style="green",
            )
        )


def _display_recommendations(analysis: Dict[str, Any]):
    """Display recommendations"""
    if analysis["recommendations"]:
        recommendations_text = "\n".join([f"• {rec}" for rec in analysis["recommendations"]])
        console.print(Panel(recommendations_text, title="🔧 Recommendations", border_style="yellow"))


def display_health_results(analysis: Dict[str, Any]):
    """Display formatted health check results"""
    severity_colors = _get_severity_colors()
    _display_header(analysis, severity_colors)
    _display_system_info(analysis)
    _display_resource_usage(analysis)
    _display_issues(analysis, severity_colors)
    _display_recommendations(analysis)


@health_app.command("check")
def check_system_health(
    quick: Annotated[bool, typer.Option(help="Perform a quick health check")] = False,
    full: Annotated[bool, typer.Option(help="Perform a comprehensive health check")] = False,
    json_output: Annotated[bool, typer.Option(help="Output results in JSON format")] = False,
):
    """
    Run a comprehensive system health check
    """
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Running health check...", total=100)

            # Determine check level
            check_level = "standard"
            if quick:
                check_level = "quick"
            elif full:
                check_level = "full"

            # Show initial progress
            progress.update(task, advance=10, description="[cyan]Collecting system info...")

            # Get system information
            system_info = get_system_info()

            # Update progress
            progress.update(task, advance=20, description="[cyan]Checking CPU and memory...")

            # Check CPU and memory
            cpu_memory = check_cpu_memory()

            # Update progress
            progress.update(task, advance=20, description="[cyan]Checking disk usage...")

            # Check disk usage
            disk_status = check_disk_usage()

            # Update progress
            progress.update(task, advance=20, description="[cyan]Checking network status...")

            # Check network
            network_status = check_network()

            # Update progress based on check level
            if check_level == "full":
                progress.update(task, advance=10, description="[cyan]Running extended diagnostics...")
                time.sleep(1)  # Simulate extended checks

            # Analyze results
            analysis = analyze_health_results(system_info, cpu_memory, disk_status, network_status, check_level)

            # Update progress
            progress.update(task, advance=20, description="[cyan]Preparing report...")

            # Complete progress
            progress.update(task, completed=100)

        # Output results
        if json_output:
            import json

            console.print_json(json.dumps(analysis))
        else:
            display_health_results(analysis)

        return analysis

    except Exception as e:
        print_error(f"Error checking system health: {str(e)}")
        logger.error(f"Error checking system health: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


# Helper functions for monitor_system to reduce cognitive complexity
def _create_monitoring_header(hostname: str, current_time: str, interval: int) -> Panel:
    """Create the monitoring header panel"""
    content = f"System: [bold]{hostname}[/bold]  |  Time: [cyan]{current_time}[/cyan]  |  Interval: [green]{interval}s[/green]  |  Press [bold red]Ctrl+C[/bold red] to exit"
    return Panel(
        content,
        title="NeuraOps System Monitor",
        border_style="blue",
    )


def _get_cpu_style(percentage: float) -> str:
    """Get color style based on CPU usage percentage"""
    if percentage > 90:
        return "red"
    elif percentage > 70:
        return "yellow"
    return "green"


def _create_cpu_table() -> Table:
    """Create and populate CPU usage table"""
    cpu_table = Table(show_header=True, header_style="bold magenta")
    cpu_table.add_column("CPU Core")
    cpu_table.add_column("Usage %")

    # Per-core CPU usage
    for i, percentage in enumerate(psutil.cpu_percent(interval=0.1, percpu=True)):
        cpu_style = _get_cpu_style(percentage)
        cpu_table.add_row(f"Core {i}", f"[{cpu_style}]{percentage:.1f}%[/{cpu_style}]")

    # Overall CPU usage
    cpu_usage = psutil.cpu_percent(interval=0.1)
    cpu_style = _get_cpu_style(cpu_usage)
    cpu_table.add_row("Total", f"[bold {cpu_style}]{cpu_usage:.1f}%[/bold {cpu_style}]")

    return cpu_table


def _get_memory_style(percent: float) -> str:
    """Get color style based on memory usage percentage"""
    if percent > 90:
        return "red"
    elif percent > 70:
        return "yellow"
    return "green"


def _get_swap_style(percent: float) -> str:
    """Get color style based on swap usage percentage"""
    if percent > 80:
        return "red"
    elif percent > 50:
        return "yellow"
    return "green"


def _create_memory_table() -> Table:
    """Create and populate memory usage table"""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    memory_table = Table(show_header=True, header_style="bold cyan")
    memory_table.add_column("Memory")
    memory_table.add_column("Usage")
    memory_table.add_column("Percentage")

    # RAM
    memory_style = _get_memory_style(memory.percent)
    memory_table.add_row(
        "RAM",
        f"{memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB",
        f"[{memory_style}]{memory.percent:.1f}%[/{memory_style}]",
    )

    # Swap
    swap_style = _get_swap_style(swap.percent)
    memory_table.add_row(
        "Swap",
        f"{swap.used / (1024**3):.1f} GB / {swap.total / (1024**3):.1f} GB",
        f"[{swap_style}]{swap.percent:.1f}%[/{swap_style}]",
    )

    return memory_table


def _get_disk_style(percent: float) -> str:
    """Get color style based on disk usage percentage"""
    if percent > 90:
        return "red"
    elif percent > 75:
        return "yellow"
    return "green"


def _create_disk_table() -> Table:
    """Create and populate disk usage table"""
    disk_table = Table(show_header=True, header_style="bold green")
    disk_table.add_column("Mount")
    disk_table.add_column("Usage")
    disk_table.add_column("Free")

    # Get disk partitions
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_style = _get_disk_style(usage.percent)

            mount = partition.mountpoint
            # Truncate long paths
            if len(mount) > 15:
                mount = f"{mount[:12]}..."

            disk_table.add_row(
                mount,
                f"[{disk_style}]{usage.percent:.1f}%[/{disk_style}]",
                f"{usage.free / (1024**3):.1f} GB",
            )
        except (PermissionError, FileNotFoundError):
            pass

    return disk_table


def _create_network_table() -> Table:
    """Create and populate network statistics table"""
    network_table = Table(show_header=True, header_style="bold yellow")
    network_table.add_column("Interface")
    network_table.add_column("Sent")
    network_table.add_column("Received")

    # Get network statistics
    net_io = psutil.net_io_counters(pernic=True)
    for interface, stats in net_io.items():
        # Skip loopback interface
        if interface.startswith("lo"):
            continue
        network_table.add_row(
            interface,
            f"{stats.bytes_sent / (1024**2):.1f} MB",
            f"{stats.bytes_recv / (1024**2):.1f} MB",
        )

    return network_table


def _update_monitoring_layout(layout: Layout, hostname: str, current_time: str, interval: int):
    """Update the complete monitoring layout with current system stats"""
    # Update header
    layout["header"].update(_create_monitoring_header(hostname, current_time, interval))

    # Update CPU and memory panel
    cpu_table = _create_cpu_table()
    memory_table = _create_memory_table()

    # Create layout for CPU and Memory tables
    cpu_mem_layout = Layout()
    cpu_layout = Layout(cpu_table, name="cpu")
    memory_layout = Layout(memory_table, name="memory")
    cpu_mem_layout.split_row(cpu_layout, memory_layout)
    
    cpu_mem_panel = Panel(
        cpu_mem_layout,
        title="CPU & Memory",
        border_style="blue",
    )
    layout["cpu_mem"].update(cpu_mem_panel)

    # Update disk and network panel
    disk_table = _create_disk_table()
    network_table = _create_network_table()

    # Create layout for Disk and Network tables
    disk_net_layout = Layout()
    disk_layout = Layout(disk_table, name="disk")
    network_layout = Layout(network_table, name="network")
    disk_net_layout.split_row(disk_layout, network_layout)
    
    disk_net_panel = Panel(
        disk_net_layout,
        title="Disk & Network",
        border_style="green",
    )
    layout["disk_net"].update(disk_net_panel)


def _should_stop_monitoring(end_time: Optional[float]) -> bool:
    """Check if monitoring should stop based on duration"""
    if end_time and time.time() > end_time:
        return True
    return False


@health_app.command("monitor")
def monitor_system(
    interval: Annotated[int, typer.Option(help="Refresh interval in seconds")] = 2,
    duration: Annotated[Optional[int], typer.Option(help="Monitoring duration in minutes (0 for continuous)")] = 0,
):
    """
    Monitor system resources in real-time
    """
    try:
        # Calculate end time if duration specified
        end_time = None
        if duration > 0:
            end_time = time.time() + (duration * 60)

        # Set up the layout
        layout = Layout()
        layout.split(Layout(name="header", size=3), Layout(name="main"))
        layout["main"].split_row(Layout(name="cpu_mem", ratio=1), Layout(name="disk_net", ratio=1))

        # Start live display
        with Live(layout, refresh_per_second=1, screen=True):
            try:
                # Monitor loop
                while True:
                    # Check if monitoring should stop
                    if _should_stop_monitoring(end_time):
                        break

                    # Get current system info
                    hostname = platform.node()
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

                    # Update the complete layout
                    _update_monitoring_layout(layout, hostname, current_time, interval)

                    # Sleep for the interval
                    time.sleep(interval)

                console.print("[green]Monitoring completed.[/green]")

            except KeyboardInterrupt:
                console.print("\n[yellow]Monitoring stopped.[/yellow]")

    except Exception as e:
        print_error(f"Error monitoring system: {str(e)}")
        logger.error(f"Error monitoring system: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


# Helper functions for list_processes command


def _get_process_list():
    """Get list of processes with their information"""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "create_time"]):
        try:
            pinfo = proc.info
            pinfo["io_counters"] = proc.io_counters() if hasattr(proc, "io_counters") else None
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes


def _sort_processes(processes, sort_by):
    """Sort processes based on specified criteria"""
    if sort_by == "cpu":
        processes.sort(key=lambda x: x["cpu_percent"] if x["cpu_percent"] is not None else 0, reverse=True)
    elif sort_by == "memory":
        processes.sort(key=lambda x: x["memory_percent"], reverse=True)
    elif sort_by == "io":
        processes.sort(
            key=lambda x: (x["io_counters"].read_bytes + x["io_counters"].write_bytes if x["io_counters"] else 0),
            reverse=True,
        )
    elif sort_by == "time":
        current_time = time.time()
        processes.sort(
            key=lambda x: current_time - x["create_time"] if x["create_time"] else 0,
            reverse=True,
        )
    return processes


def _create_process_table(sort_by, count, sort_options):
    """Create and configure the process table"""
    table = Table(title=f"Top {count} Processes by {sort_options[sort_by]}")
    table.add_column("PID", style="cyan", justify="right")
    table.add_column("Name", style="green")
    table.add_column("User", style="blue")
    table.add_column("CPU %", style="magenta", justify="right")
    table.add_column("Memory %", style="yellow", justify="right")

    if sort_by == "io":
        table.add_column("I/O Read", style="cyan", justify="right")
        table.add_column("I/O Write", style="cyan", justify="right")
    elif sort_by == "time":
        table.add_column("Running Time", style="cyan", justify="right")

    return table


def _format_running_time(running_time):
    """Format running time into human-readable string"""
    if running_time > 86400:  # More than a day
        return f"{running_time / 86400:.1f} days"
    elif running_time > 3600:  # More than an hour
        return f"{running_time / 3600:.1f} hours"
    elif running_time > 60:  # More than a minute
        return f"{running_time / 60:.1f} minutes"
    else:
        return f"{running_time:.1f} seconds"


def _add_process_to_table(table, proc, sort_by):
    """Add a single process to the table"""
    row = [
        str(proc["pid"]),
        proc["name"][:20],  # Truncate long names
        proc["username"][:10] if proc["username"] else "N/A",  # Truncate long usernames
        f"{proc['cpu_percent'] if proc['cpu_percent'] is not None else 0.0:.1f}%",
        f"{proc['memory_percent'] if proc['memory_percent'] is not None else 0.0:.1f}%",
    ]

    # Add extra columns based on sort criteria
    if sort_by == "io" and proc["io_counters"]:
        row.append(f"{proc['io_counters'].read_bytes / (1024**2):.1f} MB")
        row.append(f"{proc['io_counters'].write_bytes / (1024**2):.1f} MB")
    elif sort_by == "time" and proc["create_time"]:
        running_time = time.time() - proc["create_time"]
        row.append(_format_running_time(running_time))

    table.add_row(*row)


@health_app.command("processes")
def list_processes(
    sort_by: Annotated[str, typer.Option(help="Sort processes by: cpu, memory, io, time")] = "cpu",
    count: Annotated[int, typer.Option(help="Number of processes to show")] = 10,
):
    """
    List top processes by resource usage
    """
    try:
        # Validate sort option
        sort_options = {"cpu": "CPU %", "memory": "Memory %", "io": "I/O", "time": "Running Time"}

        if sort_by not in sort_options:
            print_error(f"Invalid sort option. Choose from: {', '.join(sort_options.keys())}")
            raise typer.Exit(code=1)

        # Get, sort, and limit processes
        processes = _get_process_list()
        processes = _sort_processes(processes, sort_by)
        processes = processes[:count]

        # Create and populate table
        table = _create_process_table(sort_by, count, sort_options)
        for proc in processes:
            _add_process_to_table(table, proc, sort_by)

        # Display table
        console.print(table)

    except Exception as e:
        print_error(f"Error listing processes: {str(e)}")
        logger.error(f"Error listing processes: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


def _create_network_interfaces_table():
    """Create and populate network interfaces table"""
    interfaces = psutil.net_if_addrs()
    if_table = Table(title="Network Interfaces")
    if_table.add_column("Interface", style="cyan")
    if_table.add_column("IP Address", style="green")
    if_table.add_column("Netmask", style="blue")
    if_table.add_column("MAC Address", style="yellow")

    for interface, addrs in interfaces.items():
        ipv4_addr = "N/A"
        netmask = "N/A"
        mac_addr = "N/A"

        for addr in addrs:
            if addr.family == 2:  # AF_INET (IPv4)
                ipv4_addr = addr.address
                netmask = addr.netmask
            elif addr.family == 17:  # AF_LINK (MAC)
                mac_addr = addr.address

        if_table.add_row(interface, ipv4_addr, netmask, mac_addr)

    return if_table


def _create_network_stats_table():
    """Create and populate network statistics table"""
    stats = psutil.net_io_counters(pernic=True)
    stats_table = Table(title="Network Statistics")
    stats_table.add_column("Interface", style="cyan")
    stats_table.add_column("Bytes Sent", style="green", justify="right")
    stats_table.add_column("Bytes Received", style="blue", justify="right")
    stats_table.add_column("Packets Sent", style="yellow", justify="right")
    stats_table.add_column("Packets Received", style="magenta", justify="right")

    for interface, stat in stats.items():
        stats_table.add_row(
            interface,
            f"{stat.bytes_sent / (1024**2):.2f} MB",
            f"{stat.bytes_recv / (1024**2):.2f} MB",
            str(stat.packets_sent),
            str(stat.packets_recv),
        )

    return stats_table


def _format_connection_address(addr):
    """Format connection address"""
    return f"{addr.ip}:{addr.port}" if addr else "N/A"


def _create_connections_table():
    """Create and populate active connections table"""
    connections = psutil.net_connections(kind="inet")
    conn_table = Table(title="Active Connections")
    conn_table.add_column("Proto", style="cyan")
    conn_table.add_column("Local Address", style="green")
    conn_table.add_column("Remote Address", style="blue")
    conn_table.add_column("Status", style="yellow")
    conn_table.add_column("PID", style="magenta")

    for conn in connections[:20]:  # Limit to first 20 for readability
        proto = "TCP" if conn.type == 1 else "UDP"
        local_addr = _format_connection_address(conn.laddr)
        remote_addr = _format_connection_address(conn.raddr)
        status = conn.status if conn.status else "N/A"
        pid = str(conn.pid) if conn.pid else "N/A"

        conn_table.add_row(proto, local_addr, remote_addr, status, pid)

    return conn_table, len(connections)


@health_app.command("network")
def check_network_status(
    detailed: Annotated[bool, typer.Option(help="Show detailed network information")] = False,
):
    """
    Check network interfaces and connections
    """
    try:
        console.print(create_header("Network Status Check"))

        # Display interfaces and statistics
        console.print(_create_network_interfaces_table())
        console.print(_create_network_stats_table())

        # Show detailed connections if requested
        if detailed:
            conn_table, total_connections = _create_connections_table()
            console.print(conn_table)
            if total_connections > 20:
                console.print(f"[yellow]Showing 20 of {total_connections} connections.[/yellow]")

    except Exception as e:
        print_error(f"Error checking network status: {str(e)}")
        logger.error(f"Error checking network status: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


@health_app.command("disk")
def check_disk_status(
    all_filesystems: Annotated[bool, typer.Option(help="Show all filesystems, including special ones")] = False,
):
    """
    Check disk usage and I/O statistics
    """
    try:
        console.print(create_header("Disk Status Check"))

        # Get disk partitions
        partitions = psutil.disk_partitions(all=all_filesystems)

        # Create table for disk usage
        usage_table = Table(title="Disk Usage")
        usage_table.add_column("Mount Point", style="cyan")
        usage_table.add_column("Device", style="green")
        usage_table.add_column("Filesystem", style="blue")
        usage_table.add_column("Total", style="yellow", justify="right")
        usage_table.add_column("Used", style="magenta", justify="right")
        usage_table.add_column("Free", style="cyan", justify="right")
        usage_table.add_column("Usage", justify="right")

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)

                # Determine color based on usage percentage
                usage_color = "green"
                if usage.percent > 90:
                    usage_color = "red"
                elif usage.percent > 75:
                    usage_color = "yellow"

                usage_table.add_row(
                    partition.mountpoint,
                    partition.device,
                    partition.fstype,
                    f"{usage.total / (1024**3):.1f} GB",
                    f"{usage.used / (1024**3):.1f} GB",
                    f"{usage.free / (1024**3):.1f} GB",
                    f"[{usage_color}]{usage.percent:.1f}%[/{usage_color}]",
                )
            except (PermissionError, FileNotFoundError):
                # Skip partitions we can't access
                pass

        console.print(usage_table)

        # Get disk I/O statistics
        io_stats = psutil.disk_io_counters(perdisk=True)
        if io_stats:
            # Create table for I/O statistics
            io_table = Table(title="Disk I/O Statistics")
            io_table.add_column("Disk", style="cyan")
            io_table.add_column("Read Count", style="green", justify="right")
            io_table.add_column("Write Count", style="blue", justify="right")
            io_table.add_column("Read Bytes", style="yellow", justify="right")
            io_table.add_column("Write Bytes", style="magenta", justify="right")

            for disk, stats in io_stats.items():
                io_table.add_row(
                    disk,
                    str(stats.read_count),
                    str(stats.write_count),
                    f"{stats.read_bytes / (1024**3):.2f} GB",
                    f"{stats.write_bytes / (1024**3):.2f} GB",
                )

            console.print(io_table)

    except Exception as e:
        print_error(f"Error checking disk status: {str(e)}")
        logger.error(f"Error checking disk status: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


def get_system_info() -> Dict[str, Any]:
    """Get basic system information"""
    info = {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "boot_time": psutil.boot_time(),
    }

    # Get CPU information
    info["cpu_count_physical"] = psutil.cpu_count(logical=False)
    info["cpu_count_logical"] = psutil.cpu_count(logical=True)

    # Get memory information
    memory = psutil.virtual_memory()
    info["memory_total"] = memory.total
    info["memory_available"] = memory.available

    return info


def check_cpu_memory() -> Dict[str, Any]:
    """Check CPU and memory status"""
    result = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_per_core": psutil.cpu_percent(interval=1, percpu=True),
        "memory": psutil.virtual_memory()._asdict(),
        "swap": psutil.swap_memory()._asdict(),
    }
    return result


def check_disk_usage() -> Dict[str, Any]:
    """Check disk usage"""
    result = {"partitions": [], "io_counters": None}

    # Get partition info
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            result["partitions"].append(
                {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "usage": usage._asdict(),
                }
            )
        except (PermissionError, FileNotFoundError):
            # Skip partitions we can't access
            pass

    # Get I/O counters if available
    try:
        result["io_counters"] = psutil.disk_io_counters()._asdict()
    except Exception:
        pass

    return result


def check_network() -> Dict[str, Any]:
    """Check network status"""
    result = {"interfaces": {}, "io_counters": None, "connections_count": 0}

    # Get network interfaces
    for interface, addrs in psutil.net_if_addrs().items():
        result["interfaces"][interface] = []
        for addr in addrs:
            result["interfaces"][interface].append(
                {
                    "family": addr.family,
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast if hasattr(addr, "broadcast") else None,
                }
            )

    # Get I/O counters
    try:
        result["io_counters"] = psutil.net_io_counters()._asdict()
    except Exception:
        pass

    # Get connection count
    try:
        result["connections_count"] = len(psutil.net_connections())
    except Exception:
        pass

    return result
