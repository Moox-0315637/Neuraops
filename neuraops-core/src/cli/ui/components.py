"""
NeuraOps CLI UI Components
Rich-powered UI components for professional CLI interface
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.tree import Tree

# Rich style constants
STYLE_BOLD_BLUE = "bold blue"
STYLE_BOLD_RED = "bold red"


def _get_performance_time_style(inference_time: float) -> str:
    """Determine style based on inference time"""
    if inference_time < 2.0:
        return "green"
    elif inference_time < 5.0:
        return "yellow"
    else:
        return "red"


def _get_performance_status_style(status: str) -> str:
    """Determine style based on performance status"""
    if status == "good":
        return "green"
    elif status == "slow":
        return "yellow"
    else:
        return "red"


def _get_compliance_style(score: int) -> str:
    """Determine style based on compliance score"""
    if score >= 90:
        return "green"
    elif score >= 70:
        return "yellow"
    else:
        return "red"


def _setup_metrics_table() -> Table:
    """Setup the metrics table with columns"""
    table = Table(title="⚡ Performance Metrics", show_header=True, header_style=STYLE_BOLD_BLUE)

    # Add columns
    table.add_column("Iteration", style="cyan", no_wrap=True)
    table.add_column("Inference Time (s)", style="green", justify="right")
    table.add_column("Status", style="yellow")
    table.add_column("Model", style="blue")
    table.add_column("Cache", style="magenta")
    table.add_column("Timestamp", style="dim")

    return table


def _format_timestamp_display(timestamp: str) -> str:
    """Format timestamp for display in table"""
    if not timestamp:
        return ""

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return timestamp[:8]


def _add_metrics_row(table: Table, i: int, metrics: Dict[str, Any]) -> None:
    """Add a single metrics row to the table with styling"""
    inference_time = metrics.get("inference_time_seconds", 0.0)
    status = metrics.get("performance_status", "unknown")
    model = metrics.get("model", "unknown")
    cache_enabled = "✅" if metrics.get("cache_enabled", False) else "❌"
    timestamp = _format_timestamp_display(metrics.get("timestamp", ""))

    # Get styles using helper functions
    time_style = _get_performance_time_style(inference_time)
    status_style = _get_performance_status_style(status)

    table.add_row(
        str(i),
        f"[{time_style}]{inference_time:.3f}[/{time_style}]",
        f"[{status_style}]{status}[/{status_style}]",
        model,
        cache_enabled,
        timestamp,
    )


def create_header(title: str, subtitle: Optional[str] = None) -> Panel:
    """Create and display the NeuraOps application header"""

    header_text = Text()
    header_text.append("🤖 ", style=STYLE_BOLD_BLUE)
    header_text.append("NeuraOps", style="bold white")
    header_text.append(" - ", style="dim white")
    header_text.append(title, style="bold cyan")

    if subtitle:
        header_text.append(f"\n{subtitle}", style="dim white")

    header_panel = Panel(Align.center(header_text), style="blue", padding=(0, 1))

    return header_panel


def create_status_panel(health_status: Dict[str, Any], verbose: bool = False) -> Panel:
    """Create a status panel showing system health"""

    # Overall status with emoji
    overall_status = health_status.get("overall", "unknown")
    status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌", "unknown": "❓"}.get(overall_status, "❓")

    # Create status content
    status_content = []

    # Main status line
    status_line = Text()
    status_line.append(f"{status_emoji} Overall Status: ", style="bold")
    status_line.append(overall_status.upper(), style=_get_status_style(overall_status))
    status_content.append(status_line)

    # Ollama status
    ollama_status = health_status.get("ollama", {})
    ollama_emoji = "✅" if ollama_status.get("status") == "healthy" else "❌"
    ollama_line = Text()
    ollama_line.append(f"{ollama_emoji} Ollama: ", style="bold")
    ollama_line.append(ollama_status.get("status", "unknown"), style=_get_status_style(ollama_status.get("status")))
    ollama_line.append(f" ({ollama_status.get('model', 'unknown')})", style="dim")
    status_content.append(ollama_line)

    # Engine status
    engine_status = health_status.get("engine", "unknown")
    engine_emoji = "✅" if engine_status == "healthy" else "❌"
    engine_line = Text()
    engine_line.append(f"{engine_emoji} Engine: ", style="bold")
    engine_line.append(engine_status, style=_get_status_style(engine_status))
    status_content.append(engine_line)

    # Memory status
    memory_info = health_status.get("memory", {})
    if isinstance(memory_info, dict):
        memory_emoji = "✅" if memory_info.get("status") == "healthy" else "⚠️"
        memory_line = Text()
        memory_line.append(f"{memory_emoji} Memory: ", style="bold")
        memory_line.append(
            f"{memory_info.get('used_percent', 0):.1f}% used",
            style=_get_status_style(memory_info.get("status")),
        )
        memory_line.append(f" ({memory_info.get('available_gb', 0):.1f}GB available)", style="dim")
        status_content.append(memory_line)

    # Verbose information
    if verbose:
        status_content.append(Text())  # Blank line
        status_content.append(Text("📊 Detailed Information:", style="bold yellow"))

        # Timestamp
        timestamp = health_status.get("timestamp", datetime.now(timezone.utc).isoformat())
        status_content.append(Text(f"⏰ Checked at: {timestamp}", style="dim"))

        # Ollama URL
        if ollama_status.get("url"):
            status_content.append(Text(f"🔗 Ollama URL: {ollama_status['url']}", style="dim"))

        # Error information
        if ollama_status.get("error"):
            error_text = Text()
            error_text.append("❌ Ollama Error: ", style=STYLE_BOLD_RED)
            error_text.append(str(ollama_status["error"]), style="red")
            status_content.append(error_text)

    # Combine content
    panel_content = "\n".join(str(line) for line in status_content)

    # Panel style based on overall status
    panel_style = {
        "healthy": "green",
        "degraded": "yellow",
        "unhealthy": "red",
        "unknown": "blue",
    }.get(overall_status, "blue")

    return Panel(
        panel_content,
        title="🏥 System Health",
        title_align="left",
        style=panel_style,
        padding=(1, 2),
    )


def create_metrics_table(metrics_list: List[Dict[str, Any]]) -> Table:
    """Create a table showing performance metrics"""

    table = _setup_metrics_table()

    # Add rows using helper function
    for i, metrics in enumerate(metrics_list, 1):
        _add_metrics_row(table, i, metrics)

    return table


def create_log_analysis_table(analysis: Dict[str, Any]) -> Table:
    """Create a table showing log analysis results"""

    table = Table(title="📊 Log Analysis Results", show_header=True, header_style=STYLE_BOLD_BLUE)

    # Add columns
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Count/Value", style="green", justify="right")
    table.add_column("Details", style="white")

    # Add basic metrics
    severity = analysis.get("severity", "unknown")
    severity_style = _get_severity_style(severity)
    table.add_row(
        "Severity",
        f"[{severity_style}]{severity.upper()}[/{severity_style}]",
        "Overall severity level",
    )

    error_count = analysis.get("error_count", 0)
    error_style = "red" if error_count > 0 else "green"
    table.add_row("Errors", f"[{error_style}]{error_count}[/{error_style}]", "Total errors detected")

    warning_count = analysis.get("warning_count", 0)
    warning_style = "yellow" if warning_count > 0 else "green"
    table.add_row("Warnings", f"[{warning_style}]{warning_count}[/{warning_style}]", "Total warnings detected")

    # Add affected services
    affected_services = analysis.get("affected_services", [])
    if affected_services:
        services_text = ", ".join(affected_services[:3])
        if len(affected_services) > 3:
            services_text += f" (+{len(affected_services) - 3} more)"
        table.add_row("Affected Services", str(len(affected_services)), services_text)

    # Add security issues
    security_issues = analysis.get("security_issues", [])
    if security_issues:
        security_style = "red" if security_issues else "green"
        table.add_row(
            "Security Issues",
            f"[{security_style}]{len(security_issues)}[/{security_style}]",
            "Security concerns found",
        )

    return table


def create_infrastructure_table(infrastructure_config: str, provider: str) -> Panel:
    """Create a panel showing generated infrastructure configuration"""

    # Truncate config for display if too long
    display_config = infrastructure_config
    if len(display_config) > 1000:
        display_config = display_config[:1000] + "\n... (truncated)"

    return Panel(
        display_config,
        title=f"🏗️ Generated {provider.upper()} Infrastructure",
        title_align="left",
        style="cyan",
        padding=(1, 2),
    )


def create_incident_response_panel(response_plan: Dict[str, Any]) -> Panel:
    """Create a panel showing incident response plan"""

    content = []

    # Incident info
    severity = response_plan.get("severity", "unknown")
    severity_style = _get_severity_style(severity)
    content.append(f"[bold]Incident:[/bold] {response_plan.get('title', 'Unknown')}")
    content.append(f"[bold]Severity:[/bold] [{severity_style}]{severity.upper()}[/{severity_style}]")
    content.append(f"[bold]Estimated Resolution:[/bold] {response_plan.get('estimated_resolution_time', 'Unknown')}")
    content.append("")

    # Immediate actions
    immediate_actions = response_plan.get("immediate_actions", [])
    if immediate_actions:
        content.append("[bold yellow]🚨 Immediate Actions:[/bold yellow]")
        for i, action in enumerate(immediate_actions[:3], 1):
            if isinstance(action, dict):
                description = action.get("description", "Unknown action")
            else:
                description = str(action)
            content.append(f"{i}. {description}")

        if len(immediate_actions) > 3:
            content.append(f"   ... and {len(immediate_actions) - 3} more actions")

    panel_content = "\n".join(content)

    return Panel(
        panel_content,
        title="🚨 Incident Response Plan",
        title_align="left",
        style="red",
        padding=(1, 2),
    )


def create_security_scan_table(scan_result: Dict[str, Any]) -> Table:
    """Create a table showing security scan results"""

    table = Table(title="🔒 Security Scan Results", show_header=True, header_style=STYLE_BOLD_BLUE)

    # Add columns
    table.add_column("Severity", style="cyan", no_wrap=True)
    table.add_column("Count", style="green", justify="right")
    table.add_column("Issues", style="white")

    # Add vulnerability counts
    critical = scan_result.get("critical_vulnerabilities", [])
    if critical:
        table.add_row(
            "Critical",
            f"[red]{len(critical)}[/red]",
            ", ".join(critical[:2]) + ("..." if len(critical) > 2 else ""),
        )

    high = scan_result.get("high_vulnerabilities", [])
    if high:
        table.add_row(
            "High",
            f"[yellow]{len(high)}[/yellow]",
            ", ".join(high[:2]) + ("..." if len(high) > 2 else ""),
        )

    medium = scan_result.get("medium_vulnerabilities", [])
    if medium:
        table.add_row(
            "Medium",
            f"[blue]{len(medium)}[/blue]",
            ", ".join(medium[:2]) + ("..." if len(medium) > 2 else ""),
        )

    low = scan_result.get("low_vulnerabilities", [])
    if low:
        table.add_row(
            "Low",
            f"[green]{len(low)}[/green]",
            ", ".join(low[:2]) + ("..." if len(low) > 2 else ""),
        )

    # Add compliance score
    compliance_score = scan_result.get("compliance_score", 0)
    compliance_style = _get_compliance_style(compliance_score)
    table.add_row(
        "Compliance",
        f"[{compliance_style}]{compliance_score}%[/{compliance_style}]",
        "Overall compliance score",
    )

    return table


def create_progress_tracker(tasks: List[str], current_task: int = 0) -> Progress:
    """Create a multi-step progress tracker"""

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        expand=True,
    )

    # Add main progress task
    task_id = progress.add_task("Overall Progress", total=len(tasks))

    # Update to current position
    if current_task > 0:
        progress.update(task_id, completed=current_task)

    return progress


def create_command_execution_panel(result: Dict[str, Any]) -> Panel:
    """Create a panel showing command execution results"""

    content = []

    # Command info
    command = result.get("command", "Unknown")
    success = result.get("success", False)
    exit_code = result.get("exit_code", -1)
    execution_time = result.get("execution_time", 0.0)

    # Status line
    status_emoji = "✅" if success else "❌"
    status_text = "SUCCESS" if success else "FAILED"
    status_style = "green" if success else "red"

    content.append(f"[bold]Command:[/bold] [code]{command}[/code]")
    content.append(f"[bold]Status:[/bold] {status_emoji} [{status_style}]{status_text}[/{status_style}] (exit code: {exit_code})")
    content.append(f"[bold]Execution Time:[/bold] {execution_time:.3f}s")

    # Output
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    if stdout:
        content.append("")
        content.append("[bold green]📤 Output:[/bold green]")
        # Truncate long output
        display_stdout = stdout[:500] + "..." if len(stdout) > 500 else stdout
        content.append(f"[dim]{display_stdout}[/dim]")

    if stderr:
        content.append("")
        content.append("[bold red]📥 Errors:[/bold red]")
        # Truncate long errors
        display_stderr = stderr[:500] + "..." if len(stderr) > 500 else stderr
        content.append(f"[red]{display_stderr}[/red]")

    panel_content = "\n".join(content)
    panel_style = "green" if success else "red"

    return Panel(
        panel_content,
        title="⚡ Command Execution",
        title_align="left",
        style=panel_style,
        padding=(1, 2),
    )


def create_recommendations_list(recommendations: List[str], title: str = "💡 Recommendations") -> Panel:
    """Create a panel with a list of recommendations"""

    if not recommendations:
        return Panel("[dim]No recommendations available[/dim]", title=title, style="yellow")

    content = []
    for i, rec in enumerate(recommendations, 1):
        content.append(f"{i}. {rec}")

    panel_content = "\n".join(content)

    return Panel(panel_content, title=title, title_align="left", style="yellow", padding=(1, 2))


def _add_tree_node_dict(parent_node, key: str, value: dict) -> None:
    """Add a dictionary node to the tree"""
    branch = parent_node.add(f"[bold]{key}[/bold]")
    _add_dict_to_tree(branch, value)


def _add_tree_node_list(parent_node, key: str, value: list) -> None:
    """Add a list node to the tree with truncation"""
    if not value:  # Skip empty lists
        return

    branch = parent_node.add(f"[bold]{key}[/bold] [dim]({len(value)} items)[/dim]")
    for i, item in enumerate(value[:3]):  # Show first 3 items
        branch.add(str(item))
    if len(value) > 3:
        branch.add(f"[dim]... and {len(value) - 3} more[/dim]")


def _add_tree_node_simple(parent_node, key: str, value: Any) -> None:
    """Add a simple value node to the tree"""
    parent_node.add(f"[bold]{key}[/bold]: {value}")


def _add_dict_to_tree(parent_node, data_dict: dict) -> None:
    """Add dictionary items to tree node recursively"""
    for key, value in data_dict.items():
        if isinstance(value, dict):
            _add_tree_node_dict(parent_node, key, value)
        elif isinstance(value, list):
            _add_tree_node_list(parent_node, key, value)
        else:
            _add_tree_node_simple(parent_node, key, value)


def create_tree_view(data: Dict[str, Any], title: str = "📋 Data Structure") -> Tree:
    """Create a tree view for hierarchical data"""

    tree = Tree(title, style="blue")
    _add_dict_to_tree(tree, data)
    return tree


def create_summary_columns(data: List[Dict[str, Any]], title: str = "📈 Summary") -> Panel:
    """Create a multi-column summary panel"""

    if not data:
        return Panel("[dim]No data available[/dim]", title=title)

    # Create columns for different metrics
    columns_content = []

    # Group data by categories
    categories = {}
    for item in data:
        category = item.get("category", "General")
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    # Create column for each category
    for category, items in categories.items():
        column_text = Text(f"{category}\n", style=STYLE_BOLD_BLUE)
        for item in items[:5]:  # Show first 5 items
            name = item.get("name", "Unknown")
            value = item.get("value", "")
            column_text.append(f"{name}: {value}\n", style="white")

        columns_content.append(Panel(column_text, expand=False, padding=(0, 1)))

    if columns_content:
        columns = Columns(columns_content, equal=True, expand=True)
        return Panel(columns, title=title, style="blue")
    else:
        return Panel("[dim]No summary data available[/dim]", title=title)


def _get_status_style(status: str) -> str:
    """Get Rich style for status text"""
    status_styles = {
        "healthy": "green",
        "degraded": "yellow",
        "unhealthy": "red",
        "warning": "yellow",
        "error": "red",
        "unknown": "blue",
        "good": "green",
        "slow": "yellow",
    }
    return status_styles.get(status, "white")


def _get_severity_style(severity: str) -> str:
    """Get Rich style for severity levels"""
    severity_styles = {
        "critical": STYLE_BOLD_RED,
        "high": "red",
        "medium": "yellow",
        "low": "blue",
        "info": "green",
        "sev1": STYLE_BOLD_RED,
        "sev2": "red",
        "sev3": "yellow",
        "sev4": "blue",
    }
    return severity_styles.get(severity.lower(), "white")


def display_error(console: Console, error_message: str, details: Optional[str] = None) -> None:
    """Display a formatted error message"""

    content = [f"[red]❌ {error_message}[/red]"]

    if details:
        content.append("")
        content.append("[bold]Details:[/bold]")
        content.append(f"[dim]{details}[/dim]")

    error_panel = Panel("\n".join(content), title="🚨 Error", title_align="left", style="red", padding=(1, 2))

    console.print(error_panel)


def display_success(console: Console, message: str, details: Optional[str] = None) -> None:
    """Display a formatted success message"""

    content = [f"[green]✅ {message}[/green]"]

    if details:
        content.append("")
        content.append(f"[dim]{details}[/dim]")

    success_panel = Panel("\n".join(content), title="✅ Success", title_align="left", style="green", padding=(1, 2))

    console.print(success_panel)

def create_info_panel(message: str, details: Optional[str] = None, title: str = "ℹ️ Info") -> Panel:
    """Create an info panel with message and optional details
    
    CLAUDE.md: < 15 lines - Simple panel creation for info messages
    
    Args:
        message: Main info message
        details: Optional details text
        title: Panel title
        
    Returns:
        Rich Panel with info styling
    """
    content = [f"[blue]ℹ️ {message}[/blue]"]
    
    if details:
        content.append("")
        content.append(f"[dim]{details}[/dim]")
    
    return Panel("\n".join(content), title=title, title_align="left", style="blue", padding=(1, 2))


def create_error_panel(message: str, details: Optional[str] = None, title: str = "🚨 Error") -> Panel:
    """Create an error panel with message and optional details
    
    CLAUDE.md: < 15 lines - Simple panel creation for error messages
    
    Args:
        message: Main error message
        details: Optional details text
        title: Panel title
        
    Returns:
        Rich Panel with error styling
    """
    content = [f"[red]❌ {message}[/red]"]
    
    if details:
        content.append("")
        content.append("[bold]Details:[/bold]")
        content.append(f"[dim]{details}[/dim]")
    
    return Panel("\n".join(content), title=title, title_align="left", style="red", padding=(1, 2))


def create_success_panel(message: str, details: Optional[str] = None, title: str = "✅ Success") -> Panel:
    """Create a success panel with message and optional details
    
    CLAUDE.md: < 15 lines - Simple panel creation for success messages
    
    Args:
        message: Main success message
        details: Optional details text
        title: Panel title
        
    Returns:
        Rich Panel with success styling
    """
    content = [f"[green]✅ {message}[/green]"]
    
    if details:
        content.append("")
        content.append(f"[dim]{details}[/dim]")
    
    return Panel("\n".join(content), title=title, title_align="left", style="green", padding=(1, 2))


def create_warning_panel(message: str, details: Optional[str] = None, title: str = "⚠️ Warning") -> Panel:
    """Create a warning panel with message and optional details
    
    CLAUDE.md: < 15 lines - Simple panel creation for warning messages
    
    Args:
        message: Main warning message
        details: Optional details text
        title: Panel title
        
    Returns:
        Rich Panel with warning styling
    """
    content = [f"[yellow]⚠️ {message}[/yellow]"]
    
    if details:
        content.append("")
        content.append(f"[dim]{details}[/dim]")
    
    return Panel("\n".join(content), title=title, title_align="left", style="yellow", padding=(1, 2))


def print_success(message: str, details: Optional[str] = None) -> None:
    """Print a success message using the global console"""
    console = Console()
    display_success(console, message, details)


def print_error(message: str, details: Optional[str] = None) -> None:
    """Print an error message using the global console"""
    console = Console()
    display_error(console, message, details)


def create_status_panel(items: List[str], title: str = "Status") -> Panel:
    """Create a status panel from a list of status items (overload)"""
    if isinstance(items, list):
        content = "\n".join(items)
        return Panel(content, title=title, style="blue", padding=(1, 2))
    else:
        # Handle the original dict format
        return create_status_panel(items)


def create_recommendations_panel(recommendations: List[str]) -> Panel:
    """Create a recommendations panel"""
    return create_recommendations_list(recommendations, "💡 Recommendations")


def format_table(data: List[List[str]], headers: List[str]) -> str:
    """
    Format data as a Rich table.

    Args:
        data: List of rows, each row is a list of column values
        headers: List of column headers

    Returns:
        Formatted table string
    """
    from rich.table import Table
    from rich.console import Console
    import io

    # Create a table with the given headers
    table = Table(show_header=True, header_style="bold cyan")

    # Add columns
    for header in headers:
        table.add_column(header)

    # Add rows
    for row in data:
        # Ensure all values are strings
        str_row = [str(val) for val in row]
        table.add_row(*str_row)

    # Render table to string
    console = Console(file=io.StringIO(), force_terminal=True)
    console.print(table)
    return console.file.getvalue()
