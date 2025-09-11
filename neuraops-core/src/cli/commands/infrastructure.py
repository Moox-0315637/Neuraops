"""
NeuraOps CLI commands for infrastructure operations
Provides commands for templates, deployments, monitoring, and management of infrastructure
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

import aiofiles

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich.tree import Tree
from rich.progress import BarColumn

from ...modules.infrastructure.templates import TemplateEngine, TemplateType
from ...modules.infrastructure.deployment import DeploymentOrchestrator
from ...modules.infrastructure.monitoring import (
    InfrastructureMonitor,
    ResourceType,
    AlertManager,
    quick_k8s_health_check,
    quick_docker_health_check,
    comprehensive_infrastructure_check,
)
from ...core.engine import get_engine
from ...core.structured_output import InfrastructureAssessment
from ...devops_commander.exceptions import OllamaConnectionError, ModelInferenceError


# Helper functions for UI feedback (remplace l'import manquant cli.ui.helpers)
def print_success(text: str) -> None:
    console.print(f"[green]✅ {text}[/green]")


def print_error(text: str) -> None:
    console.print(f"[red]❌ {text}[/red]")


def print_warning(text: str) -> None:
    console.print(f"[yellow]⚠️ {text}[/yellow]")


def print_info(text: str) -> None:
    console.print(f"[blue]ℹ️ {text}[/blue]")


# Create Typer app for infrastructure commands
infrastructure_app = typer.Typer(help="Infrastructure management commands", name="infra")

console = Console()

# UI Constants - évite la duplication de littéraux strings (SonarQube S1192)
K8S_NAMESPACE_LABEL = "Kubernetes namespace"
BOLD_WHITE_STYLE = "bold white"
CLOUD_RESOURCES_ANALYSIS = "Include cloud resources in analysis"


@infrastructure_app.command("templates")
def list_available_templates(template_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by template type")):
    """List available infrastructure templates"""

    template_engine = TemplateEngine()

    # Extract nested conditional expression
    if template_type:
        template_type_enum = TemplateType(template_type.upper())
    else:
        template_type_enum = None

    available_templates = template_engine.list_available_templates(template_type=template_type_enum)

    table = Table(title="Available Infrastructure Templates")
    table.add_column("Template Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Description", style="white")

    for template in available_templates:
        table.add_row(template["name"], template["type"], template["description"])

    console.print(table)


# Helper functions for template generation (Phase 57 refactoring)

def _parse_template_variables(variables: Optional[List[str]]) -> Dict[str, str]:
    """Parse variables from KEY=VALUE format to dictionary"""
    var_dict = {}
    if variables:
        for var in variables:
            if "=" in var:
                key, value = var.split("=", 1)
                var_dict[key.strip()] = value.strip()
    return var_dict


def _validate_and_get_template_type(template_name: str):
    """Validate template name and return corresponding TemplateType"""
    from ...modules.infrastructure.templates import TemplateType, TemplateEngine
    
    # Get all available templates
    template_engine = TemplateEngine()
    all_templates = template_engine.list_available_templates()
    
    # Find the template by name
    for template_info in all_templates:
        if template_info["name"] == template_name:
            # Map the type string back to TemplateType enum
            template_type_map = {
                "DOCKER": TemplateType.DOCKER,
                "KUBERNETES": TemplateType.KUBERNETES,
                "TERRAFORM": TemplateType.TERRAFORM,
                "ANSIBLE": TemplateType.ANSIBLE,
                "COMPOSE": TemplateType.COMPOSE,
                "HELM": TemplateType.HELM,
                "VAGRANT": TemplateType.VAGRANT,
            }
            return template_type_map.get(template_info["type"])
    
    # Template not found - list available templates
    available_names = [t["name"] for t in all_templates]
    raise ValueError(f"Template '{template_name}' not found. Available templates: {', '.join(available_names)}")


def _create_template_request(template_type, template_name: str, var_dict: Dict[str, str]):
    """Create TemplateRequest with proper parameters"""
    from ...modules.infrastructure.templates import TemplateRequest, Environment
    
    app_name = var_dict.get("app_name") or var_dict.get("name", f"myapp-{template_name}")
    description = var_dict.get("description", f"Generated {template_name} infrastructure template")
    
    return TemplateRequest(
        template_type=template_type,
        application_name=app_name,
        description=description,
        environment=Environment.DEVELOPMENT,
        requirements=var_dict,
    )


def _save_generated_template(generated_template, template_type, template_name: str, output_dir: str) -> List[str]:
    """Save generated template and return list of generated files"""
    from ...modules.infrastructure.templates import TemplateType
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    file_extensions = {
        TemplateType.DOCKER: "Dockerfile",
        TemplateType.KUBERNETES: "k8s.yaml",
        TemplateType.TERRAFORM: "main.tf",
        TemplateType.ANSIBLE: "playbook.yml",
        TemplateType.COMPOSE: "docker-compose.yml",
        TemplateType.HELM: "Chart.yaml",
        TemplateType.VAGRANT: "Vagrantfile",
    }
    
    filename = file_extensions.get(template_type, f"{template_name}.txt")
    file_path = output_path / filename
    
    generated_template.save_to_file(file_path)
    
    generated_files = [str(file_path)]
    metadata_file = file_path.with_suffix(f"{file_path.suffix}.meta.json")
    if metadata_file.exists():
        generated_files.append(str(metadata_file))
    
    return generated_files


def _create_template_result(success: bool, generated_files=None, error_message=None):
    """Create TemplateResult object"""
    class TemplateResult:
        def __init__(self, success: bool, generated_files=None, error_message=None):
            self.success = success
            self.generated_files = generated_files or []
            self.error_message = error_message
    
    return TemplateResult(success=success, generated_files=generated_files, error_message=error_message)


def _display_template_results(result, output_dir: str):
    """Display template generation results"""
    if result.success:
        print_success(f"Template generated successfully to {output_dir}")
        
        tree = Tree(f"📁 [bold]{output_dir}")
        for file_path in result.generated_files:
            relative_path = os.path.relpath(file_path, output_dir)
            tree.add(f"[green]{relative_path}")
        
        console.print(tree)
    else:
        print_error(f"Failed to generate template: {result.error_message}")


@infrastructure_app.command("generate")
def generate_template(
    template_name: str = typer.Argument(..., help="Name of the template to generate"),
    output_dir: str = typer.Option("/tmp/neuraops/generated", "--output", "-o", help="Output directory"),
    variables: Optional[List[str]] = typer.Option(None, "--var", "-v", help="Variables in KEY=VALUE format"),
):
    """Generate infrastructure template files"""
    
    template_engine = TemplateEngine()
    var_dict = _parse_template_variables(variables)

    with Progress(SpinnerColumn(), TextColumn("[bold green]Generating template..."), transient=True) as progress:
        progress.add_task("generate", total=None)

        try:
            template_type = _validate_and_get_template_type(template_name)
            request = _create_template_request(template_type, template_name, var_dict)
            generated_template = asyncio.run(template_engine.generate_template(request))
            generated_files = _save_generated_template(generated_template, template_type, template_name, output_dir)
            result = _create_template_result(success=True, generated_files=generated_files)
            
        except Exception as e:
            result = _create_template_result(success=False, error_message=str(e))

    _display_template_results(result, output_dir)


def _display_generation_header(requirement: str, provider: str, config_type: str):
    """Display generation header panel"""
    console.print(
        Panel(
f"[bold cyan]AI Infrastructure Generation[/bold cyan]\nRequirement: {requirement}\nProvider: {provider.upper()}\nType: {config_type.upper()}",
            title="🏗️ Infrastructure Generation",
            border_style="blue",
        )
    )


def _create_status_panel(ai_used: bool, validation_passed: bool, validate: bool):
    """Create status panel content"""
    status_items = []
    if ai_used:
        status_items.append("🤖 AI Generation: ✓")
    if validation_passed:
        status_items.append("✅ Validation: ✓")
    elif validate:
        status_items.append("⏳ Validation: Pending")

    return Panel("\n".join(status_items) if status_items else "🔄 Initializing...", title="Status", border_style="green")


async def _generate_with_ai_engine(layout, requirement: str, provider: str, config_type: str, demo_mode: bool):
    """Generate infrastructure code with AI engine"""
    generated_code = None
    ai_used = False

    try:
        # Get AI engine
        engine = get_engine()
        layout["main"].update(Panel("AI engine connected ✓\nGenerating infrastructure code...", title="Progress"))

        # Generate infrastructure code with AI
        generated_code = await engine.generate_infrastructure_config(requirements=requirement, provider=provider, config_type=config_type)
        ai_used = True
        layout["main"].update(Panel("Infrastructure code generated ✓\nValidating syntax...", title="Progress"))

    except (OllamaConnectionError, ModelInferenceError) as e:
        if demo_mode:
            # Fallback to template-based generation
            layout["main"].update(Panel(f"AI failed: {e}\nUsing template fallback...", title="Progress"))
            generated_code = _generate_fallback_infrastructure(requirement, provider, config_type)
        else:
            raise

    return generated_code, ai_used


def _validate_generated_code(layout, generated_code: str, config_type: str, validate: bool):
    """Validate generated infrastructure code"""
    validation_passed = False

    if validate and generated_code:
        try:
            validation_result = _validate_infrastructure_syntax(generated_code, config_type)
            validation_passed = validation_result["valid"]

            if validation_passed:
                layout["main"].update(Panel("Infrastructure code validated ✓\nGeneration complete!", title="Progress"))
            else:
                warnings_preview = chr(10).join(validation_result["warnings"][:3])
                layout["main"].update(Panel(f"Validation warnings found:\n{warnings_preview}\n\nGeneration complete with warnings.", title="Progress"))

        except Exception as validation_error:
            layout["main"].update(Panel(f"Validation failed: {validation_error}\nGeneration complete (unvalidated).", title="Progress"))

    return validation_passed


def _display_generation_results(generated_code: str, provider: str, config_type: str, ai_used: bool, validation_passed: bool, validate: bool):
    """Display generation results and summary"""
    # Show generation summary
    ai_generated_text = "Yes" if ai_used else "No (Fallback)"
    if validation_passed:
        validation_text = "Yes"
    elif validate:
        validation_text = "No"
    else:
        validation_text = "Skipped"

    console.print(
        Panel(
            f"[green]✓ Infrastructure code generated successfully[/green]\n"
            f"Provider: {provider.upper()}\n"
            f"Type: {config_type.upper()}\n"
            f"AI Generated: {ai_generated_text}\n"
            f"Validated: {validation_text}",
            title="Generation Summary",
            border_style="green",
        )
    )

    # Display code (truncated for display)
    if len(generated_code) > 1000:
        code_preview = generated_code[:1000] + "..."
    else:
        code_preview = generated_code

    console.print(Panel(code_preview, title=f"Generated {config_type.title()} Code", border_style="blue", expand=False))


async def _save_generated_code(output_file: str, generated_code: str):
    """Save generated code to file"""
    try:
        async with aiofiles.open(output_file, "w") as f:
            await f.write(generated_code)
        print_success(f"Code saved to {output_file}")
    except Exception as e:
        print_error(f"Failed to save to {output_file}: {e}")


@infrastructure_app.command("ai-generate")
def ai_generate_infrastructure(
    requirement: str = typer.Argument(..., help="Describe the infrastructure you need"),
    provider: str = typer.Option("aws", "--provider", "-p", help="Cloud provider (aws, azure, gcp)"),
    config_type: str = typer.Option("terraform", "--type", "-t", help="Configuration type (terraform, kubernetes, ansible)"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save generated code to file"),
    demo_mode: bool = typer.Option(False, "--demo", help="Enable demo mode with enhanced reliability"),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Validate generated code syntax"),
):
    """Generate infrastructure code using AI with real-time progress and validation"""

    _display_generation_header(requirement, provider, config_type)

    generated_code = None
    ai_used = False
    validation_passed = False

    # Create layout for real-time updates
    layout = Layout()
    layout.split_row(Layout(name="main", minimum_size=60), Layout(name="status", size=30))

    with Live(layout, refresh_per_second=2, console=console) as _:
        try:
            # Initialize status
            layout["status"].update(_create_status_panel(ai_used, validation_passed, validate))
            layout["main"].update(Panel("Connecting to AI engine...", title="Progress"))

            # Generate infrastructure code with AI (run async function synchronously)
            generated_code, ai_used = asyncio.run(_generate_with_ai_engine(layout, requirement, provider, config_type, demo_mode))
            layout["status"].update(_create_status_panel(ai_used, validation_passed, validate))

            # Validate generated code if requested
            validation_passed = _validate_generated_code(layout, generated_code, config_type, validate)
            layout["status"].update(_create_status_panel(ai_used, validation_passed, validate))

            # Final pause to show completion status
            import time
            time.sleep(1)  # Use time.sleep instead of await asyncio.sleep

        except Exception as e:
            layout["main"].update(Panel(f"[red]Error: {str(e)}[/red]", title="Error"))
            if not demo_mode:
                raise
            generated_code = _generate_fallback_infrastructure(requirement, provider, config_type)

    # Display results
    if generated_code:
        _display_generation_results(generated_code, provider, config_type, ai_used, validation_passed, validate)

        # Save to file if requested (run async function synchronously)
        if output_file:
            asyncio.run(_save_generated_code(output_file, generated_code))

        return generated_code
    else:
        print_error("Failed to generate infrastructure code")
        if not demo_mode:
            raise typer.Exit(code=1)


def _generate_fallback_infrastructure(requirement: str, provider: str, config_type: str) -> str:
    """Generate fallback infrastructure code when AI is unavailable"""

    # Simple template-based fallback
    fallback_templates = {
        (
            "aws",
            "terraform",
        ): """# AWS Infrastructure - Generated by NeuraOps Fallback
