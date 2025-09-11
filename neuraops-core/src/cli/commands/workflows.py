"""
NeuraOps Workflow Management CLI Commands
CLI commands for managing AI-powered automation workflows
"""

import asyncio
import json
import sys
from typing import Optional

import aiofiles

from ...cli.utils.decorators import handle_exceptions
from ...cli.ui.components import format_table
from ...modules.ai.workflows import (
    WorkflowOrchestrator,
    WorkflowBuilder,
    WorkflowCondition,
    ConditionOperator,
    create_workflow_orchestrator,
    create_incident_response_workflow,
    create_performance_optimization_workflow,
    create_security_audit_workflow,
)


def _collect_workflow_info(orchestrator):
    """Collect workflow information from orchestrator"""
    workflows = []
    for workflow_id, workflow in orchestrator.workflows.items():
        workflow_info = {
            "id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "actions": len(workflow.actions),
            "decisions": len(workflow.decision_nodes),
            "timeout": (f"{workflow.timeout_minutes} min" if workflow.timeout_minutes else "None"),
            "learning": "Enabled" if workflow.learning_enabled else "Disabled",
        }
        workflows.append(workflow_info)
    return workflows


def _display_workflows_json(workflows):
    """Display workflows in JSON format"""
    print(json.dumps(workflows, indent=2))


def _build_workflow_table_data(workflows):
    """Build table data for workflow display"""
    table_data = []
    for workflow in workflows:
        table_data.append(
            [
                workflow["id"],
                workflow["name"],
                workflow["actions"],
                workflow["decisions"],
                workflow["timeout"],
                workflow["learning"],
                (workflow["description"][:40] + "..." if len(workflow["description"]) > 40 else workflow["description"]),
            ]
        )
    return table_data


def _display_workflows_table(workflows):
    """Display workflows in table format"""
    if not workflows:
        print("No workflows registered.")
        return

    table_data = _build_workflow_table_data(workflows)
    headers = ["ID", "Name", "Actions", "Decisions", "Timeout", "Learning", "Description"]
    print(format_table(table_data, headers))
    print(f"\nTotal workflows: {len(workflows)}")


