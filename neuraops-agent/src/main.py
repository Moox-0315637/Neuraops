"""NeuraOps Agent CLI - Main entry point."""

import asyncio
import sys
import typer
from pathlib import Path
from typing import Optional

from .agent import Agent, daemonize, is_agent_running, stop_agent
from .config import AgentConfig, save_config_value, get_config_path, NEURAOPS_DIR_NAME


app = typer.Typer(
    name="neuraops-agent",
    help="NeuraOps Agent - Lightweight connector to NeuraOps Core",
    no_args_is_help=True
)


@app.command()
def start(
    core_url: Optional[str] = typer.Option(None, help="NeuraOps Core URL"),
    token: Optional[str] = typer.Option(None, help="Agent authentication token"),
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run as daemon"),
    name: Optional[str] = typer.Option(None, help="Agent name")
):
    """Start the NeuraOps Agent and connect to Core."""
    
    # Update config if parameters provided
    if core_url:
        save_config_value("neuraops_core_url", core_url)
        typer.echo(f"Core URL set to: {core_url}")
    
    if token:
        save_config_value("neuraops_auth_token", token)
        typer.echo("Authentication token saved")
    
    if name:
        save_config_value("neuraops_agent_name", name)
        typer.echo(f"Agent name set to: {name}")
    
    # Check if already running
    if is_agent_running():
        typer.echo("❌ Agent is already running", err=True)
        typer.echo("Use 'neuraops-agent stop' to stop it first")
        sys.exit(1)
    
    try:
        config = AgentConfig()
        
        # Validate configuration
        if not config.core_url:
            typer.echo("❌ Core URL not configured", err=True)
            typer.echo("Use: neuraops-agent start --core-url <url>")
            sys.exit(1)
        
        typer.echo(f"Starting NeuraOps Agent '{config.agent_name}'...")
        typer.echo(f"Connecting to Core: {config.core_url}")
        
        if daemon:
            typer.echo("Running as daemon...")
            # Save PID file
            pid_file = Path.home() / NEURAOPS_DIR_NAME / "agent.pid"
            pid_file.parent.mkdir(exist_ok=True)
            
            daemonize()
            
            import os
            pid_file.write_text(str(os.getpid()))
        
        # Start agent
        agent = Agent(config)
        asyncio.run(agent.start())
        
    except KeyboardInterrupt:
        typer.echo("\nAgent stopped by user")
    except Exception as e:
        typer.echo(f"❌ Failed to start agent: {e}", err=True)
        sys.exit(1)


@app.command()
def stop():
    """Stop the running NeuraOps Agent."""
    if not is_agent_running():
        typer.echo("❌ Agent is not running")
        sys.exit(1)
    
    try:
        stop_agent()
        typer.echo("✅ Agent stopped successfully")
    except Exception as e:
        typer.echo(f"❌ Failed to stop agent: {e}", err=True)
        sys.exit(1)


@app.command()
def status():
    """Check NeuraOps Agent status."""
    config = AgentConfig()
    
    typer.echo("NeuraOps Agent Status")
    typer.echo(f"Agent Name: {config.agent_name}")
    typer.echo(f"Core URL: {config.core_url}")
    typer.echo()
    
    if is_agent_running():
        typer.echo("✅ Status: Running")
        
        # Show PID if available
        pid_file = Path.home() / NEURAOPS_DIR_NAME / "agent.pid"
        if pid_file.exists():
            try:
                pid = pid_file.read_text().strip()
                typer.echo(f"   PID: {pid}")
            except (OSError, UnicodeDecodeError):  # S5754: Specify exception types instead of generic except
                # Silent fail - PID display is non-critical for status command
                pass
    else:
        typer.echo("❌ Status: Stopped")


@app.command()
def config(
    core_url: Optional[str] = typer.Option(None, help="Set Core URL"),
    token: Optional[str] = typer.Option(None, help="Set authentication token"),
    name: Optional[str] = typer.Option(None, help="Set agent name"),
    show: bool = typer.Option(False, help="Show current configuration")
):
    """Configure the NeuraOps Agent."""
    
    if show:
        config = AgentConfig()
        typer.echo("Current Configuration:")
        typer.echo(f"  Core URL: {config.core_url}")
        typer.echo(f"  Agent Name: {config.agent_name}")
        typer.echo(f"  Auth Token: {'***' if config.auth_token else 'Not set'}")
        typer.echo(f"  Config File: {get_config_path()}")
        return
    
    changed = False
    
    if core_url:
        save_config_value("neuraops_core_url", core_url)
        typer.echo(f"✅ Core URL set to: {core_url}")
        changed = True
    
    if token:
        save_config_value("neuraops_auth_token", token)
        typer.echo("✅ Authentication token saved")
        changed = True
    
    if name:
        save_config_value("neuraops_agent_name", name)
        typer.echo(f"✅ Agent name set to: {name}")
        changed = True
    
    if not changed:
        typer.echo("No configuration changes made")
        typer.echo("Use --help to see available options")


@app.command()
def logs(
    lines: int = typer.Option(50, help="Number of log lines to show"),
    follow: bool = typer.Option(False, "-f", help="Follow log output")
):
    """Show agent logs."""
    config = AgentConfig()
    
    if not config.log_file:
        typer.echo("❌ Log file not configured", err=True)
        typer.echo("Logs are sent to stdout when running in foreground mode")
        sys.exit(1)
    
    log_path = Path(config.log_file)
    if not log_path.exists():
        typer.echo(f"❌ Log file not found: {log_path}", err=True)
        sys.exit(1)
    
    try:
        if follow:
            # Simple tail -f implementation
            import subprocess
            subprocess.run(["tail", "-f", str(log_path)])
        else:
            # Show last N lines
            import subprocess
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                typer.echo(result.stdout)
            else:
                typer.echo(f"❌ Error reading logs: {result.stderr}", err=True)
    
    except FileNotFoundError:
        typer.echo("❌ 'tail' command not found", err=True)
    except KeyboardInterrupt:
        pass


@app.command()
def version():
    """Show NeuraOps Agent version."""
    from . import __version__
    typer.echo(f"NeuraOps Agent v{__version__}")


if __name__ == "__main__":
    app()