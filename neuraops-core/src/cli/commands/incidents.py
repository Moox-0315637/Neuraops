"""
NeuraOps Incident Management CLI Commands
Professional CLI interface for incident detection, response, and management
AI-powered incident resolution with gpt-oss-20b
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import typer
from rich import print as rich_print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.layout import Layout
from rich.live import Live

from ...devops_commander.config import get_config
from ...modules.incidents.detector import (
    IncidentDetector,
    IncidentDetectionResult,
    IncidentType,
    IncidentSeverity,
    DetectedIncident,
)
from ...modules.incidents.responder import IncidentResponder, ResponseMode
from ...modules.incidents.playbooks import PlaybookStatus, create_playbook_library

# Rich console for beautiful output
console = Console()

# Create Typer app for incident commands
incidents_app = typer.Typer(
    name="incidents",
    help="🚨 AI-powered incident detection, response, and management",
    rich_markup_mode="rich",
)

# UI Messages Constants
DETECTION_PROGRESS_TITLE = "Detection Progress"


def get_incident_components():
    """Get initialized incident management components"""
    config = get_config()
    detector = IncidentDetector(config)
    responder = IncidentResponder(config)
    playbook_library = create_playbook_library(config)
    return detector, responder, playbook_library, config


# Demo incident scenarios for reliable demonstrations
DEMO_INCIDENTS = {
    "database_timeout": {
        "description": "Database connection timeout affecting user authentication",
        "severity": "high",
        "source": "alerts",
        "log_sample": """2024-08-31 10:15:23 ERROR [auth-service] Database connection timeout after 30 seconds
2024-08-31 10:15:45 ERROR [auth-service] Failed to authenticate user: database unavailable
2024-08-31 10:16:12 CRITICAL [database] Connection pool exhausted, 0 available connections""",
        "expected_type": "DATABASE_OUTAGE",
        "response_time": "15-30 minutes",
    },
    "memory_leak": {
        "description": "Application memory leak causing performance degradation",
        "severity": "medium",
        "source": "metrics",
        "log_sample": """2024-08-31 09:30:15 WARNING [app-server] Memory usage at 85%
2024-08-31 09:45:22 WARNING [app-server] Memory usage at 92% 
2024-08-31 10:00:18 ERROR [app-server] OutOfMemoryError: Java heap space""",
        "expected_type": "PERFORMANCE_ISSUE",
        "response_time": "30-60 minutes",
    },
    "security_breach": {
        "description": "Suspicious login attempts from multiple IP addresses",
        "severity": "critical",
        "source": "security_alerts",
        "log_sample": """2024-08-31 08:15:33 WARNING [security] Failed login attempt from 192.168.1.100
