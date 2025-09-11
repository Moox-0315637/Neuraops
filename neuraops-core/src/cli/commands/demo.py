"""NeuraOps Demo CLI Commands

CLI commands for running demonstration scenarios
"""

import asyncio
import json
import sys
from typing import Optional, List, Dict, Any

import aiofiles

from ..ui.components import create_metrics_table, display_success, display_error, format_table
from ..utils.decorators import handle_exceptions
from ...demos import (
    NeuraOpsDemoEngine,
    run_quick_demo,
    run_interactive_demo,
    list_available_demos,
    create_custom_demo,
)


@handle_exceptions
def demo_list_command(
    output_format: str = "table",
    complexity: Optional[str] = None,
    duration_max: Optional[int] = None,
) -> int:
    """List all available demo scenarios"""
    scenarios = list_available_demos()

    # Filter by complexity if specified
    if complexity:
        scenarios = [s for s in scenarios if s.get("complexity") == complexity.lower()]

    # Filter by maximum duration if specified
    if duration_max:
        scenarios = [s for s in scenarios if s.get("duration_minutes", 0) <= duration_max]

    if output_format == "json":
        print(json.dumps(scenarios, indent=2))
    else:
        # Prepare data for table
        table_data = []
        for scenario in scenarios:
            name_clean = scenario.get("name", "")
            for emoji in ["🚨", "⚡", "🔐", "🏗️", "🤖", "🔮", "🎯"]:
                name_clean = name_clean.replace(emoji, "")
            name_clean = name_clean.strip()

            desc = scenario.get("description", "")
            desc_short = desc[:50] + ("..." if len(desc) > 50 else "")

            table_data.append(
                [
                    scenario.get("id", ""),
                    name_clean,
                    scenario.get("complexity", ""),
                    f"{scenario.get('duration_minutes', 0)} min",
                    str(scenario.get("step_count", 0)),
                    desc_short,
                ]
            )

        headers = ["ID", "Name", "Complexity", "Duration", "Steps", "Description"]
        print(format_table(table_data, headers))
        print(f"\nTotal scenarios: {len(scenarios)}")

    return 0


@handle_exceptions
def demo_show_command(scenario_id: str, output_format: str = "json") -> int:
    """Show detailed information about a specific demo scenario"""
    demo_engine = NeuraOpsDemoEngine()
    scenario_details = demo_engine.get_scenario_details(scenario_id)

    if not scenario_details:
        print(f"Error: Demo scenario '{scenario_id}' not found", file=sys.stderr)
        return 1

    if output_format == "json":
        print(json.dumps(scenario_details, indent=2))
    else:
        # Format as readable text
        scenario = scenario_details["scenario"]
        steps = scenario_details["steps"]

        print(f"Demo Scenario: {scenario['name']}")
        print("=" * (len(scenario["name"]) + 15))
        print()
        print(f"ID: {scenario['id']}")
        print(f"Description: {scenario['description']}")
        print(f"Duration: {scenario['duration_minutes']} minutes")
        print(f"Complexity: {scenario['complexity']}")
        print()

        print("Prerequisites:")
        for prereq in scenario.get("prerequisites", []):
            print(f"  • {prereq}")
        print()

        print("Learning Objectives:")
        for objective in scenario.get("learning_objectives", []):
            print(f"  • {objective}")
        print()

        print(f"Steps ({len(steps)}):")
        print("-" * 20)
        for step in steps:
            print(f"{step['step_number']}. {step['title']}")
            print(f"   {step['description']}")
            if step.get("command"):
                print(f"   Command: {step['command']}")
            if step.get("interactive"):
                print("   [Interactive Step]")
            print()

    return 0


# Helper functions to reduce complexity


def _validate_scenario(demo_engine: NeuraOpsDemoEngine, scenario_id: str) -> bool:
    """Validate that a scenario exists."""
    if scenario_id not in demo_engine.demo_scenarios:
        available = list(demo_engine.demo_scenarios.keys())
        print(f"Error: Demo scenario '{scenario_id}' not found", file=sys.stderr)
        print(f"Available scenarios: {', '.join(available)}", file=sys.stderr)
        return False
    return True


