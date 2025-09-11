"""
NeuraOps Workflow CLI Application
Typer app for AI-powered automation workflows
"""

import typer
from typing import Optional

from .workflows import (
    workflow_list_command,
    workflow_show_command,
    workflow_execute_command,
    workflow_create_command,
    workflow_stats_command,
    workflow_optimize_command,
    workflow_templates_command,
    workflow_create_template_command,
)

# Help text constants
WORKFLOW_ID_HELP = "Workflow ID"
OUTPUT_FORMAT_JSON_TEXT_HELP = "Output format (json, text)"
OUTPUT_FORMAT_TEXT_JSON_HELP = "Output format (text, json)"
OUTPUT_FORMAT_TABLE_JSON_HELP = "Output format (table, json)"

# Create workflow typer app
workflow_app = typer.Typer(
    name="workflow",
    help="🔄 Manage AI-powered automation workflows with decision trees and adaptive learning",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@workflow_app.command("list", help="📋 List all registered workflows")
def list_workflows(
    output_format: str = typer.Option("table", "--format", "-f", help=OUTPUT_FORMAT_TABLE_JSON_HELP),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by execution status"),
):
    """List all registered workflows"""
    return workflow_list_command(output_format, status)


@workflow_app.command("show", help="🔍 Show detailed information about a workflow")
def show_workflow(
    workflow_id: str = typer.Argument(..., help=WORKFLOW_ID_HELP),
    output_format: str = typer.Option("json", "--format", "-f", help=OUTPUT_FORMAT_JSON_TEXT_HELP),
):
    """Show detailed information about a workflow"""
    return workflow_show_command(workflow_id, output_format)


@workflow_app.command("execute", help="▶️  Execute a workflow")
def execute_workflow(
    workflow_id: str = typer.Argument(..., help="Workflow ID to execute"),
    context_file: Optional[str] = typer.Option(None, "--context", "-c", help="JSON file with execution context"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Perform dry run without executing actions"),
    output_format: str = typer.Option("text", "--format", "-f", help=OUTPUT_FORMAT_TEXT_JSON_HELP),
    save_results: Optional[str] = typer.Option(None, "--save", "-s", help="Save execution results to file"),
):
    """Execute a workflow with optional context"""
    return workflow_execute_command(workflow_id, context_file, dry_run, output_format, save_results)


@workflow_app.command("create", help="🎨 Create a new workflow from definition file")
def create_workflow(
    name: str = typer.Option(..., "--name", "-n", help="Workflow name"),
    description: str = typer.Option(..., "--description", "-d", help="Workflow description"),
    workflow_file: str = typer.Option(..., "--file", "-f", help="JSON file with workflow definition"),
    output_format: str = typer.Option("text", "--format", help=OUTPUT_FORMAT_TEXT_JSON_HELP),
):
    """Create a new workflow from definition file"""
    return workflow_create_command(name, description, workflow_file, output_format)


@workflow_app.command("stats", help="📊 Show workflow execution statistics")
def workflow_stats(
    workflow_id: str = typer.Argument(..., help=WORKFLOW_ID_HELP),
    output_format: str = typer.Option("json", "--format", "-f", help=OUTPUT_FORMAT_JSON_TEXT_HELP),
):
    """Show workflow execution statistics and performance metrics"""
    return workflow_stats_command(workflow_id, output_format)


@workflow_app.command("optimize", help="🎯 Optimize workflow based on execution history")
def optimize_workflow(
    workflow_id: str = typer.Argument(..., help=WORKFLOW_ID_HELP),
    output_format: str = typer.Option("json", "--format", "-f", help=OUTPUT_FORMAT_JSON_TEXT_HELP),
):
    """Optimize workflow based on execution history and learning data"""
    return workflow_optimize_command(workflow_id, output_format)


@workflow_app.command("templates", help="📝 List available workflow templates")
def list_templates(output_format: str = typer.Option("table", "--format", "-f", help=OUTPUT_FORMAT_TABLE_JSON_HELP)):
    """List available pre-built workflow templates"""
    return workflow_templates_command(output_format)


@workflow_app.command("create-template", help="⚡ Create workflow from template")
def create_from_template(
    template_id: str = typer.Argument(..., help="Template ID (incident_response, performance_optimization, security_audit)"),
    workflow_id: Optional[str] = typer.Option(None, "--id", help="Custom workflow ID (optional)"),
    output_format: str = typer.Option("text", "--format", "-f", help=OUTPUT_FORMAT_TEXT_JSON_HELP),
):
    """Create a workflow from a pre-built template"""
    return workflow_create_template_command(template_id, workflow_id, output_format)
