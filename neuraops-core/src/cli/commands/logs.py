"""
NeuraOps Log CLI Commands
CLI commands for log analysis and management
"""

import asyncio
import json
import logging
from typing import Optional, Annotated
from pathlib import Path

import aiofiles

import typer
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ...core.structured_output import LogAnalysisResult, SeverityLevel
from ...cli.ui.components import (
    create_header,
    create_recommendations_list,
    display_error,
)
from ...modules.logs.analyzer import LogAnalyzer
from ...modules.logs.parser import LogFormat
from ...devops_commander.exceptions import LogParsingError

# Constantes de couleur pour styling
BOLD_RED_STYLE = "bold red"
BOLD_YELLOW_STYLE = "bold yellow"
BOLD_BLUE_STYLE = "bold blue"
DIM_BLUE_STYLE = "dim blue"

# Create the logs CLI app
logs_app = typer.Typer(
    name="logs",
    help="Analyze and manage system and application logs",
    short_help="Log analysis tools",
    invoke_without_command=True,
)

console = Console()
logger = logging.getLogger(__name__)

# Default logs command (for backward compatibility)
@logs_app.callback()
def logs_callback(
    ctx: typer.Context,
    file_path: Annotated[Optional[Path], typer.Argument(help="Path to log file to analyze")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (table, json)")] = "table",
    ai_analysis: Annotated[bool, typer.Option("--ai", "--no-ai", help="Enable AI analysis")] = True,
):
    """🔍 Analyze log files with AI insights"""
    if ctx.invoked_subcommand is None:
        if file_path is None:
            console.print("[red]Error: Missing argument 'FILE_PATH'.[/red]")
            raise typer.Exit(1)
        # Redirect to analyze command for backward compatibility
        return asyncio.run(_analyze_logs_async(file_path, format, ai_analysis))


def _validate_log_file_input(file_path: Path):
    """Validate log file input and return file size info"""
    if not file_path.exists():
        display_error(console, f"Log file not found: {file_path}")
        raise typer.Exit(code=1)

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 50:
        console.print(f"[yellow]Warning: Large log file ({file_size_mb:.1f}MB). Consider using --no-ai for faster processing.[/yellow]")

    return file_size_mb


def _initialize_log_analyzer(format: str):
    """Initialize log analyzer and format mapping"""
    format_map = {
        "auto": LogFormat.AUTO_DETECT,
        "syslog": LogFormat.SYSLOG,
        "json": LogFormat.JSON,
        "nginx": LogFormat.NGINX,
        "apache": LogFormat.APACHE,
        "docker": LogFormat.DOCKER,
        "kubernetes": LogFormat.KUBERNETES,
        "custom": LogFormat.CUSTOM,
    }

    log_format = format_map.get(format.lower(), LogFormat.AUTO_DETECT)
    analyzer = LogAnalyzer()

    return analyzer, log_format


async def _perform_log_analysis_with_fallback(analyzer, file_path: Path, log_format, ai: bool, context: Optional[str], demo_mode: bool, progress, task):
    """Perform log analysis with AI and fallback mechanisms"""
    analysis = None
    ai_used = False
    fallback_used = False

    try:
        # PRIMARY: Perform analysis with AI
        analysis = await analyzer.analyze_file(file_path=file_path, format_type=log_format, use_ai=ai, context=context)
        ai_used = ai
        progress.update(task, advance=60, description="[cyan]AI analysis completed...")

    except Exception as ai_error:
        logger.warning(f"AI analysis failed: {ai_error}")

        if ai and not demo_mode:
            console.print(f"[yellow]AI analysis failed: {ai_error}[/yellow]")
            console.print("[blue]Falling back to pattern-based analysis...[/blue]")

        progress.update(task, advance=40, description="[blue]Fallback analysis...")

        # FALLBACK: Perform analysis without AI
        analysis = await analyzer.analyze_file(file_path=file_path, format_type=log_format, use_ai=False, context=context)
        fallback_used = True
        progress.update(task, advance=60, description="[blue]Pattern analysis completed...")

    return analysis, ai_used, fallback_used


def _handle_analysis_failure(e: Exception, demo_mode: bool, file_path: Path):
    """Handle analysis failure with demo mode fallback"""
    logger.error(f"Complete analysis failure: {str(e)}")

    if demo_mode:
        console.print("[red]Analysis failed, providing basic file information...[/red]")

        try:
            from ...core.structured_output import LogAnalysisResult, SeverityLevel

            analysis = LogAnalysisResult(
                severity=SeverityLevel.INFO,
                error_count=0,
                warning_count=0,
                critical_issues=[],
                error_patterns={},
                affected_services=[],
                recommendations=[
                    f"Log file analysis failed: {str(e)}",
                    "Manual review of the log file is recommended",
                    f"File size: {file_path.stat().st_size / 1024:.1f} KB",
                ],
                root_causes=[],
                security_issues=[],
                performance_metrics={},
                incident_timeline=[],
            )
            return analysis, True

        except Exception as final_error:
            display_error(console, f"Critical error: Unable to process log file: {final_error}")
            raise typer.Exit(code=1)
    else:
        display_error(console, f"Error analyzing logs: {str(e)}")
        logger.error(f"Error analyzing logs: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


def _format_analysis_output(analysis, json_output: bool, ai_used: bool, fallback_used: bool, demo_mode: bool, file_size_mb: float, file_path: Path):
    """Format and display analysis output"""
    if json_output:
        output_data = analysis.model_dump()
        output_data["_meta"] = {
            "ai_used": ai_used,
            "fallback_used": fallback_used,
            "demo_mode": demo_mode,
            "file_size_mb": round(file_size_mb, 2),
        }
        console.print_json(json.dumps(output_data, indent=2))
    else:
        # Display status banner
        status_items = []
        if ai_used:
            status_items.append("[green]AI Analysis: ✓[/green]")
        elif fallback_used:
            status_items.append("[yellow]Fallback Mode: ✓[/yellow]")

        if demo_mode:
            status_items.append("[blue]Demo Mode: ✓[/blue]")

        if status_items:
            console.print(Panel(" | ".join(status_items), title="Analysis Status", border_style="green"))

        display_analysis_results(analysis, file_path)


@logs_app.command("analyze")
def analyze_logs(
    file_path: Annotated[Path, typer.Argument(help="Path to the log file to analyze")],
    format: Annotated[Optional[str], typer.Option(help="Log format (auto, syslog, json, nginx, apache, custom)")] = "auto",
    ai: Annotated[bool, typer.Option(help="Use AI-powered analysis for deeper insights")] = True,
    json_output: Annotated[bool, typer.Option(help="Output results in JSON format")] = False,
    context: Annotated[Optional[str], typer.Option(help="Additional context to improve analysis")] = None,
    demo_mode: Annotated[bool, typer.Option(help="Enable demo mode with enhanced reliability")] = False,
):
    """Analyze a log file for patterns, errors, and actionable insights with fallback mechanisms"""
    return asyncio.run(_analyze_logs_async(file_path, format, ai, json_output, context, demo_mode))


async def _analyze_logs_async(
    file_path: Path,
    format: str = "auto",
    ai: bool = True,
    json_output: bool = False,
    context: Optional[str] = None,
    demo_mode: bool = False,
):
    """Analyze a log file for patterns, errors, and actionable insights with fallback mechanisms"""
    file_size_mb = _validate_log_file_input(file_path)
    analyzer, log_format = _initialize_log_analyzer(format)

    analysis = None
    ai_used = False
    fallback_used = False

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing logs...", total=100)
            progress.update(task, advance=10, description="[cyan]Loading log file...")
            progress.update(task, advance=20, description="[cyan]Parsing log entries...")

            analysis, ai_used, fallback_used = await _perform_log_analysis_with_fallback(analyzer, file_path, log_format, ai, context, demo_mode, progress, task)

            progress.update(task, advance=30, description="[cyan]Preparing results...")
            progress.update(task, completed=100)

    except Exception as e:
        analysis, fallback_used = _handle_analysis_failure(e, demo_mode, file_path)

    _format_analysis_output(analysis, json_output, ai_used, fallback_used, demo_mode, file_size_mb, file_path)
    return analysis


def _setup_log_parser(format: str):
    """Setup log parser and format mapping"""
    format_map = {
        "auto": LogFormat.AUTO_DETECT,
        "syslog": LogFormat.SYSLOG,
        "json": LogFormat.JSON,
        "nginx": LogFormat.NGINX,
        "apache": LogFormat.APACHE,
        "docker": LogFormat.DOCKER,
        "kubernetes": LogFormat.KUBERNETES,
        "custom": LogFormat.CUSTOM,
    }

    log_format = format_map.get(format.lower(), LogFormat.AUTO_DETECT)

    from ...modules.logs.parser import LogParser

    parser = LogParser()

    return parser, log_format


def _process_parsed_entries(entries, limit: Optional[int]):
    """Process parsed entries and apply limit if specified"""
    if limit and limit > 0:
        entries = entries[:limit]
    return entries


def _display_parse_results(entries, parser, json_output: bool):
    """Display parsing results in table or JSON format"""
    if json_output:
        import json

        entry_dicts = [entry.model_dump() for entry in entries]
        console.print_json(json.dumps(entry_dicts))
        return

    # Create a table for the parsed logs
    table = Table(title=f"Parsed Log Entries ({len(entries)} entries)")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Source", style="green")
    table.add_column("Message", style="white")

    for entry in entries:
        timestamp = str(entry.timestamp) if entry.timestamp else "N/A"
        level = entry.level or "N/A"
        source = entry.source or "N/A"
        message = entry.message or "N/A"

        # Color level based on severity
        level_style = {
            "ERROR": BOLD_RED_STYLE,
            "CRITICAL": BOLD_RED_STYLE,
            "FATAL": BOLD_RED_STYLE,
            "WARNING": BOLD_YELLOW_STYLE,
            "INFO": "blue",
            "DEBUG": DIM_BLUE_STYLE,
        }.get(level, "white")

        table.add_row(
            timestamp,
            f"[{level_style}]{level}[/{level_style}]",
            source,
            message[:100] + ("..." if len(message) > 100 else ""),
        )

    console.print(table)

    # Print parse stats
    console.print(
        Panel(
            f"Detected Format: [bold]{parser.last_detected_format.value}[/bold]\n"
            f"Total Entries: [bold]{len(entries)}[/bold]\n"
            f"Successfully Parsed: [green]{parser.last_parse_stats.get('success', 0)}[/green]\n"
            f"Failed to Parse: [red]{parser.last_parse_stats.get('failed', 0)}[/red]",
            title="Parse Statistics",
            border_style="blue",
        )
    )


@logs_app.command("parse")
def parse_logs(
    file_path: Annotated[Path, typer.Argument(help="Path to the log file to parse")],
    format: Annotated[Optional[str], typer.Option(help="Log format (auto, syslog, json, nginx, apache, custom)")] = "auto",
    limit: Annotated[Optional[int], typer.Option(help="Limit the number of parsed entries")] = 10,
    json_output: Annotated[bool, typer.Option(help="Output results in JSON format")] = False,
):
    """Parse and display log entries in a structured format"""
    try:
        parser, log_format = _setup_log_parser(format)

        with Progress() as progress:
            task = progress.add_task("[cyan]Parsing logs...", total=100)
            progress.update(task, advance=20)

            entries = parser.parse_file(file_path, log_format)
            progress.update(task, completed=100)

        entries = _process_parsed_entries(entries, limit)
        _display_parse_results(entries, parser, json_output)

        return entries

    except LogParsingError as e:
        display_error(console, f"Log parsing error: {str(e)}")
        logger.error(f"Log parsing error: {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        display_error(console, f"Error parsing logs: {str(e)}")
        logger.error(f"Error parsing logs: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


@logs_app.command("monitor")
def monitor_logs_sync(
    file_path: Annotated[Path, typer.Argument(help="Path to the log file to monitor")],
    interval: Annotated[int, typer.Option(help="Polling interval in seconds")] = 5,
    format: Annotated[Optional[str], typer.Option(help="Log format (auto, syslog, json, nginx, apache, custom)")] = "auto",
):
    """
    Monitor a log file in real-time for new entries and issues
    """
    asyncio.run(_async_monitor_logs(file_path, interval, format))


def _setup_log_monitoring(file_path: Path, interval: int, format: str):
    """Setup log monitoring configuration and display initial info"""
    format_map = {
        "auto": LogFormat.AUTO_DETECT,
        "syslog": LogFormat.SYSLOG,
        "json": LogFormat.JSON,
        "nginx": LogFormat.NGINX,
        "apache": LogFormat.APACHE,
        "docker": LogFormat.DOCKER,
        "kubernetes": LogFormat.KUBERNETES,
        "custom": LogFormat.CUSTOM,
    }

    log_format = format_map.get(format.lower(), LogFormat.AUTO_DETECT)

    console.print(
        Panel(
            f"Monitoring: [bold]{file_path}[/bold]\nInterval: [cyan]{interval}[/cyan] seconds\nFormat: [yellow]{format}[/yellow]\n\nPress [bold red]Ctrl+C[/bold red] to stop monitoring.",
            title="📊 Log Monitor Started",
            border_style="green",
        )
    )

    return log_format


async def _check_file_changes(file_path: Path, file_position: int):
    """Check for file changes and return new content if available"""
    if not file_path.exists():
        console.print("[yellow]Waiting for log file to be created...[/yellow]")
        return None, file_position

    current_size = file_path.stat().st_size

    if current_size > file_position:
        async with aiofiles.open(file_path, "r") as file:
            await file.seek(file_position)
            new_content = await file.read()
            return new_content, current_size

    return None, file_position


def _process_new_log_entries(entries):
    """Process and display new log entries"""
    if not entries:
        return

    table = Table(title=f"New Log Entries ({len(entries)} entries)")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Message", style="white")

    for entry in entries[:5]:  # Limit to most recent 5
        timestamp = str(entry.timestamp) if entry.timestamp else "N/A"
        level = entry.level or "N/A"

        # Color level based on severity
        level_style = {
            "ERROR": BOLD_RED_STYLE,
            "CRITICAL": BOLD_RED_STYLE,
            "FATAL": BOLD_RED_STYLE,
            "WARNING": BOLD_YELLOW_STYLE,
            "INFO": "blue",
            "DEBUG": DIM_BLUE_STYLE,
        }.get(level, "white")

        table.add_row(
            timestamp,
            f"[{level_style}]{level}[/{level_style}]",
            entry.message[:100] + ("..." if len(entry.message) > 100 else ""),
        )

    console.print(table)


def _display_monitoring_alerts(entries):
    """Display alerts for errors and warnings found in entries"""
    error_entries = [e for e in entries if e.level and e.level.upper() in ["ERROR", "CRITICAL", "FATAL"]]
    warning_entries = [e for e in entries if e.level and e.level.upper() == "WARNING"]

    if error_entries or warning_entries:
        console.print(
            Panel(
                f"[bold red]Alert![/bold red] Found {len(error_entries)} errors and {len(warning_entries)} warnings in new entries.",
                title="⚠️ Issues Detected",
                border_style="red",
            )
        )

        # Show latest errors
        if error_entries:
            for error in error_entries[:3]:  # Show first 3 errors
                console.print(f"[red]• {error.message}[/red]")


def _cleanup_monitoring():
    """Cleanup monitoring resources and display exit message"""
    console.print("\n[yellow]📊 Log monitoring stopped.[/yellow]")


async def _async_monitor_logs(file_path: Path, interval: int, format: str):
    """Async implementation of log monitoring"""
    try:
        log_format = _setup_log_monitoring(file_path, interval, format)

        from ...modules.logs.parser import LogParser

        parser = LogParser()

        # Track file position
        file_position = 0
        if file_path.exists():
            file_position = file_path.stat().st_size

        # Event loop for monitoring
        try:
            while True:
                try:
                    new_content, file_position = await _check_file_changes(file_path, file_position)

                    if new_content:
                        entries = parser.parse_text(new_content, log_format)

                        if entries:
                            _process_new_log_entries(entries)
                            _display_monitoring_alerts(entries)

                    await asyncio.sleep(interval)

                except Exception as e:
                    console.print(f"[red]Error during monitoring: {str(e)}[/red]")
                    await asyncio.sleep(interval)

        except KeyboardInterrupt:
            _cleanup_monitoring()

    except Exception as e:
        display_error(console, f"Error monitoring logs: {str(e)}")
        logger.error(f"Error monitoring logs: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


@logs_app.command("summarize")
def summarize_logs(
    file_path: Annotated[Path, typer.Argument(help="Path to the log file to summarize")],
    format: Annotated[Optional[str], typer.Option(help="Log format (auto, syslog, json, nginx, apache, custom)")] = "auto",
    brief: Annotated[bool, typer.Option(help="Generate a brief summary")] = False,
    json_output: Annotated[bool, typer.Option(help="Output results in JSON format")] = False,
):
    """
    Generate a concise summary of log events and issues
    """
    return asyncio.run(_summarize_logs_async(file_path, format, brief, json_output))


async def _summarize_logs_async(
    file_path: Path,
    format: str,
    brief: bool,
    json_output: bool,
):
    try:
        # Map format string to LogFormat enum
        format_map = {
            "auto": LogFormat.AUTO_DETECT,
            "syslog": LogFormat.SYSLOG,
            "json": LogFormat.JSON,
            "nginx": LogFormat.NGINX,
            "apache": LogFormat.APACHE,
            "docker": LogFormat.DOCKER,
            "kubernetes": LogFormat.KUBERNETES,
            "custom": LogFormat.CUSTOM,
        }

        log_format = format_map.get(format.lower(), LogFormat.AUTO_DETECT)

        with Progress() as progress:
            task = progress.add_task("[cyan]Summarizing logs...", total=100)

            # Initialize analyzer
            analyzer = LogAnalyzer()

            # Parse and analyze log file
            progress.update(task, advance=30, description="[cyan]Analyzing log file...")
            analysis = await analyzer.analyze_file(file_path=file_path, format_type=log_format, use_ai=True)

            # Complete progress
            progress.update(task, completed=100)

        # Output results
        if json_output:
            console.print_json(analysis.model_dump_json())
        else:
            if brief:
                # Brief summary
                summary = analyzer.get_analysis_summary(analysis)
                console.print(Panel(summary, title=f"Log Summary: {file_path.name}", border_style="blue"))

                # Brief recommendations
                if analysis.recommendations:
                    console.print(create_recommendations_list(analysis.recommendations[:3] if len(analysis.recommendations) > 3 else analysis.recommendations))
            else:
                # Full summary display
                display_analysis_results(analysis, file_path)

        return analysis

    except Exception as e:
        display_error(console, f"Error summarizing logs: {str(e)}")
        logger.error(f"Error summarizing logs: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


def _initialize_anomaly_detection(format: str):
    """Initialize anomaly detection components"""
    format_map = {
        "auto": LogFormat.AUTO_DETECT,
        "syslog": LogFormat.SYSLOG,
        "json": LogFormat.JSON,
        "nginx": LogFormat.NGINX,
        "apache": LogFormat.APACHE,
        "docker": LogFormat.DOCKER,
        "kubernetes": LogFormat.KUBERNETES,
        "custom": LogFormat.CUSTOM,
    }
    return format_map.get(format.lower(), LogFormat.AUTO_DETECT)


def _parse_logs_for_anomalies(file_path: Path, log_format):
    """Parse logs and return entries with progress tracking"""
    with Progress() as progress:
        task = progress.add_task("[cyan]Detecting anomalies...", total=100)

        from ...modules.logs.parser import LogParser

        parser = LogParser()

        progress.update(task, advance=40, description="[cyan]Parsing log file...")
        entries = parser.parse_file(file_path, log_format)

        progress.update(task, completed=100)

    return entries, parser


def _analyze_anomaly_patterns(entries, threshold):
    """Analyze entries for anomaly patterns"""
    analyzer = LogAnalyzer()
    return analyzer.identify_anomalies(entries, threshold)


def _format_anomaly_results(anomalies, file_path: Path, json_output: bool):
    """Format and display anomaly detection results"""
    if json_output:
        import json

        console.print_json(json.dumps(anomalies))
        return

    console.print(create_header("Anomaly Detection Results"))
    console.print(
        Panel(
            "Anomaly Detection Results",
            title=f"File: {file_path.name}",
            border_style="blue",
        )
    )

    if not anomalies:
        console.print(
            Panel(
                "No significant anomalies detected in the log file.",
                title="Analysis Results",
                border_style="green",
            )
        )
        return

    _display_anomaly_details(anomalies)


def _display_anomaly_details(anomalies):
    """Display detailed anomaly information by type"""
    # Group anomalies by type
    anomaly_types = {}
    for anomaly in anomalies:
        anomaly_type = anomaly.get("type", "unknown")
        if anomaly_type not in anomaly_types:
            anomaly_types[anomaly_type] = []
        anomaly_types[anomaly_type].append(anomaly)

    console.print(f"Detected [bold red]{len(anomalies)}[/bold red] anomalies:")

    for anomaly_type, type_anomalies in anomaly_types.items():
        if anomaly_type == "high_activity":
            _display_high_activity_anomalies(type_anomalies)
        elif anomaly_type == "error_burst":
            _display_error_burst_anomalies(type_anomalies)
        else:
            _display_generic_anomalies(anomaly_type, type_anomalies)


def _display_high_activity_anomalies(type_anomalies):
    """Display high activity period anomalies"""
    table = Table(title=f"High Activity Periods ({len(type_anomalies)} detected)")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Count", style="yellow")
    table.add_column("Average", style="blue")
    table.add_column("Deviation", style="magenta")

    for anomaly in type_anomalies:
        table.add_row(
            anomaly.get("timestamp", "unknown"),
            str(anomaly.get("count", "N/A")),
            str(anomaly.get("average", "N/A")),
            f"{anomaly.get('deviation', 'N/A')}σ",
        )

    console.print(table)


def _display_error_burst_anomalies(type_anomalies):
    """Display error burst anomalies"""
    table = Table(title=f"Error Bursts ({len(type_anomalies)} detected)")
    table.add_column("Start Time", style="cyan")
    table.add_column("End Time", style="cyan")
    table.add_column("Error Count", style="red")
    table.add_column("Time Span", style="yellow")

    for anomaly in type_anomalies:
        table.add_row(
            anomaly.get("start_time", "unknown"),
            anomaly.get("end_time", "unknown"),
            str(anomaly.get("error_count", "N/A")),
            f"{anomaly.get('time_span_seconds', 'N/A')} seconds",
        )

    console.print(table)


def _display_generic_anomalies(anomaly_type, type_anomalies):
    """Display generic anomaly types"""
    console.print(
        Panel(
            f"{len(type_anomalies)} anomalies of type '{anomaly_type}' detected",
            title=f"Anomaly Type: {anomaly_type.replace('_', ' ').title()}",
            border_style="yellow",
        )
    )


@logs_app.command("anomalies")
def detect_anomalies(
    file_path: Annotated[Path, typer.Argument(help="Path to the log file to analyze")],
    format: Annotated[Optional[str], typer.Option(help="Log format (auto, syslog, json, nginx, apache, custom)")] = "auto",
    threshold: Annotated[float, typer.Option(help="Sensitivity threshold for anomaly detection")] = 2.0,
    json_output: Annotated[bool, typer.Option(help="Output results in JSON format")] = False,
):
    """Detect anomalies and unusual patterns in log files"""
    return _detect_anomalies_async(file_path, format, threshold, json_output)


def _detect_anomalies_async(
    file_path: Path,
    format: str, 
    threshold: float,
    json_output: bool,
):
    try:
        log_format = _initialize_anomaly_detection(format)
        entries, _ = _parse_logs_for_anomalies(file_path, log_format)
        anomalies = _analyze_anomaly_patterns(entries, threshold)
        _format_anomaly_results(anomalies, file_path, json_output)

        return anomalies

    except Exception as e:
        display_error(console, f"Error detecting anomalies: {str(e)}")
        logger.error(f"Error detecting anomalies: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)


def _display_analysis_header(analysis: LogAnalysisResult, file_path: Path):
    """Display analysis header with severity information"""
    severity_colors = {
        SeverityLevel.CRITICAL: BOLD_RED_STYLE,
        SeverityLevel.ERROR: "red",
        SeverityLevel.MEDIUM: "yellow",
        SeverityLevel.WARNING: "blue",
        SeverityLevel.INFO: "green",
    }
    severity_color = severity_colors.get(analysis.severity, "white")

    console.print(create_header("Log Analysis Results"))
    console.print(
        Panel(
            f"Log Analysis Results: [{severity_color}]{analysis.severity.value.upper()}[/{severity_color}]",
            title=f"File: {file_path.name}",
            border_style="blue",
        )
    )


def _display_issues_summary(analysis: LogAnalysisResult):
    """Display summary of issues found in analysis"""
    status_items = [
        f"Errors: [bold red]{analysis.error_count}[/bold red]",
        f"Warnings: [bold yellow]{analysis.warning_count}[/bold yellow]",
    ]
    if analysis.critical_issues:
        status_items.append(f"Critical Issues: [bold red]{len(analysis.critical_issues)}[/bold red]")
    if analysis.security_issues:
        status_items.append(f"Security Concerns: [bold red]{len(analysis.security_issues)}[/bold red]")
    if analysis.affected_services:
        status_items.append(f"Affected Services: [bold]{len(analysis.affected_services)}[/bold]")

    console.print(Panel("\n".join(status_items), title="📊 Analysis Summary", border_style="blue"))

    # Display critical issues if any
    if analysis.critical_issues:
        console.print(
            Panel(
                "\n".join(f"• [bold red]{issue}[/bold red]" for issue in analysis.critical_issues),
                title="Critical Issues",
                border_style="red",
            )
        )


def _display_error_patterns(analysis: LogAnalysisResult):
    """Display detected error patterns in table format"""
    if not analysis.error_patterns:
        return

    error_table = Table(title="Detected Error Patterns")
    error_table.add_column("Pattern", style="magenta")
    error_table.add_column("Count", style="cyan", justify="right")

    for pattern, count in analysis.error_patterns.items():
        pattern_name = pattern.replace("_", " ").title()
        error_table.add_row(pattern_name, str(count))

    console.print(error_table)


def _display_recommendations(analysis: LogAnalysisResult):
    """Display analysis recommendations"""
    if analysis.recommendations:
        console.print(create_recommendations_list(analysis.recommendations))


def _display_performance_metrics(analysis: LogAnalysisResult):
    """Display performance metrics and additional analysis data"""
    # Display root causes if available
    if analysis.root_causes:
        console.print(
            Panel(
                "\n".join(f"• {cause}" for cause in analysis.root_causes),
                title="Root Causes",
                border_style="yellow",
            )
        )

    # Display affected services
    if analysis.affected_services:
        services_tree = Tree("Affected Services")
        for service in analysis.affected_services:
            services_tree.add(f"[bold]{service}[/bold]")
        console.print(services_tree)

    # Display performance metrics if available
    if analysis.performance_metrics:
        metrics_panel = Panel(
            "\n".join(f"• {key.replace('_', ' ').title()}: {value}" for key, value in analysis.performance_metrics.items() if not isinstance(value, dict)),
            title="Performance Metrics",
            border_style="blue",
        )
        console.print(metrics_panel)

    # Display incident timeline if available
    if analysis.incident_timeline:
        timeline_table = Table(title="Incident Timeline")
        timeline_table.add_column("Time", style="cyan")
        timeline_table.add_column("Event", style="white")

        for event in analysis.incident_timeline:
            if isinstance(event, dict):
                time = event.get("timestamp", "N/A")
                description = event.get("event", "Unknown event")
                timeline_table.add_row(time, description)
            elif isinstance(event, str):
                timeline_table.add_row("N/A", event)

        console.print(timeline_table)


def display_analysis_results(analysis: LogAnalysisResult, file_path: Path):
    """Display formatted analysis results"""
    _display_analysis_header(analysis, file_path)
    _display_issues_summary(analysis)
    _display_error_patterns(analysis)
    _display_recommendations(analysis)
    _display_performance_metrics(analysis)