2024-08-31 08:15:45 WARNING [security] Failed login attempt from 10.0.0.50
2024-08-31 08:16:02 CRITICAL [security] Brute force attack detected: 50+ failed attempts""",
        "expected_type": "SECURITY_BREACH",
        "response_time": "5-15 minutes",
    },
}


def get_demo_incident(name: str) -> Dict[str, Any]:
    """Get a predefined demo incident scenario"""
    return DEMO_INCIDENTS.get(name, DEMO_INCIDENTS["database_timeout"])


def _select_demo_scenario(console) -> Dict[str, Any]:
    """Select and display demo scenarios for incident detection"""
    console.print("\n[bold yellow]Demo Mode: Select a predefined incident scenario[/bold yellow]")

    # Display available scenarios
    scenario_table = Table(title="Available Demo Scenarios")
    scenario_table.add_column("ID", style="cyan", width=3)
    scenario_table.add_column("Scenario", style="magenta")
    scenario_table.add_column("Severity", style="red")
    scenario_table.add_column("Type", style="green")

    scenarios = list(DEMO_INCIDENTS.keys())
    for i, (name, details) in enumerate(DEMO_INCIDENTS.items(), 1):
        scenario_table.add_row(
            str(i),
            (details["description"][:50] + "..." if len(details["description"]) > 50 else details["description"]),
            details["severity"].upper(),
            details["expected_type"],
        )

    console.print(scenario_table)

    # Scenario selection
    scenario_choice = IntPrompt.ask("\nSelect scenario", default=1, choices=[str(i) for i in range(1, len(scenarios) + 1)])
    selected_scenario = scenarios[scenario_choice - 1]
    demo_incident = get_demo_incident(selected_scenario)
    console.print(f"\n[green]✓[/green] Selected: {demo_incident['description']}")

    return demo_incident


def _collect_incident_info_interactive(console) -> tuple:
    """Interactively collect incident information from user"""
    # Interactive input collection
    console.print("\n[bold]Step 1: Incident Description[/bold]")
    description = Prompt.ask("Describe the incident")

    # Interactive severity selection
    console.print("\n[bold]Step 2: Severity Assessment[/bold]")
    severity_table = Table(title="Severity Levels")
    severity_table.add_column("Level", style="cyan")
    severity_table.add_column("Description", style="white")
    severity_table.add_column("Response Time", style="yellow")

    severity_levels = {
        "critical": ("System down, severe impact", "< 15 minutes"),
        "high": ("Significant functionality affected", "< 1 hour"),
        "medium": ("Some functionality degraded", "< 4 hours"),
        "low": ("Minor issues, workarounds available", "< 24 hours"),
        "info": ("Informational, no immediate action", "As time permits"),
    }

    for level, (desc, time) in severity_levels.items():
        severity_table.add_row(level.title(), desc, time)

    console.print(severity_table)
    severity = Prompt.ask("\nSelect severity level", choices=list(severity_levels.keys()), default="medium")

    # Source selection
    console.print("\n[bold]Step 3: Incident Source[/bold]")
    source = Prompt.ask(
        "Incident source",
        choices=["logs", "metrics", "alerts", "user_reports", "monitoring"],
        default="alerts",
    )

    return description, severity, source


def _display_detection_progress(console, layout, description, detector, source, severity):
    """Display incident detection progress with live updates"""
    with Live(layout, refresh_per_second=4, console=console) as _:
        # Header
        layout["header"].update(Panel(f"[bold]Analyzing:[/bold] {description}", style="blue"))

        # Detection progress
        layout["main"].update(Panel("🧠 AI analyzing incident patterns...", title=DETECTION_PROGRESS_TITLE))
        layout["footer"].update(Panel("⏳ Connecting to AI engine...", style="yellow"))

        try:
            # Perform detection
            incident = asyncio.run(
                detector.detect_from_description(
                    description=description,
                    source=source,
                    expected_severity=IncidentSeverity(severity.upper()) if severity else None,
                )
            )

            # Update with results
            layout["main"].update(Panel("✅ Incident analysis complete!", title=DETECTION_PROGRESS_TITLE))
            layout["footer"].update(
                Panel(
                    f"[green]Detected:[/green] {incident.incident_type.value}\n[yellow]Severity:[/yellow] {incident.severity.value}\n[blue]Confidence:[/blue] {incident.confidence_score:.0%}",
                    title="Results",
                    style="green",
                )
            )

            # Brief pause to show results
            import time

            time.sleep(2)

            return incident

        except Exception as e:
            layout["main"].update(Panel(f"❌ Detection failed: {e}", title="Error", style="red"))
            layout["footer"].update(Panel("Please check AI connectivity", style="red"))
            import time

            time.sleep(2)
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@incidents_app.command("interactive")
def interactive_incident_detection(
    demo_mode: bool = typer.Option(False, "--demo", help="Enable demo mode with predefined scenarios"),
):
    """Interactive incident detection with guided severity selection and demo scenarios"""
    _display_header()

    # Get incident data based on mode
    if demo_mode:
        incident_data = _select_demo_scenario()
    else:
        incident_data = _collect_incident_input()

    # Perform detection with progress display
    incident = _perform_detection_with_progress(incident_data)

    # Display detailed results
    _display_detected_incident(incident, verbose=True)

    # Handle response options if incident detected
    if incident.incident_type != IncidentType.NO_INCIDENT:
        console.print("\n[bold]Step 4: Response Options[/bold]")
        _, responder, playbook_library, _ = get_incident_components()
        suitable_playbooks = playbook_library.find_suitable_playbooks(incident)

        if suitable_playbooks:
            _handle_playbook_selection(incident, suitable_playbooks, responder, playbook_library)
        else:
            console.print("[yellow]⚠️ No automated playbooks available for this incident type[/yellow]")
            console.print("Consider creating a custom playbook or handling manually.")


def _display_header() -> None:
    """Display the interactive incident detection header"""
    console.print(
        Panel(
            "[bold cyan]🚨 Interactive Incident Detection[/bold cyan]\nGuided incident analysis with AI-powered insights",
            title="NeuraOps Incident Management",
            border_style="blue",
        )
    )


def _display_demo_scenarios_table() -> Table:
    """Create and return the demo scenarios table"""
    scenario_table = Table(title="Available Demo Scenarios")
    scenario_table.add_column("ID", style="cyan", width=3)
    scenario_table.add_column("Scenario", style="magenta")
    scenario_table.add_column("Severity", style="red")
    scenario_table.add_column("Type", style="green")

    for i, (name, details) in enumerate(DEMO_INCIDENTS.items(), 1):
        scenario_table.add_row(
            str(i),
            (details["description"][:50] + "..." if len(details["description"]) > 50 else details["description"]),
            details["severity"].upper(),
            details["expected_type"],
        )
    return scenario_table


def _select_demo_scenario() -> Dict[str, str]:
    """Handle demo scenario selection and return incident data"""
    console.print("\n[bold yellow]Demo Mode: Select a predefined incident scenario[/bold yellow]")

    scenario_table = _display_demo_scenarios_table()
    console.print(scenario_table)

    scenarios = list(DEMO_INCIDENTS.keys())
    scenario_choice = IntPrompt.ask("\nSelect scenario", default=1, choices=[str(i) for i in range(1, len(scenarios) + 1)])
    selected_scenario = scenarios[scenario_choice - 1]
    demo_incident = get_demo_incident(selected_scenario)

    console.print(f"\n[green]✓[/green] Selected: {demo_incident['description']}")

    return {"description": demo_incident["description"], "severity": demo_incident["severity"], "source": demo_incident["source"]}


def _display_severity_table() -> None:
    """Display the severity levels table"""
    severity_table = Table(title="Severity Levels")
    severity_table.add_column("Level", style="cyan")
    severity_table.add_column("Description", style="white")
    severity_table.add_column("Response Time", style="yellow")

    severity_levels = {
        "critical": ("System down, severe impact", "< 15 minutes"),
        "high": ("Significant functionality affected", "< 1 hour"),
        "medium": ("Some functionality degraded", "< 4 hours"),
        "low": ("Minor issues, workarounds available", "< 24 hours"),
        "info": ("Informational, no immediate action", "As time permits"),
    }

    for level, (desc, time) in severity_levels.items():
        severity_table.add_row(level.title(), desc, time)

    console.print(severity_table)


def _collect_incident_input() -> Dict[str, str]:
    """Collect incident input interactively and return incident data"""
    console.print("\n[bold]Step 1: Incident Description[/bold]")
    description = Prompt.ask("Describe the incident")

    console.print("\n[bold]Step 2: Severity Assessment[/bold]")
    _display_severity_table()

    severity_levels = ["critical", "high", "medium", "low", "info"]
    severity = Prompt.ask("\nSelect severity level", choices=severity_levels, default="medium")

    console.print("\n[bold]Step 3: Incident Source[/bold]")
    source = Prompt.ask(
        "Incident source",
        choices=["logs", "metrics", "alerts", "user_reports", "monitoring"],
        default="alerts",
    )

    return {"description": description, "severity": severity, "source": source}


def _perform_detection_with_progress(incident_data: Dict[str, str]) -> DetectedIncident:
    """Perform incident detection with progress display"""
    detector, _, _, _ = get_incident_components()
    console.print("\n[cyan]🔍 Analyzing incident...[/cyan]")

    layout = Layout()
    layout.split_column(Layout(name="header", size=3), Layout(name="main"), Layout(name="footer", size=5))

    with Live(layout, refresh_per_second=4, console=console) as _:
        layout["header"].update(Panel(f"[bold]Analyzing:[/bold] {incident_data['description']}", style="blue"))
        layout["main"].update(Panel("🧠 AI analyzing incident patterns...", title=DETECTION_PROGRESS_TITLE))
        layout["footer"].update(Panel("⏳ Connecting to AI engine...", style="yellow"))

        try:
            incident = asyncio.run(
                detector.detect_from_description(
                    description=incident_data["description"],
                    source=incident_data["source"],
                    expected_severity=IncidentSeverity(incident_data["severity"].upper()) if incident_data["severity"] else None,
                )
            )

            layout["main"].update(Panel("✅ Incident analysis complete!", title=DETECTION_PROGRESS_TITLE))
            layout["footer"].update(
                Panel(
                    f"[green]Detected:[/green] {incident.incident_type.value}\n[yellow]Severity:[/yellow] {incident.severity.value}\n[blue]Confidence:[/blue] {incident.confidence_score:.0%}",
                    title="Results",
                    style="green",
                )
            )

            import time

            time.sleep(2)
            return incident

        except Exception as e:
            layout["main"].update(Panel(f"❌ Detection failed: {e}", title="Error", style="red"))
            layout["footer"].update(Panel("Please check AI connectivity", style="red"))
            time.sleep(2)
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


def _display_playbook_options(suitable_playbooks: List) -> None:
    """Display available playbook options in a table"""
    playbook_table = Table(title="Available Response Playbooks")
    playbook_table.add_column("ID", style="cyan", width=3)
    playbook_table.add_column("Playbook", style="magenta")
    playbook_table.add_column("Est. Time", style="yellow")
    playbook_table.add_column("Steps", style="blue")

    for i, playbook in enumerate(suitable_playbooks[:5], 1):  # Show top 5
        step_count = len(playbook.steps) if hasattr(playbook, "steps") else "N/A"
        playbook_table.add_row(
            str(i),
            playbook.name,
            getattr(playbook, "estimated_duration", "Unknown"),
            str(step_count),
        )

    console.print(playbook_table)


def _handle_playbook_selection(incident: DetectedIncident, suitable_playbooks: List, responder, playbook_library) -> None:
    """Handle interactive playbook selection and execution"""
    _display_playbook_options(suitable_playbooks)

    action = Prompt.ask(
        "\nChoose action",
        choices=["execute", "preview", "skip", "manual"],
        default="preview",
    )

    if action in ["execute", "preview"]:
        selected_id = IntPrompt.ask(
            "Select playbook",
            default=1,
            choices=[str(i) for i in range(1, min(6, len(suitable_playbooks) + 1))],
        )
        selected_playbook = suitable_playbooks[selected_id - 1]

        if action == "execute":
            console.print(f"\n[green]🚀 Executing playbook: {selected_playbook.name}[/green]")
            asyncio.run(_execute_incident_response(incident, selected_playbook, responder, playbook_library))
        else:  # preview
            _display_playbook_details(selected_playbook)


def _validate_detection_inputs(log_file: Optional[Path]) -> None:
    """Validate detection inputs and exit if invalid."""
    if log_file and not log_file.exists():
        console.print(f"❌ [red]Log file not found: {log_file}[/red]")
        raise typer.Exit(1)


def _perform_incident_detection(
    detector, description: str, log_file: Optional[Path]
) -> 'IncidentDetectionResult':
    """Execute core detection logic."""
    if log_file:
        return asyncio.run(detector.detect_from_log_file(str(log_file)))
    else:
        return asyncio.run(detector.detect_from_description(
            incident_description=description
        ))


def _handle_detection_results(
    incident: 'IncidentDetectionResult', 
    json_output: bool, 
    verbose: bool
) -> Optional['DetectedIncident']:
    """Process and display detection results."""
    if not incident.success or not incident.incidents:
        console.print(f"❌ [red]No incident detected: {incident.error_message or 'Unknown error'}[/red]")
        return None
    
    detected_incident = incident.incidents[0]
    
    if json_output:
        rich_print(json.dumps(detected_incident.model_dump(), indent=2, default=str))
        return detected_incident
    
    _display_detected_incident(detected_incident, verbose)
    return detected_incident


def _execute_auto_response_if_requested(
    auto_respond: bool,
    detected_incident: 'DetectedIncident',
    responder,
    playbook_library
) -> None:
    """Handle auto-response workflow if enabled."""
    if not auto_respond or detected_incident.incident_type == IncidentType.CONFIGURATION_ERROR:
        return
        
    console.print("\n🤖 [yellow]Auto-response enabled - finding suitable playbooks...[/yellow]")
    
    suitable_playbooks = playbook_library.find_suitable_playbooks(detected_incident)
    if suitable_playbooks:
        best_playbook = suitable_playbooks[0]
        console.print(f"📋 Selected playbook: [cyan]{best_playbook.name}[/cyan]")
        asyncio.run(_execute_incident_response(
            detected_incident, best_playbook, responder, playbook_library, auto_confirm=True
        ))
    else:
        console.print("❌ [red]No suitable playbooks found for auto-response[/red]")


@incidents_app.command()
def detect(
    description: str = typer.Argument(..., help="Description of the suspected incident"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Incident source: logs, metrics, alerts, user_reports"),
    severity: Optional[str] = typer.Option(None, "--severity", "-sev", help="Expected severity: critical, high, medium, low, info"),
    log_file: Optional[Path] = typer.Option(None, "--log-file", "-f", help="Log file to analyze for incident detection"),
    auto_respond: bool = typer.Option(False, "--auto-respond", "-a", help="Automatically trigger response if incident detected"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output results in JSON format"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output with AI reasoning"),
):
    """
    🔍 **Detect incidents** using AI analysis

    Analyzes descriptions, logs, or system state to identify potential incidents.
    Can optionally trigger automated response workflows.

    **Examples:**

      neuraops incidents detect "Database responding slowly" --severity high

      neuraops incidents detect "500 errors in app" --log-file /var/log/app.log --auto-respond

      neuraops incidents detect "Network timeout issues" --source alerts --verbose
    """
    
    # Validation phase (Fail Fast)
    _validate_detection_inputs(log_file)
    
    detector, responder, playbook_library, _ = get_incident_components()
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            
            # Detection phase
            detect_task = progress.add_task("🧠 Analyzing incident with AI...", total=None)
            
            incident = _perform_incident_detection(detector, description, log_file)
            
            progress.update(detect_task, description="✅ Detection complete", completed=True)
        
        # Results handling
        detected_incident = _handle_detection_results(incident, json_output, verbose)
        if not detected_incident:
            return
            
        # Auto-response if requested
        _execute_auto_response_if_requested(auto_respond, detected_incident, responder, playbook_library)
        
    except Exception as e:
        console.print(f"❌ [red]Incident detection failed: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@incidents_app.command()
def respond(
    incident_id: Optional[str] = typer.Argument(None, help="Incident ID from detection"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Incident description if no incident ID provided"),
    playbook: Optional[str] = typer.Option(None, "--playbook", "-p", help="Specific playbook to use for response"),
    mode: str = typer.Option("guided", "--mode", "-m", help="Response mode: manual, guided, auto"),
    dry_run: bool = typer.Option(False, "--dry-run", "--simulate", help="Simulate response without executing commands"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompts"),
    variables: Optional[str] = typer.Option(None, "--variables", "-var", help="JSON string of variables for playbook execution"),
):
    """
    🛠️ **Respond to incidents** with automated playbooks

    Executes incident response playbooks with safety checks and rollback capabilities.
    Supports manual oversight, guided execution, or full automation.

    **Examples:**

      neuraops incidents respond incident-123 --mode guided

      neuraops incidents respond --description "Database down" --playbook database_performance_issues

      neuraops incidents respond incident-456 --mode auto --confirm --dry-run
    """

    detector, responder, playbook_library, _ = get_incident_components()

    try:
        # Parse variables and resolve incident
        playbook_variables = _parse_playbook_variables(variables)
        incident = _resolve_incident(incident_id, description, detector)

        # Display incident details
        console.print("\n📊 [bold blue]Incident Details[/bold blue]")
        _display_detected_incident(incident, verbose=False)

        # Find suitable playbooks
        suitable_playbooks = playbook_library.find_suitable_playbooks(incident)
        if not suitable_playbooks:
            suitable_playbooks = _handle_custom_playbook_generation(incident, playbook_library)
            if not suitable_playbooks:
                return

        # Select playbook
        if playbook:
            selected_playbook = _select_specific_playbook(playbook, playbook_library)
        else:
            selected_playbook = _select_playbook_interactive(suitable_playbooks)

        if not selected_playbook:
            console.print("❌ [red]No playbook selected[/red]")
            return

        # Execute response
        asyncio.run(
            _execute_incident_response(
                incident,
                selected_playbook,
                responder,
                playbook_library,
                _mode=ResponseMode(mode),
                dry_run=dry_run,
                variables=playbook_variables,
                auto_confirm=confirm,
            )
        )

    except Exception as e:
        console.print(f"❌ [red]Incident response failed: {e}[/red]")
        console.print_exception()
        raise typer.Exit(1)


def _parse_playbook_variables(variables: Optional[str]) -> Dict[str, Any]:
    """Parse JSON variables string into dictionary"""
    if not variables:
        return {}

    try:
        return json.loads(variables)
    except json.JSONDecodeError:
        console.print("❌ [red]Invalid JSON format for variables[/red]")
        raise typer.Exit(1)


def _resolve_incident(incident_id: Optional[str], description: Optional[str], detector) -> DetectedIncident:
    """Resolve incident from ID or description"""
    if incident_id:
        console.print(f"🔍 [yellow]Looking up incident: {incident_id}[/yellow]")
        # For demo, create a sample incident
        return DetectedIncident(
            incident_type=IncidentType.DATABASE_ISSUES,
            severity=IncidentSeverity.HIGH,
            description="Sample incident for demo",
            affected_services=["database"],
            evidence=[],
            confidence_score=0.85,
            estimated_impact="High impact on application performance",
            recommended_actions=["Restart database service", "Analyze slow queries"],
        )
    elif description:
        console.print("🧠 [yellow]Detecting incident from description...[/yellow]")
        return asyncio.run(detector.detect_from_description(description))
    else:
        console.print("❌ [red]Either incident-id or description must be provided[/red]")
        raise typer.Exit(1)


def _handle_custom_playbook_generation(incident: DetectedIncident, playbook_library) -> List:
    """Handle custom playbook generation if no suitable playbooks found"""
    console.print("❌ [red]No suitable playbooks found for this incident[/red]")

    if Confirm.ask("\n🤖 Generate custom playbook using AI?"):
        console.print("🧠 [yellow]Generating custom playbook...[/yellow]")
        custom_playbook = asyncio.run(playbook_library.generate_playbook_from_incident(incident))
        playbook_library.add_playbook(custom_playbook)
        return [custom_playbook]
    return []


def _select_specific_playbook(playbook_name: str, playbook_library):
    """Select a specific playbook by name"""
    selected_playbook = playbook_library.get_playbook(playbook_name)
    if not selected_playbook:
        console.print(f"❌ [red]Playbook not found: {playbook_name}[/red]")
        raise typer.Exit(1)
    return selected_playbook


@incidents_app.command()
def status(
    execution_id: Optional[str] = typer.Argument(None, help="Execution ID to check status"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all recent executions"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """
    📈 **Check incident response status** and execution history

    Monitor playbook execution progress, view logs, and track resolution status.

    **Examples:**

      neuraops incidents status exec-20240831-142030

      neuraops incidents status --list

      neuraops incidents status exec-123 --json
    """

    _, _, playbook_library, _ = get_incident_components()

    if list_all:
        _display_execution_list(playbook_library)
        return

    if not execution_id:
        console.print("❌ [red]Execution ID required. Use --list to see all executions.[/red]")
        raise typer.Exit(1)

    execution = playbook_library.get_execution_status(execution_id)
    if not execution:
        console.print(f"❌ [red]Execution not found: {execution_id}[/red]")
        raise typer.Exit(1)

    if json_output:
        _output_execution_json(execution)
    else:
        _display_execution_status(execution)


def _format_execution_duration(execution) -> str:
    """Format execution duration string"""
    if not execution.started_at:
        return "N/A"

    if execution.completed_at:
        return str(execution.completed_at - execution.started_at)
    else:
        return f"Running ({datetime.now(timezone.utc) - execution.started_at})"


def _get_status_color(status: PlaybookStatus) -> str:
    """Get color for execution status"""
    status_colors = {
        PlaybookStatus.SUCCESS: "green",
        PlaybookStatus.FAILED: "red",
        PlaybookStatus.RUNNING: "yellow",
        PlaybookStatus.CANCELLED: "orange1",
        PlaybookStatus.ROLLED_BACK: "purple",
    }
    return status_colors.get(status, "white")


def _display_execution_list(playbook_library) -> None:
    """Display list of all recent executions"""
    console.print("\n📋 [bold blue]Recent Incident Response Executions[/bold blue]")

    table = Table(
        "Execution ID",
        "Playbook",
        "Status",
        "Started",
        "Duration",
        title="Incident Response History",
        show_header=True,
        header_style="bold magenta",
    )

    for exec_id, execution in playbook_library.executions.items():
        duration = _format_execution_duration(execution)
        status_color = _get_status_color(execution.status)

        table.add_row(
            exec_id[:20] + "...",
            execution.playbook_name,
            f"[{status_color}]{execution.status.value}[/{status_color}]",
            (execution.started_at.strftime("%Y-%m-%d %H:%M:%S") if execution.started_at else "N/A"),
            duration[:20],
        )

    console.print(table)


def _convert_execution_to_dict(execution) -> Dict[str, Any]:
    """Convert execution object to dictionary for JSON output"""
    return {
        "execution_id": execution.execution_id,
        "playbook_name": execution.playbook_name,
        "incident_id": execution.incident_id,
        "status": execution.status.value,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "current_step_index": execution.current_step_index,
        "executed_steps": execution.executed_steps,
        "failed_steps": execution.failed_steps,
        "rollback_steps": execution.rollback_steps,
        "execution_log": execution.execution_log,
        "error_messages": execution.error_messages,
    }


def _output_execution_json(execution) -> None:
    """Output execution data in JSON format"""
    execution_dict = _convert_execution_to_dict(execution)
    rich_print(json.dumps(execution_dict, indent=2))


@incidents_app.command()
def playbooks(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all available playbooks"),
    incident_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by incident type"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity level"),
    details: Optional[str] = typer.Option(None, "--details", "-d", help="Show detailed view of specific playbook"),
    create_custom: bool = typer.Option(False, "--create", "-c", help="Create custom playbook interactively"),
    delete_playbook: Optional[str] = typer.Option(None, "--delete", help="Delete a specific playbook by name"),
):
    """
    📚 **Manage incident response playbooks**

    View, filter, and manage the library of incident response playbooks.
    Create custom playbooks for specific scenarios.

    **Examples:**

      neuraops incidents playbooks --list

      neuraops incidents playbooks --type database_issues --severity high

      neuraops incidents playbooks --details network_connectivity_issues

      neuraops incidents playbooks --create
      
      neuraops incidents playbooks --delete custom_playbook_name
    """

    _, _, playbook_library, _ = get_incident_components()

    if delete_playbook:
        _handle_playbook_deletion(delete_playbook, playbook_library)
        return

    if create_custom:
        asyncio.run(_create_custom_playbook_interactive(playbook_library))
        return

    if details:
        playbook = playbook_library.get_playbook(details)
        if not playbook:
            console.print(f"❌ [red]Playbook not found: {details}[/red]")
            raise typer.Exit(1)
        _display_playbook_details(playbook)
        return

    # Filter playbooks
    filters = {}
    if incident_type:
        try:
            filters["incident_type"] = IncidentType(incident_type)
        except ValueError:
            console.print(f"❌ [red]Invalid incident type: {incident_type}[/red]")
            console.print(f"Valid types: {', '.join([t.value for t in IncidentType])}")
            raise typer.Exit(1)

    if severity:
        try:
            filters["severity"] = IncidentSeverity(severity)
        except ValueError:
            console.print(f"❌ [red]Invalid severity: {severity}[/red]")
            console.print(f"Valid severities: {', '.join([s.value for s in IncidentSeverity])}")
            raise typer.Exit(1)

    playbooks = playbook_library.list_playbooks(**filters)

    if not playbooks:
        console.print("📚 [yellow]No playbooks found matching criteria[/yellow]")
        return

    # Display playbooks table
    _display_playbooks_table(playbooks)


@incidents_app.command()
def cancel(
    execution_id: str = typer.Argument(..., help="Execution ID to cancel"),
    force: bool = typer.Option(False, "--force", "-f", help="Force cancellation without confirmation"),
):
    """
    🛑 **Cancel running incident response**

    Safely stop a running playbook execution with proper cleanup.

    **Examples:**

      neuraops incidents cancel exec-20240831-142030

      neuraops incidents cancel exec-123 --force
    """

    _, _, playbook_library, _ = get_incident_components()

    execution = playbook_library.get_execution_status(execution_id)
    if not execution:
        console.print(f"❌ [red]Execution not found: {execution_id}[/red]")
        raise typer.Exit(1)

    if execution.status != PlaybookStatus.RUNNING:
        console.print(f"❌ [red]Execution is not running (status: {execution.status.value})[/red]")
        return

    # Confirmation
    # Confirmation
    if not force and not Confirm.ask(f"🛑 Cancel execution {execution_id}?"):
        console.print("❌ [yellow]Cancellation aborted[/yellow]")
        return

    # Cancel execution
    success = playbook_library.cancel_execution(execution_id)

    if success:
        console.print(f"✅ [green]Execution cancelled: {execution_id}[/green]")
    else:
        console.print(f"❌ [red]Failed to cancel execution: {execution_id}[/red]")


# Helper functions for rich display and interaction


def _display_detected_incident(incident: DetectedIncident, verbose: bool = False) -> None:
    """Display incident details in a rich format"""

    # Severity color mapping
    severity_colors = {
        IncidentSeverity.CRITICAL: "red",
        IncidentSeverity.HIGH: "orange1",
        IncidentSeverity.MEDIUM: "yellow",
        IncidentSeverity.LOW: "green",
        IncidentSeverity.INFO: "blue",
    }

    severity_color = severity_colors.get(incident.severity, "white")

    # Main incident panel
    incident_content = f"""