async def _show_scenario_info(scenario, interactive: bool) -> bool:
    """Display scenario information and get user confirmation."""
    if not interactive:
        return True

    print(f"\n{scenario.name}")
    print("=" * len(scenario.name))
    print(f"Description: {scenario.description}")
    print(f"Estimated duration: {scenario.duration_minutes} minutes")
    print(f"Complexity: {scenario.complexity}")
    print()

    if scenario.prerequisites:
        print("Prerequisites:")
        for prereq in scenario.prerequisites:
            print(f"  • {prereq}")
        print()

    response = await asyncio.to_thread(input, "Do you want to continue? (y/N): ")
    if response.lower() not in ["y", "yes"]:
        print("Demo cancelled.")
        return False
    return True


async def _save_results(results: Dict[str, Any], save_path: str) -> None:
    """Save demo results to a file."""
    async with aiofiles.open(save_path, "w") as f:
        await f.write(json.dumps(results, indent=2))
    print(f"\nResults saved to: {save_path}")


def _display_results(results: Dict[str, Any], output_format: str, scenario) -> None:
    """Display demo results in the specified format."""
    if output_format == "json":
        print(json.dumps(results, indent=2))
    else:
        print("\nDemo Results:")
        print(f"Scenario: {results['name']}")
        print(f"Duration: {results['actual_duration']:.1f} minutes")
        success_symbol = "✓" if results["overall_success"] else "✗"
        print(f"Success: {success_symbol}")
        completed_count = len(results["steps_completed"])
        total_steps = len(scenario.steps)
        print(f"Steps completed: {completed_count}/{total_steps}")

        if results.get("error_messages"):
            print("\nErrors:")
            for error in results["error_messages"]:
                print(f"  • {error}")