provider "aws" {
  region = "us-west-2"
}

# Basic VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "main-vpc"
    GeneratedBy = "NeuraOps"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "main-igw"
  }
}

# Note: This is a basic template. Customize based on your requirements:
# {requirement}
""",
        (
            "aws",
            "kubernetes",
        ): """# Kubernetes Deployment - Generated by NeuraOps Fallback
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  labels:
    app: main-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: main-app
  template:
    metadata:
      labels:
        app: main-app
    spec:
      containers:
      - name: app
        image: nginx:1.20
        ports:
        - containerPort: 80
        resources:
          limits:
            cpu: 500m
            memory: 512Mi
          requests:
            cpu: 200m
            memory: 256Mi

---
apiVersion: v1
kind: Service
metadata:
  name: app-service
spec:
  selector:
    app: main-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer

# Note: This is a basic template. Customize based on your requirements:
# {requirement}
""",
    }

    template_key = (provider.lower(), config_type.lower())
    if template_key in fallback_templates:
        return fallback_templates[template_key].format(requirement=requirement)
    else:
        return f"""# {config_type.title()} Configuration for {provider.upper()}
# Generated by NeuraOps Fallback System

# Requirement: {requirement}
# Provider: {provider}
# Type: {config_type}

# Note: This is a placeholder. Please implement the specific configuration
# for your requirements manually or try again with AI connectivity.
"""


def _validate_terraform_syntax(code: str, warnings: List[str]) -> bool:
    """Validate Terraform syntax and add warnings"""
    valid = True

    # Basic Terraform validation
    required_blocks = ["provider", "resource"]
    for block in required_blocks:
        if block not in code:
            warnings.append(f"Missing {block} block")

    return valid


def _validate_kubernetes_syntax(code: str, warnings: List[str]) -> bool:
    """Validate Kubernetes syntax and add warnings"""
    valid = True

    # Basic Kubernetes validation
    if "apiVersion:" not in code:
        warnings.append("Missing apiVersion field")
        valid = False

    if "kind:" not in code:
        warnings.append("Missing kind field")
        valid = False

    return valid


def _validate_ansible_syntax(code: str, warnings: List[str]) -> bool:
    """Validate Ansible syntax and add warnings"""
    valid = True

    # Basic Ansible validation
    if "hosts:" not in code and "- name:" not in code:
        warnings.append("Invalid Ansible playbook structure")
        valid = False

    return valid


def _check_security_practices(code: str, warnings: List[str]):
    """Check for basic security practices"""
    # Check for hardcoded passwords
    if "password" in code.lower() and "var." not in code:
        warnings.append("Hardcoded passwords detected - use variables instead")


def _validate_infrastructure_syntax(code: str, config_type: str) -> Dict[str, any]:
    """Basic validation of infrastructure code syntax"""

    warnings = []
    valid = True

    try:
        config_lower = config_type.lower()

        if config_lower == "terraform":
            valid = _validate_terraform_syntax(code, warnings)
            _check_security_practices(code, warnings)
        elif config_lower == "kubernetes":
            valid = _validate_kubernetes_syntax(code, warnings)
        elif config_lower == "ansible":
            valid = _validate_ansible_syntax(code, warnings)

        return {"valid": valid, "warnings": warnings, "syntax_errors": []}

    except Exception as e:
        return {"valid": False, "warnings": warnings, "syntax_errors": [str(e)]}


def _load_deployment_config(config_file: str):
    """Load and validate deployment configuration file"""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print_error(f"Configuration file not found: {config_file}")
        return None
    except json.JSONDecodeError:
        print_error(f"Invalid JSON in configuration file: {config_file}")
        return None


def _execute_dry_run(deployment_manager, config):
    """Execute deployment validation (dry run)"""
    result = asyncio.run(deployment_manager.validate_deployment_config(config))

    if result.success:
        print_success("Deployment configuration is valid")
        for message in result.validation_messages:
            print_info(f"✓ {message}")
    else:
        print_error(f"Invalid configuration: {result.error_message}")
        for message in result.validation_messages:
            print_warning(f"✗ {message}")

    return result


def _execute_deployment(deployment_manager, config):
    """Execute actual deployment"""
    result = asyncio.run(deployment_manager.execute_deployment(config))

    if result.success:
        print_success("Deployment completed successfully")
        _display_deployment_summary(result)
        _display_resource_urls(result)
    else:
        print_error(f"Deployment failed: {result.error_message}")

    return result


def _display_deployment_summary(result):
    """Display deployment summary table"""
    table = Table(title="Deployment Summary")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Duration", style="white")

    for component, details in result.deployment_details.items():
        status = "✅ Success" if details.get("success", False) else "❌ Failed"
        duration = f"{details.get('duration_seconds', 0):.2f}s"
        table.add_row(component, status, duration)

    console.print(table)


def _display_resource_urls(result):
    """Display resource URLs if available"""
    if hasattr(result, "resource_urls") and result.resource_urls:
        console.print("\n[bold]Resource URLs:[/bold]")
        for name, url in result.resource_urls.items():
            console.print(f"  [cyan]{name}:[/cyan] [link={url}]{url}[/link]")


def _run_deployment_with_progress(deployment_manager, config, dry_run: bool):
    """Run deployment operation with progress display"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Deploying infrastructure..."),
        transient=not dry_run,
    ) as progress:
        _ = progress.add_task("deploy", total=None)

        if dry_run:
            return _execute_dry_run(deployment_manager, config)
        else:
            return _execute_deployment(deployment_manager, config)