[bold]Type:[/bold] {incident.incident_type.value.replace('_', ' ').title()}
[bold]Severity:[/bold] [{severity_color}]{incident.severity.value.upper()}[/{severity_color}]
[bold]Description:[/bold] {incident.description}
[bold]Confidence:[/bold] {incident.confidence_score:.1%}
[bold]Estimated Impact:[/bold] {incident.estimated_impact}
"""

    if incident.affected_services:
        incident_content += f"\n[bold]Affected Services:[/bold] {', '.join(incident.affected_services)}"

    panel = Panel(
        incident_content.strip(),
        title="🚨 Detected Incident",
        title_align="left",
        border_style=severity_color,
        padding=(1, 2),
    )

    console.print(panel)

    # Evidence table
    if incident.evidence and verbose:
        evidence_table = Table(
            "Source",
            "Timestamp",
            "Description",
            "Confidence",
            title="Evidence",
            show_header=True,
            header_style="bold cyan",
        )

        for evidence in incident.evidence[:5]:  # Limit to first 5
            evidence_table.add_row(
                evidence.source,
                evidence.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                (evidence.description[:60] + "..." if len(evidence.description) > 60 else evidence.description),
                f"{evidence.confidence:.1%}",
            )

        console.print(evidence_table)

    # Recommended actions
    if incident.recommended_actions:
        console.print("\n💡 [bold cyan]Recommended Actions:[/bold cyan]")
        for i, action in enumerate(incident.recommended_actions, 1):
            console.print(f"  {i}. {action}")


def _select_playbook_interactive(playbooks: List) -> Optional[Any]:
    """Interactive playbook selection"""

    if not playbooks:
        return None

    console.print("\n📋 [bold blue]Available Playbooks[/bold blue]")

    for i, playbook in enumerate(playbooks, 1):
        console.print(f"  {i}. [cyan]{playbook.name}[/cyan] - {playbook.description}")

    try:
        choice = typer.prompt("\nSelect playbook (number)", type=int)
        if 1 <= choice <= len(playbooks):
            return playbooks[choice - 1]
        else:
            console.print("❌ [red]Invalid selection[/red]")
            return None
    except (ValueError, typer.Abort):
        return None


async def _execute_incident_response(
    incident,
    playbook,
    _responder,
    playbook_library,
    _mode: ResponseMode = ResponseMode.SEMI_AUTO,
    dry_run: bool = False,
    variables: Dict[str, Any] = None,
    auto_confirm: bool = False,
) -> None:
    """Execute incident response with progress tracking"""

    console.print(f"\n🛠️ [bold green]Executing Playbook: {playbook.name}[/bold green]")

    if dry_run:
        console.print("🔍 [yellow]DRY RUN MODE - No commands will be executed[/yellow]")

    # Confirmation
    if not auto_confirm and not dry_run:
        if not Confirm.ask(f"\n⚠️ Execute playbook '{playbook.name}'?"):
            console.print("❌ [yellow]Execution aborted[/yellow]")
            return

    # Execute playbook
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:

        execution_task = progress.add_task("🚀 Executing playbook...", total=len(playbook.steps))

        try:
            execution = await playbook_library.execute_playbook(
                playbook_name=playbook.name,
                incident_id="incident-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
                variables=variables or {},
                dry_run=dry_run,
            )

            # Update progress as steps complete
            for step in playbook.steps:
                progress.update(execution_task, advance=1, description=f"Executing: {step.name}")
                await asyncio.sleep(0.1)  # Small delay for visual effect

            progress.update(execution_task, description="✅ Playbook execution completed")

        except Exception as e:
            progress.update(execution_task, description=f"❌ Execution failed: {str(e)[:50]}")
            console.print(f"\n❌ [red]Playbook execution failed: {e}[/red]")
            return

    # Display results
    console.print("\n📊 [bold blue]Execution Results[/bold blue]")
    _display_execution_status(execution)


def _display_execution_status(execution) -> None:
    """Display detailed execution status"""

    # Status color mapping
    status_colors = {
        PlaybookStatus.SUCCESS: "green",
        PlaybookStatus.FAILED: "red",
        PlaybookStatus.RUNNING: "yellow",
        PlaybookStatus.CANCELLED: "orange1",
        PlaybookStatus.ROLLED_BACK: "purple",
    }

    status_color = status_colors.get(execution.status, "white")

    # Main status panel
    status_content = f"""