@handle_exceptions
def demo_run_command(
    scenario_id: str,
    interactive: bool = True,
    output_format: str = "text",
    save_results: Optional[str] = None,
) -> int:
    """Run a demo scenario with reduced complexity."""

    async def run_demo_async():
        demo_engine = NeuraOpsDemoEngine()

        # Validate scenario
        if not _validate_scenario(demo_engine, scenario_id):
            return 1

        # Get scenario
        scenario = demo_engine.demo_scenarios[scenario_id]

        # Show info and get confirmation
        if not await _show_scenario_info(scenario, interactive):
            return 0

        # Run the demo
        print(f"\nStarting demo: {scenario.name}")
        print("-" * 50)

        try:
            results = await demo_engine.run_demo(scenario_id, interactive)

            # Display results
            _display_results(results, output_format, scenario)

            # Save if requested
            if save_results:
                await _save_results(results, save_results)

            return 0 if results["overall_success"] else 1

        except Exception as e:
            print(f"Demo failed: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(run_demo_async())


def _format_quick_results(results: Dict[str, Any], output_format: str) -> None:
    """Format and display quick demo results."""
    if output_format == "json":
        print(json.dumps(results, indent=2))
    else:
        print("\nQuick Demo Results:")
        print(f"Scenario: {results['name']}")
        print(f"Duration: {results['actual_duration']:.1f} minutes")
        success_symbol = "✓" if results["overall_success"] else "✗"
        print(f"Success: {success_symbol}")

        if results.get("error_messages"):
            print("Errors:")
            for error in results["error_messages"]:
                print(f"  • {error}")


@handle_exceptions
def demo_quick_command(demo_type: str = "incident_response", output_format: str = "text") -> int:
    """Run a quick (non-interactive) demo with reduced complexity."""

    async def run_quick_async():
        try:
            print(f"Running quick demo: {demo_type}")
            results = await run_quick_demo(demo_type)

            # Display formatted results
            _format_quick_results(results, output_format)

            return 0 if results["overall_success"] else 1

        except Exception as e:
            print(f"Quick demo failed: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(run_quick_async())


@handle_exceptions
def demo_create_command(name: str, description: str, steps_file: str, output_format: str = "text") -> int:
    """Create a custom demo scenario from a JSON file"""

    async def create_demo_async():
        try:
            # Load steps from file
            async with aiofiles.open(steps_file, "r") as f:
                content = await f.read()
                steps = json.loads(content)

            if not isinstance(steps, list):
                print("Error: Steps file must contain a JSON array", file=sys.stderr)
                return 1

            # Create custom demo
            scenario_id = await create_custom_demo(steps, name, description)

            if output_format == "json":
                result = {"scenario_id": scenario_id, "name": name}
                print(json.dumps(result, indent=2))
            else:
                print("Custom demo created successfully!")
                print(f"Scenario ID: {scenario_id}")
                print(f"Name: {name}")
                print(f"Steps: {len(steps)}")
                print(f"\nTo run: neuraops demo run {scenario_id}")

            return 0

        except FileNotFoundError:
            print(f"Error: Steps file '{steps_file}' not found", file=sys.stderr)
            return 1
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in steps file: {str(e)}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Failed to create custom demo: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(create_demo_async())


@handle_exceptions
def demo_interactive_command(demo_type: str = "ai_assistant_showcase", save_results: Optional[str] = None) -> int:
    """Run an interactive demo with full user interaction"""

    async def run_interactive_async():
        try:
            print(f"Starting interactive demo: {demo_type}")
            print("This demo will guide you through each step interactively.\n")

            results = await run_interactive_demo(demo_type)

            print("\nInteractive Demo Completed!")
            print(f"Scenario: {results['name']}")
            print(f"Duration: {results['actual_duration']:.1f} minutes")
            success_symbol = "✓" if results["overall_success"] else "✗"
            print(f"Success: {success_symbol}")

            # Save results if requested
            if save_results:
                async with aiofiles.open(save_results, "w") as f:
                    await f.write(json.dumps(results, indent=2))
                print(f"Results saved to: {save_results}")

            return 0 if results["overall_success"] else 1

        except Exception as e:
            print(f"Interactive demo failed: {str(e)}", file=sys.stderr)
            return 1

    return asyncio.run(run_interactive_async())


# Helper functions for export command


def _generate_markdown_content(scenario: Dict[str, Any], steps: List[Dict[str, Any]]) -> str:
    """Generate Markdown documentation for a scenario."""
    content = f"# {scenario['name']}\n\n"
    content += f"{scenario['description']}\n\n"
    content += f"**Duration:** {scenario['duration_minutes']} minutes  \n"
    content += f"**Complexity:** {scenario['complexity']}\n\n"

    # Add prerequisites if present
    if scenario.get("prerequisites"):
        content += "## Prerequisites\n\n"
        for prereq in scenario["prerequisites"]:
            content += f"- {prereq}\n"
        content += "\n"

    # Add learning objectives if present
    if scenario.get("learning_objectives"):
        content += "## Learning Objectives\n\n"
        for objective in scenario["learning_objectives"]:
            content += f"- {objective}\n"
        content += "\n"

    # Add steps
    content += "## Steps\n\n"
    for step in steps:
        content += f"### Step {step['step_number']}: {step['title']}\n\n"
        content += f"{step['description']}\n\n"

        if step.get("explanation"):
            content += f"**Explanation:** {step['explanation']}\n\n"

        if step.get("command"):
            content += f"```bash\n{step['command']}\n```\n\n"

        if step.get("interactive"):
            content += "*This is an interactive step.*\n\n"

        content += "---\n\n"

    return content


def _generate_json_content(scenario_details: Dict[str, Any]) -> str:
    """Generate JSON documentation for a scenario."""
    return json.dumps(scenario_details, indent=2)


def _write_export_file(file_path: str, content: str) -> None:
    """Write exported content to a file."""
    with open(file_path, "w") as f:
        f.write(content)


@handle_exceptions
def demo_export_command(scenario_id: str, output_file: str, format_type: str = "markdown") -> int:
    """Export demo scenario as documentation with reduced complexity."""
    demo_engine = NeuraOpsDemoEngine()
    scenario_details = demo_engine.get_scenario_details(scenario_id)

    if not scenario_details:
        print(f"Error: Demo scenario '{scenario_id}' not found", file=sys.stderr)
        return 1

    try:
        # Generate content based on format
        if format_type.lower() == "markdown":
            content = _generate_markdown_content(scenario_details["scenario"], scenario_details["steps"])
        elif format_type.lower() == "json":
            content = _generate_json_content(scenario_details)
        else:
            print(f"Error: Unsupported format '{format_type}'. Use 'markdown' or 'json'", file=sys.stderr)
            return 1

        # Write to file
        _write_export_file(output_file, content)
        print(f"Demo scenario exported to: {output_file}")
        return 0

    except Exception as e:
        print(f"Failed to export demo: {str(e)}", file=sys.stderr)
        return 1