@handle_exceptions
def workflow_list_command(output_format: str = "table", status: Optional[str] = None) -> int:
    """List all registered workflows"""

    async def list_workflows_async():
        try:
            orchestrator = await create_workflow_orchestrator()
            workflows = _collect_workflow_info(orchestrator)

            if output_format == "json":
                _display_workflows_json(workflows)
            else:
                _display_workflows_table(workflows)

            return 0

        except Exception as e:
            print(f"Error listing workflows: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(list_workflows_async())


def _build_workflow_details(workflow):
    """Build detailed workflow information structure"""
    return {
        "workflow": {
            "id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "entry_point": workflow.entry_point,
            "timeout_minutes": workflow.timeout_minutes,
            "max_retries": workflow.max_retries,
            "rollback_strategy": workflow.rollback_strategy,
            "learning_enabled": workflow.learning_enabled,
        },
        "actions": [
            {
                "id": action.action_id,
                "name": action.name,
                "type": action.action_type.value,
                "description": action.description,
                "parameters": action.parameters,
                "conditions": len(action.conditions),
                "dependencies": action.dependencies,
                "timeout": action.timeout_seconds,
            }
            for action in workflow.actions
        ],
        "decision_nodes": [
            {
                "id": node.node_id,
                "name": node.name,
                "description": node.description,
                "conditions": len(node.conditions),
                "true_path": node.true_path,
                "false_path": node.false_path,
            }
            for node in workflow.decision_nodes
        ],
    }


def _display_workflow_json(workflow_details):
    """Display workflow details in JSON format"""
    print(json.dumps(workflow_details, indent=2))


def _display_workflow_header(workflow):
    """Display workflow header information"""
    print(f"Workflow: {workflow.name}")
    print("=" * (len(workflow.name) + 10))
    print(f"ID: {workflow.workflow_id}")
    print(f"Description: {workflow.description}")
    print(f"Version: {workflow.version}")
    print(f"Entry Point: {workflow.entry_point}")
    print(f"Timeout: {workflow.timeout_minutes} minutes" if workflow.timeout_minutes else "No timeout")
    print(f"Learning: {'Enabled' if workflow.learning_enabled else 'Disabled'}")
    print()


def _display_workflow_actions(workflow):
    """Display workflow actions"""
    print(f"Actions ({len(workflow.actions)}):")
    print("-" * 20)
    for action in workflow.actions:
        print(f"  {action.action_id}: {action.name} ({action.action_type.value})")
        print(f"    {action.description}")
        if action.dependencies:
            print(f"    Dependencies: {', '.join(action.dependencies)}")
        print()


def _display_workflow_decisions(workflow):
    """Display workflow decision nodes"""
    if workflow.decision_nodes:
        print(f"Decision Nodes ({len(workflow.decision_nodes)}):")
        print("-" * 25)
        for node in workflow.decision_nodes:
            print(f"  {node.node_id}: {node.name}")
            print(f"    True path: {', '.join(node.true_path)}")
            print(f"    False path: {', '.join(node.false_path)}")
            print()


@handle_exceptions
def workflow_show_command(workflow_id: str, output_format: str = "json") -> int:
    """Show detailed information about a workflow"""

    async def show_workflow_async():
        try:
            orchestrator = await create_workflow_orchestrator()

            if workflow_id not in orchestrator.workflows:
                print(f"Workflow '{workflow_id}' not found", file=sys.stderr)
                return 1

            workflow = orchestrator.workflows[workflow_id]
            workflow_details = _build_workflow_details(workflow)

            if output_format == "json":
                _display_workflow_json(workflow_details)
            else:
                _display_workflow_header(workflow)
                _display_workflow_actions(workflow)
                _display_workflow_decisions(workflow)

            return 0

        except Exception as e:
            print(f"Error showing workflow: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(show_workflow_async())


async def _load_workflow_context(context_file):
    """Load workflow context from file"""
    if not context_file:
        return {}

    try:
        async with aiofiles.open(context_file, "r") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        print(f"Error loading context file: {str(e)}", file=sys.stderr)
        raise


async def _execute_workflow_with_orchestrator(orchestrator, workflow_id, context, dry_run):
    """Execute workflow with orchestrator"""
    workflow = orchestrator.workflows[workflow_id]
    print(f"{'[DRY RUN] ' if dry_run else ''}Executing workflow: {workflow.name}")
    if context:
        print("Using context from file")

    return await orchestrator.execute_workflow(workflow_id=workflow_id, context=context, dry_run=dry_run)


def _build_execution_data(execution):
    """Build execution data structure"""
    return {
        "execution_id": execution.execution_id,
        "workflow_id": execution.workflow_id,
        "status": execution.status.value,
        "start_time": execution.start_time.isoformat(),
        "end_time": execution.end_time.isoformat() if execution.end_time else None,
        "duration_seconds": (execution.duration.total_seconds() if execution.duration else None),
        "completed_actions": execution.completed_actions,
        "failed_actions": execution.failed_actions,
        "error_messages": execution.error_messages,
        "rollback_performed": execution.rollback_performed,
        "results": execution.results,
    }


def _display_execution_results_json(execution):
    """Display execution results in JSON format"""
    execution_data = _build_execution_data(execution)
    print(json.dumps(execution_data, indent=2))


def _display_execution_results_text(execution):
    """Display execution results in text format"""
    print("\nWorkflow Execution Results:")
    print(f"Execution ID: {execution.execution_id}")
    print(f"Status: {execution.status.value.upper()}")
    print(f"Duration: {execution.duration.total_seconds():.1f} seconds" if execution.duration else "N/A")
    print(f"Actions completed: {len(execution.completed_actions)}")
    print(f"Actions failed: {len(execution.failed_actions)}")

    if execution.error_messages:
        print("\nErrors:")
        for error in execution.error_messages:
            print(f"  • {error}")

    if execution.rollback_performed:
        print("\n⚠️  Rollback was performed due to failures")


def _display_dry_run_actions(execution):
    """Display actions that would be executed in dry run"""
    if "actions_to_execute" in execution.results:
        print(f"\nActions that would be executed ({len(execution.results['actions_to_execute'])}):")
        for action in execution.results["actions_to_execute"]:
            print(f"  • {action['name']} ({action['type']})")


async def _save_execution_results(execution, save_results):
    """Save execution results to file"""
    execution_data = {
        **_build_execution_data(execution),
        "context": execution.context,
    }

    async with aiofiles.open(save_results, "w") as f:
        await f.write(json.dumps(execution_data, indent=2))
    print(f"\nResults saved to: {save_results}")


@handle_exceptions
def workflow_execute_command(
    workflow_id: str,
    context_file: Optional[str] = None,
    dry_run: bool = False,
    output_format: str = "text",
    save_results: Optional[str] = None,
) -> int:
    """Execute a workflow"""

    async def execute_workflow_async():
        try:
            orchestrator = await create_workflow_orchestrator()

            if workflow_id not in orchestrator.workflows:
                print(f"Workflow '{workflow_id}' not found", file=sys.stderr)
                return 1

            # Load context and execute workflow
            context = await _load_workflow_context(context_file)
            execution = await _execute_workflow_with_orchestrator(orchestrator, workflow_id, context, dry_run)

            # Display results
            if output_format == "json":
                _display_execution_results_json(execution)
            else:
                _display_execution_results_text(execution)
                if dry_run:
                    _display_dry_run_actions(execution)

            # Save results if requested
            if save_results:
                await _save_execution_results(execution, save_results)

            return 0 if execution.status.value in ["completed", "pending"] else 1

        except Exception as e:
            print(f"Error executing workflow: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(execute_workflow_async())


async def _load_workflow_definition(workflow_file):
    """Load workflow definition from file"""
    async with aiofiles.open(workflow_file, "r") as f:
        content = await f.read()
        return json.loads(content)


def _build_workflow_actions(builder, workflow_def):
    """Build workflow actions from definition"""
    for action_def in workflow_def.get("actions", []):
        action_type = action_def["type"]

        if action_type == "command":
            builder.add_command_action(
                action_id=action_def["id"],
                name=action_def["name"],
                command=action_def["command"],
                description=action_def.get("description", ""),
                safety_level=action_def.get("safety_level", "MEDIUM"),
                timeout=action_def.get("timeout"),
            )
        elif action_type == "ai_analysis":
            builder.add_ai_analysis_action(
                action_id=action_def["id"],
                name=action_def["name"],
                analysis_type=action_def["analysis_type"],
                data_source=action_def["data_source"],
                description=action_def.get("description", ""),
            )
        elif action_type == "notification":
            builder.add_notification_action(
                action_id=action_def["id"],
                name=action_def["name"],
                message=action_def["message"],
                recipients=action_def["recipients"],
                description=action_def.get("description", ""),
            )


def _build_workflow_decisions(builder, workflow_def):
    """Build workflow decision nodes from definition"""
    for decision_def in workflow_def.get("decision_nodes", []):
        conditions = []
        for cond_def in decision_def.get("conditions", []):
            condition = WorkflowCondition(
                field=cond_def["field"],
                operator=ConditionOperator(cond_def["operator"]),
                value=cond_def["value"],
                description=cond_def.get("description"),
            )
            conditions.append(condition)

        builder.add_decision_node(
            node_id=decision_def["id"],
            name=decision_def["name"],
            conditions=conditions,
            true_path=decision_def["true_path"],
            false_path=decision_def["false_path"],
            description=decision_def.get("description", ""),
        )


def _configure_workflow_properties(builder, workflow_def):
    """Configure workflow properties from definition"""
    if "entry_point" in workflow_def:
        builder.set_entry_point(workflow_def["entry_point"])
    if "timeout_minutes" in workflow_def:
        builder.set_timeout(workflow_def["timeout_minutes"])
    if "learning_enabled" in workflow_def:
        builder.enable_learning(workflow_def["learning_enabled"])


async def _register_workflow_with_orchestrator(workflow):
    """Register workflow with orchestrator"""
    orchestrator = await create_workflow_orchestrator()
    return await orchestrator.register_workflow(workflow)


def _display_creation_results(workflow, registered_id, output_format):
    """Display workflow creation results"""
    if output_format == "json":
        result = {
            "workflow_id": registered_id,
            "name": workflow.name,
            "actions": len(workflow.actions),
            "decision_nodes": len(workflow.decision_nodes),
        }
        print(json.dumps(result, indent=2))
    else:
        print("Workflow created successfully!")
        print(f"ID: {registered_id}")
        print(f"Name: {workflow.name}")
        print(f"Actions: {len(workflow.actions)}")
        print(f"Decision nodes: {len(workflow.decision_nodes)}")
        print(f"\nTo execute: neuraops workflow execute {registered_id}")


@handle_exceptions
def workflow_create_command(name: str, description: str, workflow_file: str, output_format: str = "text") -> int:
    """Create a new workflow from definition file"""

    async def create_workflow_async():
        try:
            # Load workflow definition and create builder
            workflow_def = await _load_workflow_definition(workflow_file)
            workflow_id = workflow_def.get("id", name.lower().replace(" ", "_"))
            builder = WorkflowBuilder(workflow_id=workflow_id, name=name, description=description)

            # Build workflow components
            _build_workflow_actions(builder, workflow_def)
            _build_workflow_decisions(builder, workflow_def)
            _configure_workflow_properties(builder, workflow_def)

            # Build and register workflow
            workflow = builder.build()
            registered_id = await _register_workflow_with_orchestrator(workflow)

            # Display results
            _display_creation_results(workflow, registered_id, output_format)
            return 0

        except FileNotFoundError:
            print(f"Workflow definition file '{workflow_file}' not found", file=sys.stderr)
            return 1
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in workflow definition: {str(e)}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error creating workflow: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(create_workflow_async())


async def _get_workflow_statistics(orchestrator, workflow_id):
    """Get workflow statistics from orchestrator"""
    stats = await orchestrator.get_workflow_statistics(workflow_id)
    if not stats:
        print(f"No execution statistics available for workflow '{workflow_id}'")
        return None
    return stats


def _display_stats_json(stats):
    """Display statistics in JSON format"""
    print(json.dumps(stats, indent=2))


def _display_stats_text(workflow_id, stats):
    """Display statistics in text format"""
    print(f"Workflow Statistics: {workflow_id}")
    print("=" * 40)
    print(f"Total executions: {stats['total_executions']}")
    print(f"Successful executions: {stats['successful_executions']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"Average duration: {stats['average_duration_seconds']:.1f} seconds")
    if stats["last_execution"]:
        print(f"Last execution: {stats['last_execution']}")


@handle_exceptions
def workflow_stats_command(workflow_id: str, output_format: str = "json") -> int:
    """Show workflow execution statistics"""

    async def show_stats_async():
        try:
            orchestrator = await create_workflow_orchestrator()

            if workflow_id not in orchestrator.workflows:
                print(f"Workflow '{workflow_id}' not found", file=sys.stderr)
                return 1

            stats = await _get_workflow_statistics(orchestrator, workflow_id)
            if not stats:
                return 0

            if output_format == "json":
                _display_stats_json(stats)
            else:
                _display_stats_text(workflow_id, stats)

            return 0

        except Exception as e:
            print(f"Error getting workflow statistics: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(show_stats_async())


def _validate_workflow_exists(orchestrator, workflow_id: str) -> bool:
    """Validate that workflow exists"""
    if workflow_id not in orchestrator.workflows:
        print(f"Workflow '{workflow_id}' not found", file=sys.stderr)
        return False
    return True


async def _execute_optimization(orchestrator, workflow_id: str):
    """Execute workflow optimization and handle errors"""
    optimization = await orchestrator.optimize_workflow(workflow_id)

    if "error" in optimization:
        print(f"Error: {optimization['error']}", file=sys.stderr)
        return None

    return optimization


def _display_optimization_suggestions(suggestions) -> None:
    """Display optimization suggestions in formatted text"""
    if suggestions:
        print("Optimization Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion['type'].replace('_', ' ').title()}")
            print(f"   {suggestion['reasoning']}")
            if "current_timeout" in suggestion:
                print(f"   Current: {suggestion['current_timeout']}s")
                print(f"   Suggested: {suggestion['suggested_timeout']}s")
            print()
    else:
        print("No optimization suggestions available at this time.")


def _display_optimization_stats(stats) -> None:
    """Display current performance statistics"""
    if stats:
        print("Current Performance:")
        print(f"  Success rate: {stats.get('success_rate', 0):.1%}")
        print(f"  Average duration: {stats.get('average_duration_seconds', 0):.1f}s")
        print(f"  Total executions: {stats.get('total_executions', 0)}")


def _display_optimization_text(optimization, workflow_id: str) -> None:
    """Display optimization results in text format"""
    print(f"Workflow Optimization Report: {workflow_id}")
    print("=" * 45)

    suggestions = optimization.get("optimization_suggestions", [])
    _display_optimization_suggestions(suggestions)

    stats = optimization.get("current_stats", {})
    _display_optimization_stats(stats)


@handle_exceptions
def workflow_optimize_command(workflow_id: str, output_format: str = "json") -> int:
    """Optimize workflow based on execution history"""

    async def optimize_workflow_async():
        try:
            orchestrator = await create_workflow_orchestrator()

            if not _validate_workflow_exists(orchestrator, workflow_id):
                return 1

            optimization = await _execute_optimization(orchestrator, workflow_id)
            if optimization is None:
                return 1

            if output_format == "json":
                print(json.dumps(optimization, indent=2))
            else:
                _display_optimization_text(optimization, workflow_id)

            return 0

        except Exception as e:
            print(f"Error optimizing workflow: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(optimize_workflow_async())


@handle_exceptions
def workflow_templates_command(output_format: str = "table") -> int:
    """List available workflow templates"""

    templates = [
        {
            "id": "incident_response",
            "name": "Incident Response",
            "description": "Automated incident detection, analysis, and response",
            "complexity": "Intermediate",
            "duration": "~30 minutes",
        },
        {
            "id": "performance_optimization",
            "name": "Performance Optimization",
            "description": "Automated performance monitoring and optimization",
            "complexity": "Intermediate",
            "duration": "~45 minutes",
        },
        {
            "id": "security_audit",
            "name": "Security Audit",
            "description": "Automated security scanning and remediation",
            "complexity": "Advanced",
            "duration": "~60 minutes",
        },
    ]

    if output_format == "json":
        print(json.dumps(templates, indent=2))
    else:
        table_data = []
        for template in templates:
            table_data.append(
                [
                    template["id"],
                    template["name"],
                    template["complexity"],
                    template["duration"],
                    template["description"],
                ]
            )

        headers = ["ID", "Name", "Complexity", "Duration", "Description"]
        print(format_table(table_data, headers))

        print(f"\nTotal templates: {len(templates)}")
        print("Use 'neuraops workflow create-template <template_id>' to create from template")

    return 0


@handle_exceptions
def workflow_create_template_command(template_id: str, workflow_id: Optional[str] = None, output_format: str = "text") -> int:
    """Create workflow from template"""

    async def create_from_template_async():
        try:
            # Create workflow based on template
            if template_id == "incident_response":
                workflow = await create_incident_response_workflow()
            elif template_id == "performance_optimization":
                workflow = await create_performance_optimization_workflow()
            elif template_id == "security_audit":
                workflow = await create_security_audit_workflow()
            else:
                print(f"Unknown template: {template_id}", file=sys.stderr)
                print("Available templates: incident_response, performance_optimization, security_audit")
                return 1

            # Override workflow ID if provided
            if workflow_id:
                workflow.workflow_id = workflow_id

            # Register workflow
            orchestrator = WorkflowOrchestrator()  # Create new instance for registration
            registered_id = await orchestrator.register_workflow(workflow)

            if output_format == "json":
                result = {
                    "workflow_id": registered_id,
                    "template": template_id,
                    "name": workflow.name,
                    "actions": len(workflow.actions),
                    "decision_nodes": len(workflow.decision_nodes),
                }
                print(json.dumps(result, indent=2))
            else:
                print(f"Workflow created from template '{template_id}'!")
                print(f"ID: {registered_id}")
                print(f"Name: {workflow.name}")
                print(f"Actions: {len(workflow.actions)}")
                print(f"Decision nodes: {len(workflow.decision_nodes)}")
                print(f"\nTo execute: neuraops workflow execute {registered_id}")

            return 0

        except Exception as e:
            print(f"Error creating workflow from template: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(create_from_template_async())
