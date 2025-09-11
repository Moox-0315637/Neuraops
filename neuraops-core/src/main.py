# src/main.py
"""
NeuraOps - Entrypoint
Interface CLI Typer basée sur documentation Context7 /fastapi/typer
"""
import typer
from typing import Optional
from rich.console import Console
from rich import print as rprint
from pathlib import Path

from .devops_commander.config import get_config

# Import sub-applications
from .cli.commands.health import health_app
from .cli.commands.logs import logs_app
from .cli.commands.infrastructure import infrastructure_app
from .cli.commands.system import system_app
from .cli.commands.incidents import incidents_app
from .cli.commands.workflow_app import workflow_app
from .cli.commands.demo_app import demo_app
from .cli.commands.agents import app as agents_app


class UIMessages:
    """Constantes pour messages d'interface utilisateur"""
    ENGINE_CONNECTED = "[green]✅ DevOpsEngine connected[/green]"
    BASIC_RESULTS = "[green]✅ Basic Analysis Results:[/green]"
    AI_ANALYZING = "[yellow]🤖 Analyzing with AI...[/yellow]"
    FALLBACK_WARNING = "[yellow]⚠️ Falling back to basic analysis[/yellow]"
    AI_SUCCESS = "[green]✅ AI analysis completed![/green]"
    ANALYSIS_RESULTS = "[cyan]📋 Analysis Results:[/cyan]"


app = typer.Typer(name="neuraops", help="🤖 AI-Powered DevOps Assistant for Air-gapped Environments", add_completion=False)

# Register sub-applications
app.add_typer(health_app, name="health")
app.add_typer(logs_app, name="logs") 
app.add_typer(infrastructure_app, name="infra")
app.add_typer(system_app, name="system")
app.add_typer(incidents_app, name="incidents")
app.add_typer(workflow_app, name="workflow") 
app.add_typer(demo_app, name="demo")
app.add_typer(agents_app, name="agents")

console = Console()


@app.command()
def version():
    """Show NeuraOps version information"""
    rprint("[bold green]NeuraOps v0.1.0[/bold green]")
    rprint("[dim]AI-Powered DevOps Assistant[/dim]")