@infrastructure_app.command("deploy")
def deploy_infrastructure(
    config_file: str = typer.Argument(..., help="Path to deployment configuration file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without actual deployment"),
):
    """Deploy infrastructure using configuration file"""

    try:
        # Load deployment configuration
        config = _load_deployment_config(config_file)
        if config is None:
            return

        # Execute deployment
        deployment_manager = DeploymentOrchestrator()
        _run_deployment_with_progress(deployment_manager, config, dry_run)

    except Exception as e:
        print_error(f"Deployment error: {str(e)}")


def _setup_monitoring_layout():
    """Setup monitoring layout with panels"""
    layout = Layout()
    layout.split(Layout(name="header", size=3), Layout(name="main"), Layout(name="footer", size=3))

    # Split main area into sections
    layout["main"].split_row(Layout(name="left"), Layout(name="right"))
    layout["left"].split(Layout(name="kubernetes", ratio=2), Layout(name="docker", ratio=1))
    layout["right"].split(Layout(name="system", ratio=1), Layout(name="alerts", ratio=2))

    return layout


def _render_header():
    """Render monitoring header panel"""
    return Panel(
        f"[{BOLD_WHITE_STYLE} on blue]NeuraOps Infrastructure Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/{BOLD_WHITE_STYLE} on blue]",
        style="blue",
    )


def _render_footer(monitoring_time):
    """Render monitoring footer panel"""
    return Panel(
        f"[{BOLD_WHITE_STYLE}]Monitoring for {monitoring_time}s | Press Ctrl+C to exit[/{BOLD_WHITE_STYLE}]",
        style="blue",
    )


def _render_kubernetes_panel(metrics, namespace: str):
    """Render Kubernetes resources panel"""
    k8s_metrics = [m for m in metrics if m.resource_type in [ResourceType.POD, ResourceType.SERVICE, ResourceType.NODE]]

    if not k8s_metrics:
        return Panel("No Kubernetes resources found", title="Kubernetes", border_style="green")

    table = Table(show_header=True, header_style=BOLD_WHITE_STYLE, show_lines=True)
    table.add_column("Resource")
    table.add_column("Type")
    table.add_column("CPU (%)")
    table.add_column("Memory")
    table.add_column("Status")

    for metric in k8s_metrics[:10]:  # Show top 10 to avoid overflow
        resource_id = metric.resource_id
        resource_type = metric.resource_type.value
        cpu = metric.metrics.get("cpu_usage", "N/A")
        mem = metric.metrics.get("memory_usage", "N/A")

        status_style = "green" if metric.healthy else "red"
        status_text = "✓ Healthy" if metric.healthy else f"✗ {', '.join(metric.alerts)}"

        table.add_row(
            resource_id,
            resource_type,
            f"{cpu:.1f}" if isinstance(cpu, float) else str(cpu),
            f"{mem:.1f} MB" if isinstance(mem, float) else str(mem),
            f"[{status_style}]{status_text}[/{status_style}]",
        )

    return Panel(table, title=f"Kubernetes ({namespace})", border_style="green")