[bold]Execution ID:[/bold] {execution.execution_id}
[bold]Playbook:[/bold] {execution.playbook_name}
[bold]Status:[/bold] [{status_color}]{execution.status.value.upper()}[/{status_color}]
[bold]Started:[/bold] {execution.started_at.strftime('%Y-%m-%d %H:%M:%S') if execution.started_at else 'N/A'}
[bold]Completed:[/bold] {execution.completed_at.strftime('%Y-%m-%d %H:%M:%S') if execution.completed_at else 'N/A'}
[bold]Progress:[/bold] {len(execution.executed_steps)}/{execution.current_step_index + 1} steps
"""

    panel = Panel(
        status_content.strip(),
        title="📊 Execution Status",
        title_align="left",
        border_style=status_color,
        padding=(1, 2),
    )

    console.print(panel)

    # Steps summary
    if execution.executed_steps or execution.failed_steps:
        steps_table = Table(
            "Step",
            "Status",
            "Details",
            title="Steps Execution Summary",
            show_header=True,
            header_style="bold cyan",
        )

        for step in execution.executed_steps:
            steps_table.add_row(step, "[green]✅ Success[/green]", "Completed successfully")

        for step in execution.failed_steps:
            steps_table.add_row(step, "[red]❌ Failed[/red]", "Execution failed")

        for step in execution.rollback_steps:
            steps_table.add_row(step, "[purple]↩️ Rolled back[/purple]", "Changes reverted")

        console.print(steps_table)

    # Error messages
    if execution.error_messages:
        console.print("\n❌ [bold red]Error Messages:[/bold red]")
        for error in execution.error_messages[-3:]:  # Show last 3 errors
            console.print(f"  • {error}")


def _display_playbooks_table(playbooks) -> None:
    """Display playbooks in a formatted table"""

    table = Table(
        "Name",
        "Incident Type",
        "Severities",
        "Steps",
        "Updated",
        title="📚 Available Playbooks",
        show_header=True,
        header_style="bold magenta",
    )

    for playbook in playbooks:
        # Handle both enum and string values for severity levels
        severities = []
        for s in playbook.severity_levels:
            if hasattr(s, 'value'):
                severities.append(s.value)
            else:
                severities.append(str(s))
        severities_str = ", ".join(severities)

        # Handle both enum and string values for incident_type
        if hasattr(playbook.incident_type, 'value'):
            incident_type_str = playbook.incident_type.value.replace("_", " ").title()
        else:
            incident_type_str = str(playbook.incident_type).replace("_", " ").title()
        
        table.add_row(
            playbook.name,
            incident_type_str,
            severities_str,
            str(len(playbook.steps)),
            playbook.updated_at.strftime("%Y-%m-%d"),
        )

    console.print(table)


def _get_severity_display(severity_levels) -> str:
    """Helper: Convert severity levels to display string (CLAUDE.md: <50 lines)"""
    severities = []
    for s in severity_levels:
        if hasattr(s, 'value'):
            severities.append(s.value)
        elif isinstance(s, str):
            severities.append(s)
        else:
            severities.append(str(s))
    return ', '.join(severities)


def _get_incident_type_display(incident_type) -> str:
    """Helper: Convert incident type to display string (CLAUDE.md: <50 lines)"""
    if hasattr(incident_type, 'value'):
        return incident_type.value.replace('_', ' ').title()
    else:
        return str(incident_type).replace('_', ' ').title()

def _display_playbook_details(playbook) -> None:
    """Display detailed playbook information"""

    # Main playbook info
    playbook_content = f"""
