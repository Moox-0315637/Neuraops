"""NeuraOps Demo CLI Application

Typer app for demonstration scenarios
"""

import typer
from typing import Optional
from .demo import (
    demo_list_command,
    demo_show_command,
    demo_run_command,
    demo_quick_command,
    demo_create_command,
    demo_interactive_command,
    demo_export_command,
)

# Constants for help messages to avoid duplication (SonarQube python:S1192)
OUTPUT_FORMAT_TABLE_JSON_HELP = "Output format (table, json)"
OUTPUT_FORMAT_JSON_TEXT_HELP = "Output format (json, text)"
OUTPUT_FORMAT_TEXT_JSON_HELP = "Output format (text, json)"
EXPORT_FORMAT_MARKDOWN_JSON_HELP = "Export format (markdown, json)"

# Create demo typer app
demo_app = typer.Typer(
    name="demo",
    help="🎬 Run comprehensive demonstration scenarios showcasing NeuraOps capabilities",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@demo_app.command("list", help="📋 List all available demo scenarios")
def list_demos(
    output_format: str = typer.Option("table", "--format", "-f", help=OUTPUT_FORMAT_TABLE_JSON_HELP),
    complexity: Optional[str] = typer.Option(None, "--complexity", "-c", help="Filter by complexity level"),
    duration_max: Optional[int] = typer.Option(None, "--max-duration", "-d", help="Maximum duration in minutes"),
):
    """List all available demo scenarios with filtering options"""
    return demo_list_command(output_format, complexity, duration_max)


@demo_app.command("show", help="🔍 Show detailed information about a demo scenario")
def show_demo(
    scenario_id: str = typer.Argument(..., help="ID of the demo scenario to show"),
    output_format: str = typer.Option("json", "--format", "-f", help=OUTPUT_FORMAT_JSON_TEXT_HELP),
):
    """Show detailed information about a specific demo scenario"""
    return demo_show_command(scenario_id, output_format)


@demo_app.command("run", help="▶️ Run a demo scenario interactively")
def run_demo(
    scenario_id: str = typer.Argument(..., help="ID of the demo scenario to run"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Run in interactive mode"),
    output_format: str = typer.Option("text", "--format", "-f", help=OUTPUT_FORMAT_TEXT_JSON_HELP),
    save_results: Optional[str] = typer.Option(None, "--save", "-s", help="Save results to file"),
):
    """Run a demo scenario with full interaction and guidance"""
    return demo_run_command(scenario_id, interactive, output_format, save_results)


@demo_app.command("quick", help="⚡ Run a quick non-interactive demo")
def quick_demo(
    demo_type: str = typer.Option("incident_response", "--type", "-t", help="Type of quick demo to run"),
    output_format: str = typer.Option("text", "--format", "-f", help=OUTPUT_FORMAT_TEXT_JSON_HELP),
):
    """Run a quick demonstration without user interaction"""
    return demo_quick_command(demo_type, output_format)


@demo_app.command("create", help="🛠️ Create a custom demo scenario")
def create_demo(
    name: str = typer.Argument(..., help="Name of the custom demo"),
    description: str = typer.Argument(..., help="Description of the demo"),
    steps_file: str = typer.Argument(..., help="JSON file containing demo steps"),
    output_format: str = typer.Option("text", "--format", "-f", help=OUTPUT_FORMAT_TEXT_JSON_HELP),
):
    """Create a custom demo scenario from a JSON steps file"""
    return demo_create_command(name, description, steps_file, output_format)


@demo_app.command("interactive", help="🎮 Run interactive demo with full guidance")
def interactive_demo(
    demo_type: str = typer.Option("ai_assistant_showcase", "--type", "-t", help="Type of interactive demo"),
    save_results: Optional[str] = typer.Option(None, "--save", "-s", help="Save results to file"),
):
    """Run an interactive demo with step-by-step guidance"""
    return demo_interactive_command(demo_type, save_results)


@demo_app.command("export", help="📤 Export demo scenario as documentation")
def export_demo(
    scenario_id: str = typer.Argument(..., help="ID of the demo scenario to export"),
    output_file: str = typer.Argument(..., help="Output file path"),
    format_type: str = typer.Option("markdown", "--format", "-f", help=EXPORT_FORMAT_MARKDOWN_JSON_HELP),
):
    """Export a demo scenario as documentation"""
    return demo_export_command(scenario_id, output_file, format_type)