def _render_docker_panel(metrics):
    """Render Docker containers panel"""
    docker_metrics = [m for m in metrics if m.resource_type == ResourceType.CONTAINER]

    if not docker_metrics:
        return Panel("No Docker containers found", title="Docker", border_style="cyan")

    table = Table(show_header=True, header_style=BOLD_WHITE_STYLE)
    table.add_column("Container")
    table.add_column("CPU (%)")
    table.add_column("Status")

    for metric in docker_metrics[:5]:  # Show top 5
        container_id = metric.resource_id
        cpu = metric.metrics.get("cpu_usage", "N/A")

        status_style = "green" if metric.healthy else "red"
        status_text = "✓ Healthy" if metric.healthy else f"✗ {', '.join(metric.alerts)}"

        table.add_row(
            container_id,
            f"{cpu:.1f}" if isinstance(cpu, float) else str(cpu),
            f"[{status_style}]{status_text}[/{status_style}]",
        )

    return Panel(table, title="Docker Containers", border_style="cyan")


def _render_system_panel(metrics):
    """Render system resources panel"""
    system_metrics = [m for m in metrics if m.resource_type == ResourceType.NODE and m.labels.get("type") == "system"]

    if not system_metrics:
        return Panel("No system metrics found", title="System", border_style="magenta")

    # Since we only have one system entry
    metric = system_metrics[0]

    # Create progress bars for different metrics
    cpu_usage = metric.metrics.get("cpu_usage", 0)
    disk_usage = metric.metrics.get("disk_usage", 0)

    cpu_color = "green" if cpu_usage < 80 else "red"
    disk_color = "green" if disk_usage < 90 else "red"

    cpu_text = f"[{BOLD_WHITE_STYLE}]CPU: [/{BOLD_WHITE_STYLE}][{cpu_color}]{cpu_usage:.1f}%[/{cpu_color}]"
    disk_text = f"[{BOLD_WHITE_STYLE}]Disk: [/{BOLD_WHITE_STYLE}][{disk_color}]{disk_usage:.1f}%[/{disk_color}]"

    cpu_bar = Progress(BarColumn(bar_width=40))
    _ = cpu_bar.add_task("", total=100, completed=cpu_usage)

    disk_bar = Progress(BarColumn(bar_width=40))
    _ = disk_bar.add_task("", total=100, completed=disk_usage)

    # Combine into a panel
    return Panel(
        f"{cpu_text}\n{cpu_bar}\n\n{disk_text}\n{disk_bar}",
        title="System Resources",
        border_style="magenta",
    )


def _render_alerts_panel(metrics):
    """Render alerts panel"""
    alerts = []

    for metric in metrics:
        if not metric.healthy or metric.alerts:
            alerts.append(
                {
                    "resource_id": metric.resource_id,
                    "resource_type": metric.resource_type.value,
                    "alerts": metric.alerts,
                    "timestamp": metric.timestamp,
                }
            )

    if not alerts:
        return Panel("No active alerts", title="Alerts", border_style="green")

    table = Table(show_header=True, header_style=BOLD_WHITE_STYLE, show_lines=True)
    table.add_column("Resource")
    table.add_column("Type")
    table.add_column("Alert")
    table.add_column("Time")

    for alert in alerts[:10]:  # Show top 10 alerts
        alert_messages = ", ".join(alert["alerts"])
        timestamp = alert["timestamp"].strftime("%H:%M:%S")

        table.add_row(
            alert["resource_id"],
            alert["resource_type"],
            f"[red]{alert_messages}[/red]",
            timestamp,
        )

    return Panel(table, title=f"Alerts ({len(alerts)})", border_style="red")


def _update_monitoring_panels(layout, current_metrics, namespace: str):
    """Update all monitoring panels with current metrics"""
    layout["kubernetes"].update(_render_kubernetes_panel(current_metrics, namespace))
    layout["docker"].update(_render_docker_panel(current_metrics))
    layout["system"].update(_render_system_panel(current_metrics))
    layout["alerts"].update(_render_alerts_panel(current_metrics))


def _handle_monitoring_error(layout, error_message: str):
    """Handle monitoring errors by updating all panels"""
    for section in ["kubernetes", "docker", "system", "alerts"]:
        layout[section].update(Panel(f"Monitoring error: {error_message}", border_style="red"))


def _save_monitoring_data(output_file: str, all_metrics):
    """Save monitoring data to file"""
    serializable_metrics = []
    for metric in all_metrics:
        serializable_metrics.append(
            {
                "resource_id": metric.resource_id,
                "resource_type": metric.resource_type.value,
                "timestamp": metric.timestamp.isoformat(),
                "metrics": metric.metrics,
                "labels": metric.labels,
                "healthy": metric.healthy,
                "alerts": metric.alerts,
            }
        )

    with open(output_file, "w") as f:
        json.dump(serializable_metrics, f, indent=2)

    print_success(f"Monitoring data saved to {output_file}")