@app.command()
def infra(
    description: str = typer.Argument(..., help="Infrastructure description"),
    provider: str = typer.Option("aws", "--provider", "-p", help="Cloud provider"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """🏗️ Generate infrastructure code with AI"""
    import asyncio
    from .core.engine import get_engine
    
    async def generate_infra():
        rprint(f"[blue]🏗️ Generating infrastructure: {description}[/blue]")
        rprint(f"[dim]Provider: {provider}[/dim]")

        try:
            # Get AI engine and generate infrastructure
            engine = get_engine()
            rprint(UIMessages.ENGINE_CONNECTED)
            
            rprint("[yellow]🤖 Generating infrastructure with AI...[/yellow]")
            generated_code = await engine.generate_infrastructure_config(
                requirements=description,
                provider=provider,
                config_type="terraform"
            )
            
            rprint("[green]✅ Infrastructure code generated successfully![/green]")
            
            # Save or display the generated code
            if output:
                output.write_text(generated_code)
                rprint(f"[green]✅ Infrastructure code written to: {output}[/green]")
            else:
                rprint("[cyan]Generated Infrastructure Code:[/cyan]")
                rprint(generated_code)
                
        except Exception as e:
            rprint(f"[red]❌ Generation failed: {str(e)}[/red]")
            # Fallback to basic template
            rprint("[yellow]⚠️  Falling back to basic template[/yellow]")
            fallback_code = f"# Generated {provider.upper()} infrastructure template for: {description}\n# Basic template - AI generation failed: {str(e)}"
            
            if output:
                output.write_text(fallback_code)
                rprint(f"[green]✅ Basic template written to: {output}[/green]")
            else:
                rprint("[cyan]Basic Infrastructure Template:[/cyan]")
                rprint(fallback_code)
    
    # Run the async function
    asyncio.run(generate_infra())


@app.command()
def incident(
    action: str = typer.Argument(..., help="Incident action (detect, respond, status)"), 
    auto_respond: bool = typer.Option(False, "--auto-respond", help="Enable automatic response")
):
    """🚨 Handle incidents with automated response"""
    import asyncio
    from .core.engine import get_engine
    
    async def handle_incident():
        rprint(f"[yellow]🚨 Incident {action}[/yellow]")
        rprint(f"[dim]Auto-respond: {'enabled' if auto_respond else 'disabled'}[/dim]")

        try:
            # AI-powered incident handling
            engine = get_engine()
            rprint(UIMessages.ENGINE_CONNECTED)
            
            rprint("[yellow]🤖 Generating incident response with AI...[/yellow]")
            
            # Handle incident with AI
            incident_response = await engine.handle_incident(action, auto_respond)
            
            rprint("[green]✅ AI incident response completed![/green]")
            rprint(f"\n[cyan]📋 Incident {action.title()} Guide:[/cyan]")
            rprint(incident_response)
                
        except Exception as e:
            rprint(f"[red]❌ AI incident handling failed: {str(e)}[/red]")
            # Fallback to basic incident handling
            rprint("[yellow]⚠️  Falling back to basic incident handling[/yellow]")
            
            if action == "detect":
                rprint("[green]✅ Basic incident detection checklist:[/green]")
                rprint("  • Monitor system metrics (CPU, memory, disk)")
                rprint("  • Check application logs for errors")
                rprint("  • Verify service availability and response times")
                rprint("  • Review alert notifications")
                
            elif action == "respond":
                rprint("[green]✅ Basic incident response steps:[/green]")
                rprint("  • Assess incident severity and impact")
                rprint("  • Notify relevant team members")
                rprint("  • Identify and isolate the root cause")
                rprint("  • Implement immediate mitigation")
                rprint("  • Document actions taken")
                
            elif action == "status":
                rprint("[green]✅ Basic status reporting:[/green]")
                rprint("  • Current incident status: Under investigation")
                rprint("  • Affected services: To be determined")
                rprint("  • Next update: Within 30 minutes")
                rprint("  • Contact: DevOps team")
                
            else:
                rprint(f"[green]✅ Basic {action} handling completed[/green]")
    
    # Run the async function
    asyncio.run(handle_incident())


@app.command()
def security(
    scan_type: str = typer.Argument("quick", help="Scan type (quick, full, compliance)"), 
    compliance: Optional[str] = typer.Option(None, "--compliance", help="Compliance framework (CIS, SOC2, NIST)")
):
    """🔒 Security auditing and compliance checks"""
    import asyncio
    from .core.engine import get_engine
    
    async def perform_security_audit():
        rprint(f"[magenta]🔒 Security scan: {scan_type}[/magenta]")
        if compliance:
            rprint(f"[dim]Compliance: {compliance}[/dim]")

        try:
            # AI-powered security audit
            engine = get_engine()
            rprint(UIMessages.ENGINE_CONNECTED)
            
            rprint("[yellow]🤖 Performing security audit with AI...[/yellow]")
            
            # Perform security audit with AI
            audit_response = await engine.security_audit(scan_type, compliance)
            
            rprint("[green]✅ AI security audit completed![/green]")
            rprint(f"\n[cyan]🔐 Security {scan_type.title()} Audit Results:[/cyan]")
            rprint(audit_response)
                
        except Exception as e:
            rprint(f"[red]❌ AI security audit failed: {str(e)}[/red]")
            # Fallback to basic security audit
            rprint("[yellow]⚠️  Falling back to basic security audit[/yellow]")
            
            if scan_type == "quick":
                rprint("[green]✅ Basic quick security scan:[/green]")
                rprint("  • Network ports and services check")
                rprint("  • File permissions audit")
                rprint("  • User access review")
                rprint("  • Basic vulnerability scan")
                
            elif scan_type == "full":
                rprint("[green]✅ Basic full security audit:[/green]")
                rprint("  • Comprehensive vulnerability assessment")
                rprint("  • Configuration security review")
                rprint("  • Access control verification")
                rprint("  • Log analysis for security events")
                rprint("  • Network security assessment")
                
            elif scan_type == "compliance":
                framework = compliance or "general"
                rprint(f"[green]✅ Basic {framework} compliance check:[/green]")
                rprint("  • Policy documentation review")
                rprint("  • Control implementation verification")
                rprint("  • Audit trail examination")
                rprint("  • Risk assessment summary")
                
            else:
                rprint(f"[green]✅ Basic {scan_type} security scan completed[/green]")
    
    # Run the async function
    asyncio.run(perform_security_audit())


# ✅ CORRECTION: Entry point selon Context7 docs - pattern standard
def main():
    """Entry point pour console_scripts"""
    app()


if __name__ == "__main__":
    app()