[bold]Name:[/bold] {playbook.name}
[bold]Version:[/bold] {playbook.version}
[bold]Author:[/bold] {playbook.author}
        [bold]Incident Type:[/bold] {_get_incident_type_display(playbook.incident_type)}
[bold]Severities:[/bold] {_get_severity_display(playbook.severity_levels)}
[bold]Description:[/bold] {playbook.description}
[bold]Steps:[/bold] {len(playbook.steps)}
[bold]Max Execution Time:[/bold] {playbook.max_execution_time} seconds
"""

    panel = Panel(
        playbook_content.strip(),
        title="📋 Playbook Details",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )

    console.print(panel)

    # Steps details
    if playbook.steps:
        console.print("\n📝 [bold blue]Execution Steps:[/bold blue]")

        for i, step in enumerate(playbook.steps, 1):
            step_panel = Panel(
                f"""
[bold]Action:[/bold] {step.action.value.replace('_', ' ').title()}
[bold]Description:[/bold] {step.description}
[bold]Safety Level:[/bold] {step.safety_level.value}
[bold]Timeout:[/bold] {step.timeout}s
[bold]Dependencies:[/bold] {', '.join(step.depends_on) if step.depends_on else 'None'}
                """.strip(),
                title=f"Step {i}: {step.name}",
                title_align="left",
                border_style="blue",
                padding=(0, 1),
            )
            console.print(step_panel)

    # Prerequisites and success criteria
    if playbook.prerequisites:
        console.print("\n✅ [bold green]Prerequisites:[/bold green]")
        for prereq in playbook.prerequisites:
            console.print(f"  • {prereq}")

    if playbook.success_criteria:
        console.print("\n🎯 [bold cyan]Success Criteria:[/bold cyan]")
        for criteria in playbook.success_criteria:
            console.print(f"  • {criteria}")


async def _create_custom_playbook_interactive(playbook_library) -> None:
    """Interactive custom playbook creation"""

    console.print("\n🛠️ [bold blue]Custom Playbook Creation[/bold blue]")
    console.print("Let's create a custom incident response playbook.")

    # Gather basic information
    name = Prompt.ask("Playbook name")
    description = Prompt.ask("Playbook description")

    # Select incident type
    console.print("\nAvailable incident types:")
    for i, incident_type in enumerate(IncidentType, 1):
        console.print(f"  {i}. {incident_type.value.replace('_', ' ').title()}")

    type_choice = typer.prompt("Select incident type (number)", type=int)
    incident_type = list(IncidentType)[type_choice - 1]

    # Select severities
    console.print("\nAvailable severities (select multiple, comma-separated):")
    for i, severity in enumerate(IncidentSeverity, 1):
        console.print(f"  {i}. {severity.value.title()}")

    severity_choices = Prompt.ask("Select severities (e.g., 1,2,3)")
    severities = [list(IncidentSeverity)[int(i) - 1] for i in severity_choices.split(",")]

    # Generate AI-assisted playbook
    console.print("\n🤖 [yellow]Generating playbook with AI assistance...[/yellow]")

    # Create sample incident for generation
    sample_incident = DetectedIncident(
        incident_id=f"custom-{name.lower().replace(' ', '-')}",
        incident_type=incident_type,
        severity=severities[0],
        title=f"Custom Incident: {name}",
        description=description,
        affected_systems=[],
        root_cause_analysis="Custom playbook scenario - to be analyzed",
        impact_assessment="Custom incident scenario",
        evidence=[],
        detection_timestamp=datetime.now(),
        recommended_actions=[],
    )

    try:
        custom_playbook = await playbook_library.generate_playbook_from_incident(sample_incident, context=f"Custom playbook: {description}")
        custom_playbook.name = name
        custom_playbook.description = description
        custom_playbook.severity_levels = severities

        # Add to library
        playbook_library.add_playbook(custom_playbook)

        console.print(f"\n✅ [green]Custom playbook created: {name}[/green]")
        _display_playbook_details(custom_playbook)

    except Exception as e:
        console.print(f"\n❌ [red]Failed to create custom playbook: {e}[/red]")

def _handle_playbook_deletion(playbook_name: str, playbook_library) -> None:
    """Handle interactive playbook deletion with confirmation"""
    
    # Check if playbook exists
    playbook = playbook_library.get_playbook(playbook_name)
    if not playbook:
        console.print(f"❌ [red]Playbook not found: {playbook_name}[/red]")
        
        # Show available playbooks for reference
        console.print("\n📚 [cyan]Available playbooks:[/cyan]")
        all_playbooks = playbook_library.list_playbooks()
        for pb in all_playbooks[:10]:  # Show first 10
            console.print(f"  • {pb.name}")
        
        if len(all_playbooks) > 10:
            console.print(f"  ... and {len(all_playbooks) - 10} more")
            
        raise typer.Exit(1)
    
    # Show playbook details before deletion
    console.print("\n🗑️ [bold red]Playbook Deletion Confirmation[/bold red]")
    console.print(f"[bold]Name:[/bold] {playbook.name}")
    console.print(f"[bold]Description:[/bold] {playbook.description}")
    console.print(f"[bold]Incident Type:[/bold] {_get_incident_type_display(playbook.incident_type)}")
    console.print(f"[bold]Steps:[/bold] {len(playbook.steps)}")
    
    # Check if it's a built-in playbook (protect against accidental deletion)
    builtin_playbooks = [
        "network_connectivity_issues",
        "database_performance_issues", 
        "deployment_failure_response",
        "resource_exhaustion_response",
        "security_breach_response"
    ]
    
    if playbook_name in builtin_playbooks:
        console.print("\n⚠️  [bold yellow]WARNING: This is a built-in playbook![/bold yellow]")
        console.print("Deleting built-in playbooks is not recommended as they provide")
        console.print("essential incident response capabilities.")
        
        if not Confirm.ask(f"\n❗ Are you SURE you want to delete the built-in playbook '{playbook_name}'?", default=False):
            console.print("✅ [green]Deletion cancelled - playbook preserved[/green]")
            return
    else:
        if not Confirm.ask(f"\n🗑️ Delete playbook '{playbook_name}'? This action cannot be undone.", default=False):
            console.print("✅ [green]Deletion cancelled[/green]")
            return
    
    # Attempt to delete the playbook
    success = playbook_library.delete_playbook(playbook_name)
    
    if success:
        console.print(f"✅ [green]Successfully deleted playbook: {playbook_name}[/green]")
    else:
        console.print(f"❌ [red]Failed to delete playbook: {playbook_name}[/red]")
        raise typer.Exit(1)


# Export the app
__all__ = ["incidents_app"]