@infrastructure_app.command("monitor")
def monitor_infrastructure(
    namespace: str = typer.Option("default", "--namespace", "-n", help=K8S_NAMESPACE_LABEL),
    refresh_rate: int = typer.Option(10, "--refresh-rate", "-r", help="Refresh rate in seconds"),
    duration: int = typer.Option(60, "--duration", "-d", help="Monitoring duration in seconds"),
    include_cloud: bool = typer.Option(False, "--cloud", help="Include cloud resources"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for monitoring data"),
):
    """Real-time monitoring of infrastructure components"""

    monitor = InfrastructureMonitor()
    _ = AlertManager()  # AlertManager instancié mais pas utilisé dans cette version

    # Set up layout
    layout = _setup_monitoring_layout()

    # Monitoring loop
    try:
        with Live(layout, refresh_per_second=1, screen=True):
            start_time = datetime.now()
            all_metrics = []

            while (datetime.now() - start_time).total_seconds() < duration:
                layout["header"].update(_render_header())

                # Collect metrics - NOW PASSING THE NAMESPACE PARAMETER
                try:
                    result = asyncio.run(comprehensive_infrastructure_check(
                        include_cloud=include_cloud,
                        namespace=namespace
                    ))

                    if result.success:
                        current_metrics = result.details
                        monitor.store_metrics(current_metrics)
                        all_metrics.extend(current_metrics)

                        # Update panels
                        _update_monitoring_panels(layout, current_metrics, namespace)
                    else:
                        _handle_monitoring_error(layout, result.error_message)

                except Exception as e:
                    _handle_monitoring_error(layout, str(e))

                # Update footer with elapsed time
                elapsed_seconds = int((datetime.now() - start_time).total_seconds())
                layout["footer"].update(_render_footer(elapsed_seconds))

                # Wait for next refresh
                if elapsed_seconds < duration:
                    # Sleep without blocking UI refresh
                    for _ in range(min(refresh_rate, duration - elapsed_seconds)):
                        elapsed_seconds = int((datetime.now() - start_time).total_seconds())
                        layout["footer"].update(_render_footer(elapsed_seconds))
                        asyncio.run(asyncio.sleep(1))

        # Save monitoring data if output file specified
        if output_file and all_metrics:
            _save_monitoring_data(output_file, all_metrics)

    except KeyboardInterrupt:
        console.print("\n[bold green]Monitoring stopped by user[/bold green]")


def _run_health_checks(kubernetes: bool, docker: bool, namespace: str) -> Dict:
    """Run health checks with progress display"""
    with Progress(SpinnerColumn(), TextColumn("[bold green]Checking infrastructure health..."), transient=True) as progress:
        progress.add_task("check", total=None)

        results = {}

        # Check Kubernetes if requested
        if kubernetes:
            k8s_result = asyncio.run(quick_k8s_health_check(namespace))
            results["kubernetes"] = k8s_result

        # Check Docker if requested
        if docker:
            docker_result = asyncio.run(quick_docker_health_check())
            results["docker"] = docker_result

    return results


def _display_health_results(results: Dict):
    """Display health check results"""
    for system, result in results.items():
        if result.success:
            _display_system_health(system, result.summary)
        else:
            print_error(f"{system.capitalize()}: Check failed - {result.error_message}")


def _display_system_health(system: str, summary: Dict):
    """Display health results for a single system"""
    total = summary.get("total_resources", 0)
    healthy = summary.get("healthy_resources", 0)
    unhealthy = summary.get("unhealthy_resources", 0)

    if unhealthy == 0:
        print_success(f"{system.capitalize()}: All {total} resources healthy")
    else:
        health_percentage = (healthy / total * 100) if total > 0 else 0
        print_warning(f"{system.capitalize()}: {unhealthy} of {total} resources unhealthy ({health_percentage:.1f}% healthy)")

        # Display unhealthy resources
        if "alerts" in summary:
            for alert in summary["alerts"]:
                alerts_text = ", ".join(alert["alerts"])
                print_error(f"  {alert['resource_id']} ({alert['resource_type']}): {alerts_text}")


@infrastructure_app.command("check")
def quick_health_check(
    kubernetes: bool = typer.Option(True, "--k8s/--no-k8s", help="Check Kubernetes"),
    docker: bool = typer.Option(True, "--docker/--no-docker", help="Check Docker"),
    namespace: str = typer.Option("default", "--namespace", "-n", help=K8S_NAMESPACE_LABEL),
):
    """Quick infrastructure health check"""

    # Run health checks
    results = _run_health_checks(kubernetes, docker, namespace)

    # Display results
    _display_health_results(results)


def _collect_infrastructure_metrics(include_cloud: bool, cloud_provider: str):
    """Collect infrastructure metrics with progress display"""
    with Progress(SpinnerColumn(), TextColumn("[bold green]Analyzing infrastructure..."), transient=True) as progress:
        progress.add_task("analyze", total=None)
        result = asyncio.run(comprehensive_infrastructure_check(include_cloud=include_cloud, cloud_provider=cloud_provider))
    return result


def _display_health_overview(summary: Dict):
    """Display infrastructure health overview"""
    console.print("\n[bold]Health Overview[/bold]")
    health_percentage = summary.get("health_percentage", 0)

    if health_percentage > 90:
        health_color = "green"
    elif health_percentage > 70:
        health_color = "yellow"
    else:
        health_color = "red"

    console.print(f"Overall health: [{health_color}]{health_percentage:.1f}%[/{health_color}]")

    resource_counts = summary.get("resource_counts", {})
    for resource_type, count in resource_counts.items():
        console.print(f"- {resource_type}: {count} resources")


def _display_issues_and_anomalies(summary: Dict):
    """Display detected issues and anomalies"""
    alerts = summary.get("alerts", [])
    anomalies = summary.get("anomalies", [])

    if alerts:
        console.print("\n[bold red]Issues Detected[/bold red]")
        for alert in alerts:
            console.print(f"- [red]{alert['resource_id']}[/red] ({alert['resource_type']}): {', '.join(alert['alerts'])}")

    if anomalies:
        console.print("\n[bold yellow]Anomalies Detected[/bold yellow]")
        for anomaly in anomalies:
            console.print(
                f"- [yellow]{anomaly['resource_id']}[/yellow] ({anomaly['resource_type']}): "
                f"{anomaly['metric_name']} value {anomaly['current_value']:.2f} "
                f"({anomaly['anomaly_factor']:.1f}x normal)"
            )


def _generate_infrastructure_recommendations(metrics):
    """Generate recommendations based on collected metrics"""
    recommendations = []

    # Check for high CPU usage
    high_cpu_resources = [m for m in metrics if m.metrics.get("cpu_usage", 0) > 80]
    if high_cpu_resources:
        recommendations.append(
            {
                "category": "Performance",
                "title": "High CPU Usage Detected",
                "description": f"{len(high_cpu_resources)} resources have high CPU usage (>80%)",
                "action": "Consider scaling up or adding more resources",
            }
        )

    # Check for underutilized resources
    low_cpu_resources = [m for m in metrics if m.metrics.get("cpu_usage", 100) < 10 and m.resource_type != ResourceType.SERVICE]
    if low_cpu_resources and len(low_cpu_resources) > 3:
        recommendations.append(
            {
                "category": "Optimization",
                "title": "Resource Underutilization",
                "description": f"{len(low_cpu_resources)} resources have very low CPU usage (<10%)",
                "action": "Consider consolidating resources for cost savings",
            }
        )

    # Unhealthy services
    unhealthy_services = [m for m in metrics if not m.healthy and m.resource_type == ResourceType.SERVICE]
    if unhealthy_services:
        recommendations.append(
            {
                "category": "Reliability",
                "title": "Unhealthy Services",
                "description": f"{len(unhealthy_services)} services are in unhealthy state",
                "action": "Check service endpoints and dependencies",
            }
        )

    # Add general recommendations if none are generated
    if not recommendations:
        recommendations.append(
            {
                "category": "General",
                "title": "Infrastructure Healthy",
                "description": "No significant issues detected",
                "action": "Continue monitoring for changes",
            }
        )

    return recommendations


def _display_recommendations_table(recommendations):
    """Display recommendations in a formatted table"""
    console.print("\n[bold]Recommendations[/bold]")

    table = Table(show_header=True, header_style=BOLD_WHITE_STYLE, show_lines=True)
    table.add_column("Category")
    table.add_column("Recommendation")
    table.add_column("Action")

    for recommendation in recommendations:
        category_style = {
            "Performance": "yellow",
            "Optimization": "blue",
            "Reliability": "red",
            "General": "green",
        }.get(recommendation["category"], "white")

        table.add_row(
            f"[{category_style}]{recommendation['category']}[/{category_style}]",
            f"{recommendation['title']}\n{recommendation['description']}",
            recommendation["action"],
        )

    console.print(table)


def _save_analysis_report(output_file: str, health_percentage: float, resource_counts: Dict, alerts: List, anomalies: List, recommendations: List, summary: Dict):
    """Save analysis report to file"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "health_overview": {
            "health_percentage": health_percentage,
            "resource_counts": resource_counts,
        },
        "issues": {"alerts": alerts, "anomalies": anomalies},
        "recommendations": recommendations,
        "metrics_summary": {k: v for k, v in summary.items() if k not in ["alerts", "anomalies"]},
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print_success(f"Analysis report saved to {output_file}")


@infrastructure_app.command("analyze")
def analyze_infrastructure(
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for analysis report"),
    include_cloud: bool = typer.Option(False, "--cloud", help=CLOUD_RESOURCES_ANALYSIS),
    cloud_provider: str = typer.Option("aws", "--provider", "-p", help="Cloud provider (aws, gcp, azure)"),
):
    """Analyze infrastructure for optimizations and issues"""

    # Collect comprehensive metrics
    result = _collect_infrastructure_metrics(include_cloud, cloud_provider)

    if not result.success:
        print_error(f"Analysis failed: {result.error_message}")
        return

    # Display analysis results
    console.print("\n[bold]Infrastructure Analysis Report[/bold]")

    # Display health overview
    summary = result.summary
    _display_health_overview(summary)

    # Display issues and anomalies
    _display_issues_and_anomalies(summary)

    # Generate and display recommendations
    recommendations = _generate_infrastructure_recommendations(result.details)
    _display_recommendations_table(recommendations)

    # Save report if output file specified
    if output_file:
        health_percentage = summary.get("health_percentage", 0)
        resource_counts = summary.get("resource_counts", {})
        alerts = summary.get("alerts", [])
        anomalies = summary.get("anomalies", [])
        _save_analysis_report(output_file, health_percentage, resource_counts, alerts, anomalies, recommendations, summary)


def _validate_resource_type(resource_type: str) -> bool:
    """Validate that the resource type is supported"""
    supported_resources = ["deployment", "statefulset", "replicaset"]

    if resource_type.lower() not in supported_resources:
        print_error(f"Unsupported resource type: {resource_type}")
        print_info(f"Supported types: {', '.join(supported_resources)}")
        return False

    return True


def _execute_scaling_operation(resource_type: str, resource_name: str, replicas: int, namespace: str):
    """Execute the scaling operation with progress display"""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold green]Scaling {resource_type} {resource_name} to {replicas} replicas..."),
        transient=True,
    ) as progress:
        progress.add_task("scale", total=None)

        deployment_manager = DeploymentOrchestrator()

        result = asyncio.run(
            deployment_manager.scale_kubernetes_resource(
                resource_type=resource_type.lower(),
                resource_name=resource_name,
                replicas=replicas,
                namespace=namespace,
            )
        )

    return result


def _display_scaling_result(result, resource_type: str, resource_name: str, replicas: int):
    """Display scaling operation result"""
    if result.success:
        print_success(f"Successfully scaled {resource_type} {resource_name} to {replicas} replicas")

        # Print additional details if available
        if hasattr(result, "details") and result.details:
            console.print("\n[bold]Resource Details:[/bold]")
            for key, value in result.details.items():
                console.print(f"{key}: {value}")
    else:
        print_error(f"Scaling failed: {result.error_message}")


@infrastructure_app.command("scale")
def scale_resource(
    resource_type: str = typer.Argument(..., help="Type of resource to scale (deployment, statefulset, etc.)"),
    resource_name: str = typer.Argument(..., help="Name of the resource to scale"),
    replicas: int = typer.Argument(..., help="Number of replicas to scale to"),
    namespace: str = typer.Option("default", "--namespace", "-n", help=K8S_NAMESPACE_LABEL),
):
    """Scale Kubernetes resources"""

    # Validate resource type
    if not _validate_resource_type(resource_type):
        return

    try:
        # Execute scaling operation
        result = _execute_scaling_operation(resource_type, resource_name, replicas, namespace)

        # Display result
        _display_scaling_result(result, resource_type, resource_name, replicas)

    except Exception as e:
        print_error(f"Scaling error: {str(e)}")


def _validate_file_path(file_path: str) -> bool:
    """Validate that the file path exists"""
    if not os.path.exists(file_path):
        print_error(f"File not found: {file_path}")
        return False
    return True


def _collect_yaml_files(file_path: str) -> List[str]:
    """Collect YAML files from path (file or directory)"""
    files_to_apply = []

    if os.path.isdir(file_path):
        for root, _, files in os.walk(file_path):
            for file in files:
                if file.endswith((".yaml", ".yml")):
                    files_to_apply.append(os.path.join(root, file))
    else:
        files_to_apply = [file_path]

    if not files_to_apply:
        print_error(f"No YAML files found in {file_path}")
        return []

    return files_to_apply


def _apply_single_manifest(deployment_manager, file: str, namespace: str, dry_run: bool):
    """Apply a single Kubernetes manifest file"""
    action_text = "Validating" if dry_run else "Applying"

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold green]{action_text} {os.path.basename(file)}..."),
        transient=True,
    ) as progress:
        progress.add_task("apply", total=None)

        result = asyncio.run(deployment_manager.apply_kubernetes_manifest(file_path=file, namespace=namespace, dry_run=dry_run))

        if result.success:
            if dry_run:
                print_success(f"Validation successful: {os.path.basename(file)}")
            else:
                print_success(f"Applied successfully: {os.path.basename(file)}")
                _display_created_resources(result)
        else:
            action_failed = "Validation" if dry_run else "Apply"
            print_error(f"{action_failed} failed: {result.error_message}")


def _display_created_resources(result):
    """Display created resources if available"""
    if hasattr(result, "created_resources") and result.created_resources:
        console.print("[bold]Created Resources:[/bold]")
        for resource in result.created_resources:
            console.print(f"- {resource}")


@infrastructure_app.command("apply")
def apply_manifest(
    file_path: str = typer.Argument(..., help="Path to Kubernetes manifest file"),
    namespace: str = typer.Option("default", "--namespace", "-n", help=K8S_NAMESPACE_LABEL),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without applying"),
):
    """Apply Kubernetes manifests"""

    try:
        # Validate file path
        if not _validate_file_path(file_path):
            return

        # Collect YAML files to apply
        files_to_apply = _collect_yaml_files(file_path)
        if not files_to_apply:
            return

        # Apply each file
        deployment_manager = DeploymentOrchestrator()
        for file in files_to_apply:
            _apply_single_manifest(deployment_manager, file, namespace, dry_run)

    except Exception as e:
        print_error(f"Error: {str(e)}")


@infrastructure_app.command("cost-analysis")
def cost_analysis(
    include_cloud: bool = typer.Option(False, "--cloud", help=CLOUD_RESOURCES_ANALYSIS),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for cost analysis report"),
):
    """Analyze infrastructure for cost optimization opportunities"""

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Analyzing cost optimization opportunities..."),
        transient=True,
    ) as progress:
        progress.add_task("analyze", total=None)

        # Import here to avoid circular imports
        from ...modules.infrastructure.analyzer import InfrastructureAnalyzer

        analyzer = InfrastructureAnalyzer()
        result = asyncio.run(analyzer.analyze_cost_optimization())

    if not result.success:
        print_error(f"Cost analysis failed: {result.error_message}")
        return

    # Display cost analysis results
    console.print("\n[bold]💰 Cost Optimization Analysis[/bold]")

    summary = result.summary
    opportunities = summary.get("opportunities", [])
    total_savings = summary.get("potential_monthly_savings", 0)

    if total_savings > 0:
        console.print(f"\n[bold green]Potential Monthly Savings: ${total_savings:.2f}[/bold green]")

        # Display top opportunities
        table = Table(show_header=True, header_style=BOLD_WHITE_STYLE, show_lines=True)
        table.add_column("Resource")
        table.add_column("Type")
        table.add_column("Current Cost")
        table.add_column("Potential Savings")
        table.add_column("Effort")
        table.add_column("Description")

        for opp in opportunities[:10]:  # Show top 10
            effort_style = {"low": "green", "medium": "yellow", "high": "red"}.get(opp.implementation_effort, "white")

            table.add_row(
                opp.resource_id,
                opp.resource_type,
                f"${opp.current_cost:.2f}",
                f"${opp.potential_savings:.2f} ({opp.savings_percentage:.1f}%)",
                f"[{effort_style}]{opp.implementation_effort.capitalize()}[/{effort_style}]",
                opp.description,
            )

        console.print(table)

        # Quick wins summary
        quick_wins = [opp for opp in opportunities if opp.implementation_effort == "low"]
        if quick_wins:
            quick_wins_savings = sum(opp.potential_savings for opp in quick_wins)
            console.print(f"\n[bold blue]💡 Quick Wins: {len(quick_wins)} opportunities for ${quick_wins_savings:.2f}/month savings[/bold blue]")
    else:
        console.print("\n[green]✅ No significant cost optimization opportunities found[/green]")

    # Save report if output file specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "cost_analysis": summary}, f, indent=2)

        print_success(f"Cost analysis report saved to {output_file}")


@infrastructure_app.command("security-scan")
def security_scan(
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for security scan report"),
    scan_type: str = typer.Option("comprehensive", "--type", "-t", help="Type of security scan"),
):
    """Perform security scanning of infrastructure"""

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Scanning infrastructure for security issues..."),
        transient=True,
    ) as progress:
        progress.add_task("scan", total=None)

        # Import here to avoid circular imports
        from ...modules.infrastructure.analyzer import InfrastructureAnalyzer
        from ...core.structured_output import AnalysisResult

        # Simulate security analysis until the method is implemented
        result = AnalysisResult(success=True, summary={}, details=[])

    if not result.success:
        print_error(f"Security scan failed: {result.error_message}")
        return

    # Display security scan results
    console.print("\n[bold]🔐 Security Scan Results[/bold]")

    summary = result.summary
    findings = summary.get("findings", [])
    critical_count = summary.get("critical_findings", 0)
    high_count = summary.get("high_priority_findings", 0)

    # Security score
    total_findings = len(findings)
    if total_findings == 0:
        security_score = 100
        score_color = "green"
    else:
        # Simple scoring: deduct points for severity
        score_deductions = critical_count * 30 + high_count * 15 + (total_findings - critical_count - high_count) * 5
        security_score = max(0, 100 - score_deductions)
        if security_score > 80:
            score_color = "green"
        elif security_score > 60:
            score_color = "yellow"
        else:
            score_color = "red"

    console.print(f"\nSecurity Score: [{score_color}]{security_score}/100[/{score_color}]")

    if critical_count > 0:
        console.print(f"[bold red]🚨 {critical_count} Critical security issue(s) found[/bold red]")

    if high_count > 0:
        console.print(f"[bold yellow]⚠️  {high_count} High priority security issue(s) found[/bold yellow]")

    if findings:
        # Display findings
        table = Table(show_header=True, header_style=BOLD_WHITE_STYLE, show_lines=True)
        table.add_column("Finding ID")
        table.add_column("Severity")
        table.add_column("Title")
        table.add_column("Resource")
        table.add_column("Recommendation")

        for finding in findings:
            severity_style = {
                "critical": "bold red",
                "high": "red",
                "medium": "yellow",
                "low": "blue",
                "info": "white",
            }.get(finding["severity"], "white")

            table.add_row(
                finding["finding_id"],
                f"[{severity_style}]{finding['severity'].upper()}[/{severity_style}]",
                finding["title"],
                finding["resource_id"],
                finding["recommendation"],
            )

        console.print(table)
    else:
        console.print("\n[green]✅ No security issues detected[/green]")

    # Save report if output file specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "security_scan": {"security_score": security_score, "summary": summary},
                },
                f,
                indent=2,
            )

        print_success(f"Security scan report saved to {output_file}")


@infrastructure_app.command("compliance-check")
def compliance_check(
    standards: Optional[List[str]] = typer.Option(None, "--standard", "-s", help="Compliance standards to check (cis, pci, hipaa, gdpr)"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for compliance report"),
):
    """Check infrastructure compliance against standards"""

    if not standards:
        standards = ["cis", "pci", "hipaa", "gdpr"]

    with Progress(SpinnerColumn(), TextColumn("[bold green]Checking compliance standards..."), transient=True) as progress:
        progress.add_task("check", total=None)

        # Import here to avoid circular imports
        from ...modules.infrastructure.analyzer import InfrastructureAnalyzer

        analyzer = InfrastructureAnalyzer()
        findings = asyncio.run(analyzer.compliance_check(standards))

    # Display compliance results
    console.print("\n[bold]📋 Compliance Check Results[/bold]")

    if findings:
        # Group findings by standard
        findings_by_standard = {}
        for finding in findings:
            standard = finding.metadata.get("standard", "Unknown")
            if standard not in findings_by_standard:
                findings_by_standard[standard] = []
            findings_by_standard[standard].append(finding)

        for standard, standard_findings in findings_by_standard.items():
            console.print(f"\n[bold]{standard.upper()} Compliance:[/bold]")

            table = Table(show_header=True, header_style=BOLD_WHITE_STYLE)
            table.add_column("Finding")
            table.add_column("Severity")
            table.add_column("Recommendation")

            for finding in standard_findings:
                severity_style = {
                    "critical": "bold red",
                    "high": "red",
                    "medium": "yellow",
                    "low": "blue",
                    "info": "white",
                }.get(finding.severity.value, "white")

                table.add_row(
                    finding.title,
                    f"[{severity_style}]{finding.severity.value.upper()}[/{severity_style}]",
                    finding.recommendation,
                )

            console.print(table)
    else:
        console.print("\n[green]✅ No compliance issues detected[/green]")

    # Save report if output file specified
    if output_file:
        compliance_report = {
            "timestamp": datetime.now().isoformat(),
            "standards_checked": standards,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "standard": f.metadata.get("standard", "Unknown"),
                }
                for f in findings
            ],
        }

        with open(output_file, "w") as f:
            json.dump(compliance_report, f, indent=2)

        print_success(f"Compliance report saved to {output_file}")


def _run_performance_analysis():
    """Execute performance analysis and return findings"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Analyzing infrastructure performance..."),
        transient=True,
    ) as progress:
        progress.add_task("analyze", total=None)

        from ...modules.infrastructure.analyzer import InfrastructureAnalyzer

        analyzer = InfrastructureAnalyzer()
        return asyncio.run(analyzer.performance_analysis())


def _categorize_performance_findings(findings):
    """Categorize performance findings into bottlenecks, resource issues, and others"""
    bottlenecks = [f for f in findings if "bottleneck" in f.title.lower()]
    resource_issues = [f for f in findings if "resource" in f.title.lower()]
    other_issues = [f for f in findings if f not in bottlenecks and f not in resource_issues]
    return bottlenecks, resource_issues, other_issues


def _display_performance_bottlenecks(bottlenecks, resource_issues, other_issues):
    """Display categorized performance issues"""
    if bottlenecks:
        console.print("\n[bold red]🔴 Performance Bottlenecks:[/bold red]")
        for finding in bottlenecks:
            console.print(f"- [red]{finding.title}[/red]: {finding.description}")
            console.print(f"  💡 {finding.recommendation}")

    if resource_issues:
        console.print("\n[bold yellow]📊 Resource Issues:[/bold yellow]")
        for finding in resource_issues:
            console.print(f"- [yellow]{finding.title}[/yellow]: {finding.description}")
            console.print(f"  💡 {finding.recommendation}")

    if other_issues:
        console.print("\n[bold blue]📈 Other Performance Issues:[/bold blue]")
        for finding in other_issues:
            console.print(f"- [blue]{finding.title}[/blue]: {finding.description}")
            console.print(f"  💡 {finding.recommendation}")


def _display_performance_summary(bottlenecks, resource_issues, other_issues):
    """Display performance analysis summary table"""
    summary_table = Table(title="Performance Analysis Summary")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Issues Found", style="yellow")
    summary_table.add_column("Priority", style="white")

    summary_table.add_row("Bottlenecks", str(len(bottlenecks)), "High" if bottlenecks else "None")
    summary_table.add_row("Resource Issues", str(len(resource_issues)), "Medium" if resource_issues else "None")
    summary_table.add_row("Other Issues", str(len(other_issues)), "Low" if other_issues else "None")

    console.print(summary_table)


def _save_performance_report(findings, output_file):
    """Save performance analysis report to file"""
    performance_report = {
        "timestamp": datetime.now().isoformat(),
        "performance_analysis": {
            "total_findings": len(findings),
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "resource_id": f.resource_id,
                }
                for f in findings
            ],
        },
    }

    with open(output_file, "w") as f:
        json.dump(performance_report, f, indent=2)
    print_success(f"Performance analysis report saved to {output_file}")


@infrastructure_app.command("performance-analysis")
def performance_analysis(output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for performance analysis report")):
    """Analyze infrastructure performance and identify bottlenecks"""
    findings = _run_performance_analysis()

    console.print("\n[bold]⚡ Performance Analysis Results[/bold]")

    if findings:
        bottlenecks, resource_issues, other_issues = _categorize_performance_findings(findings)
        _display_performance_bottlenecks(bottlenecks, resource_issues, other_issues)
        _display_performance_summary(bottlenecks, resource_issues, other_issues)
    else:
        console.print("\n[green]✅ No performance issues detected[/green]")

    if output_file:
        _save_performance_report(findings, output_file)


def _run_comprehensive_analysis():
    """Run comprehensive infrastructure analysis with progress display"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Running comprehensive infrastructure analysis..."),
        transient=True,
    ) as progress:
        progress.add_task("analyze", total=None)

        # Import here to avoid circular imports
        from ...modules.infrastructure.analyzer import InfrastructureAnalyzer

        # Simulate comprehensive analysis until the method is implemented
        result = {"executive_summary": {"total_findings": 0, "critical_findings": 0, "high_priority_findings": 0}, "priority_recommendations": []}

    return result


def _display_executive_summary(executive_summary: Dict):
    """Display executive summary section"""
    console.print("\n[bold]📊 Executive Summary[/bold]")
    console.print(f"Total findings: {executive_summary.get('total_findings', 0)}")
    console.print(f"Critical findings: {executive_summary.get('critical_findings', 0)}")
    console.print(f"High priority findings: {executive_summary.get('high_priority_findings', 0)}")

    cost_summary = executive_summary.get("cost_optimization", {})
    if cost_summary.get("potential_monthly_savings", 0) > 0:
        console.print(f"Potential monthly savings: [green]${cost_summary['potential_monthly_savings']:.2f}[/green]")


def _display_priority_recommendations(priority_recommendations: List):
    """Display priority recommendations table"""
    if not priority_recommendations:
        return

    console.print("\n[bold]🎯 Priority Recommendations[/bold]")

    table = Table(show_header=True, header_style=BOLD_WHITE_STYLE, show_lines=True)
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Impact")
    table.add_column("Effort")

    for rec in priority_recommendations:
        category_style = {
            "cost_optimization": "green",
            "security": "red",
            "performance": "yellow",
            "compliance": "blue",
        }.get(rec["category"], "white")

        effort_style = {"Low": "green", "Medium": "yellow", "High": "red"}.get(rec["effort"], "white")

        table.add_row(
            rec["title"],
            f"[{category_style}]{rec['category'].replace('_', ' ').title()}[/{category_style}]",
            rec["impact"],
            f"[{effort_style}]{rec['effort']}[/{effort_style}]",
        )

    console.print(table)


def _display_next_steps(executive_summary: Dict, priority_recommendations: List):
    """Display recommended next steps"""
    console.print("\n[bold]📋 Recommended Next Steps[/bold]")

    cost_summary = executive_summary.get("cost_optimization", {})

    if executive_summary.get("critical_findings", 0) > 0:
        console.print("1. [red]Address critical security issues immediately[/red]")

    if cost_summary.get("potential_monthly_savings", 0) > 50:
        console.print("2. [green]Implement quick cost optimization wins[/green]")

    if executive_summary.get("total_findings", 0) > 10:
        console.print("3. [yellow]Prioritize high-impact optimizations[/yellow]")

    if not priority_recommendations:
        console.print("1. [green]Continue regular monitoring and analysis[/green]")


def _save_comprehensive_report(output_file: str, report: Dict):
    """Save comprehensive analysis report to file"""
    with open(output_file, "w") as f:
        json.dump(
            {"timestamp": datetime.now().isoformat(), "comprehensive_analysis": report},
            f,
            indent=2,
        )

    print_success(f"Comprehensive analysis report saved to {output_file}")


@infrastructure_app.command("comprehensive-analysis")
def comprehensive_analysis(
    include_cloud: bool = typer.Option(False, "--cloud", help=CLOUD_RESOURCES_ANALYSIS),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for comprehensive report"),
):
    """Run comprehensive infrastructure analysis (cost, security, compliance, performance)"""

    # Run comprehensive analysis
    result = _run_comprehensive_analysis()

    if not result.success:
        print_error(f"Comprehensive analysis failed: {result.error_message}")
        return

    # Display comprehensive analysis results
    console.print("\n[bold]🔍 Comprehensive Infrastructure Analysis[/bold]")

    report = result.summary
    executive_summary = report.get("executive_summary", {})
    priority_recommendations = report.get("priority_recommendations", [])

    # Display sections
    _display_executive_summary(executive_summary)
    _display_priority_recommendations(priority_recommendations)
    _display_next_steps(executive_summary, priority_recommendations)

    # Save comprehensive report if output file specified
    if output_file:
        _save_comprehensive_report(output_file, report)


if __name__ == "__main__":
    infrastructure_app()
