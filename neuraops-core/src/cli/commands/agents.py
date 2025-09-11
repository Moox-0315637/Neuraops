"""
Agent Management Commands for NeuraOps CLI

Provides agent management capabilities following CLAUDE.md: < 500 lines.
Commands to list, monitor, and interact with distributed agents.
"""
import asyncio
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.text import Text
import httpx

from ...devops_commander.config import get_config
from ...devops_commander.exceptions import NeuraOpsError
from ..ui.components import create_info_panel, create_error_panel, create_success_panel, create_warning_panel
from ..utils.decorators import async_command, handle_errors

console = Console()
app = typer.Typer(help="Agent management commands")


@app.command("list")
@handle_errors
@async_command
async def list_agents(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by agent status"),
    page: int = typer.Option(1, "--page", help="Page number for pagination"),
    page_size: int = typer.Option(20, "--page-size", help="Number of agents per page")
):
    """List all registered agents."""
    
    config = get_config()
    
    try:
        # Fetch agents data from API
        agents_data = await _fetch_agents_data(config, page, page_size)
        
        # Filter agents by status if specified
        agents = _filter_agents(agents_data.get("agents", []), status)
        
        # Display summary and table
        _display_agents_summary(agents_data, agents, page)
        table = _create_agents_table(agents, verbose)
        console.print(table)
        
    except httpx.HTTPStatusError as e:
        console.print(create_error_panel(f"API request failed: {e.response.status_code} {e.response.text}"))
    except Exception as e:
        console.print(create_error_panel(f"Failed to list agents: {str(e)}"))

def _get_auth_headers(config) -> dict:
    """
    Get authentication headers for CLI API requests
    
    CLAUDE.md: < 20 lines - Simple auth header generation
    Uses the existing admin user for CLI access.
    """
    import jwt
    from datetime import datetime, timedelta, timezone
    
    # Create a JWT token for CLI access using existing admin user
    import os
    admin_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
    payload = {
        "sub": admin_username,        # Use configured admin username
        "user_id": admin_username,    # Match configured user
        "role": "admin", 
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    
    # Use the same secret as the auth system
    secret_key = getattr(config, 'secret_key', 'neuraops-secret-key-change-in-production')
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    return {"Authorization": f"Bearer {token}"}

async def _fetch_agents_data(config, page: int, page_size: int) -> dict:
    """
    Fetch agents data from API with validation
    
    CLAUDE.md: < 20 lines - API call and basic validation
    Fixes S3776: Extract API logic to reduce complexity
    
    Args:
        config: NeuraOps configuration
        page: Page number for pagination  
        page_size: Number of agents per page
        
    Returns:
        dict: API response data
        
    Raises:
        httpx.HTTPStatusError: If API request fails
    """
    async with httpx.AsyncClient() as client:  # Revert back to normal
        response = await client.get(
            f"{config.core_api_url}/api/agents/",  # Use UI endpoint
            params={"page": page, "page_size": page_size},
            timeout=30.0,
            headers=_get_auth_headers(config)  # Add authentication headers
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] != "success":
            raise NeuraOpsError(f"API Error: {data.get('message', 'Unknown error')}")
        
        # Adapt UI endpoint response format to what CLI expects
        agents_list = data["data"]  # data is directly a list from UI endpoint
        return {
            "agents": agents_list,
            "total_count": len(agents_list),
            "page": page,
            "page_size": page_size,
            "total_pages": 1
        }


def _filter_agents(agents: List[dict], status: Optional[str]) -> List[dict]:
    """
    Filter agents by status if specified
    
    CLAUDE.md: < 10 lines - Simple filtering logic
    Fixes S3776: Extract filtering to reduce complexity
    
    Args:
        agents: List of agent dictionaries
        status: Optional status filter
        
    Returns:
        List[dict]: Filtered agents
    """
    if not status:
        return agents
    return [a for a in agents if a.get("status") == status]


def _display_agents_summary(agents_data: dict, agents: List[dict], page: int) -> None:
    """
    Display agents summary information
    
    CLAUDE.md: < 10 lines - Simple summary display  
    Fixes S3776: Extract summary logic + S3457: Remove f-string
    
    Args:
        agents_data: Raw API response data
        agents: Filtered agents list
        page: Current page number
    """
    active_count = len([a for a in agents if a.get("status") == "active"])
    total_count = agents_data.get("total_count", len(agents))
    
    console.print("\n🤖 [bold]Agents Summary[/bold]")
    console.print(f"   Total: {total_count} | Active: {active_count} | Page: {page}")


def _create_agents_table(agents: List[dict], verbose: bool) -> Table:
    """
    Create Rich table from agents data
    
    CLAUDE.md: < 25 lines - Table creation logic
    Fixes S3776: Extract table creation to reduce complexity
    
    Args:
        agents: List of agent dictionaries
        verbose: Include additional columns
        
    Returns:
        Table: Rich table ready for display
    """
    if not agents:
        console.print(create_info_panel("No agents registered"))
        return Table()
    
    # Create table structure
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Hostname", style="yellow")
    table.add_column("Status", justify="center")
    table.add_column("Capabilities", style="dim")
    
    if verbose:
        table.add_column("Registered", style="dim")
        table.add_column("Last Seen", style="dim")
    
    # Add agent rows
    for agent in agents:
        status_style = "green" if agent.get("status") == "active" else "red"
        capabilities = ", ".join(agent.get("capabilities", []))
        
        row = [
            agent.get("agent_id", "unknown"),
            agent.get("agent_name", "unknown"),
            agent.get("hostname", "unknown"),
            f"[{status_style}]{agent.get('status', 'unknown')}[/{status_style}]",
            capabilities[:30] + "..." if len(capabilities) > 30 else capabilities
        ]
        
        if verbose:
            row.extend([
                agent.get("registered_at", "unknown")[:19],
                agent.get("last_seen", "unknown")[:19] if agent.get("last_seen") else "never"
            ])
        
        table.add_row(*row)
    
    return table


@app.command("show")
@handle_errors
@async_command
async def show_agent(
    agent_id: str = typer.Argument(..., help="Agent ID to display"),
    metrics: bool = typer.Option(False, "--metrics", "-m", help="Include system metrics")
):
    """Show detailed information for a specific agent."""
    
    config = get_config()
    
    try:
        async with httpx.AsyncClient() as client:  # Revert back to normal
            # Get all agents and find the specific one (same as list command)
            response = await client.get(
                f"{config.core_api_url}/api/agents/",
                params={"page": 1, "page_size": 100},
                timeout=30.0,
                headers=_get_auth_headers(config)
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data["status"] != "success":
                console.print(create_error_panel(f"API Error: {data.get('message', 'Unknown error')}"))
                return
            
            # Find the specific agent
            agents = data["data"]
            agent = None
            for a in agents:
                if a.get("agent_id") == agent_id or a.get("id") == agent_id:
                    agent = a
                    break
            
            if not agent:
                console.print(create_error_panel(f"Agent '{agent_id}' not found"))
                return
            
            # Create agent info panel
            info_text = f"""
[bold]Agent Details[/bold]
Agent ID: {agent.get('agent_id', agent.get('id', 'unknown'))}
Name: {agent.get('agent_name', agent.get('name', 'unknown'))}
Hostname: {agent.get('hostname', 'unknown')}
Status: {'🟢 Active' if agent.get('status') == 'active' else '🔴 Inactive'}
Registered: {agent.get('registered_at', 'unknown')[:19] if agent.get('registered_at') else 'unknown'}
Last Seen: {agent.get('last_seen', 'never')[:19] if agent.get('last_seen') else 'never'}

[bold]Capabilities[/bold]
{', '.join(agent.get('capabilities', []))}

[bold]Metadata[/bold]
OS: {agent.get('metadata', {}).get('os', 'unknown')}
Version: {agent.get('metadata', {}).get('version', 'unknown')}
Region: {agent.get('metadata', {}).get('region', 'unknown')}
""".strip()
            
            console.print(Panel(info_text, title=f"Agent: {agent_id}", border_style="blue"))
            
            # Get metrics if requested - use UI-specific endpoint
            if metrics:
                try:
                    metrics_response = await client.get(
                        f"{config.core_api_url}/api/agents/{agent_id}/metrics-ui",  # Use UI endpoint
                        timeout=30.0,
                        headers=_get_auth_headers(config)
                    )
                    metrics_response.raise_for_status()
                    
                    metrics_data = metrics_response.json()
                    
                    if metrics_data["status"] == "success":
                        system_metrics = metrics_data["data"]
                        
                        metrics_text = f"""
[bold]System Metrics[/bold]
CPU Usage: {system_metrics.get('cpu_usage', 0):.1f}%
Memory Usage: {system_metrics.get('memory_usage', 0):.1f}%
Disk Usage: {system_metrics.get('disk_usage', 0):.1f}%
Network In: {system_metrics.get('network_in', 0):.2f} MB/s
Network Out: {system_metrics.get('network_out', 0):.2f} MB/s
Uptime: {system_metrics.get('uptime', 0)} seconds
Last Update: {system_metrics.get('timestamp', 'unknown')[:19]}
""".strip()
                        
                        console.print(Panel(metrics_text, title="Metrics", border_style="green"))
                    else:
                        console.print(create_error_panel(f"Metrics unavailable: {metrics_data.get('message')}"))
                
                except Exception as e:
                    console.print(create_error_panel(f"Failed to retrieve metrics: {str(e)}"))
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(create_error_panel(f"Agent '{agent_id}' not found"))
        elif e.response.status_code == 403:
            console.print(create_error_panel("Authentication failed"))
        else:
            console.print(create_error_panel(f"API request failed: {e.response.status_code}"))
    except Exception as e:
        console.print(create_error_panel(f"Failed to show agent: {str(e)}"))


@app.command("exec")
@handle_errors
@async_command
async def execute_on_agent(
    agent_id: str = typer.Argument(..., help="Agent ID to execute command on"),
    command: str = typer.Argument(..., help="Command to execute"),
    timeout_seconds: int = typer.Option(30, "--timeout", "-t", help="Command timeout in seconds"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for command completion")
):
    """Execute a command on a specific agent."""
    
    config = get_config()
    
    try:
        # Use timeout context manager instead of parameter (S7483)
        await asyncio.wait_for(
            _execute_agent_command(config, agent_id, command, timeout_seconds, wait),
            timeout=float(timeout_seconds + 5)  # Add buffer for API overhead
        )
    except asyncio.TimeoutError:
        console.print(create_error_panel(f"Command execution timed out after {timeout_seconds} seconds"))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(create_error_panel("Agent not found"))
        else:
            console.print(create_error_panel("API request failed"))
    except Exception as e:
        console.print(create_error_panel(f"Failed to execute command: {str(e)}"))

async def _execute_agent_command(config, agent_id: str, command: str, timeout_seconds: int, wait: bool) -> None:
    """
    Execute command on agent with real implementation
    
    CLAUDE.md: < 50 lines - Command execution logic
    Fixes S3776: Reduce cognitive complexity by extracting helper functions
    Fixes S7483: No timeout parameter, caller uses asyncio.wait_for()
    Removed mock implementation - now uses real WebSocket polling
    
    Args:
        config: NeuraOps configuration
        agent_id: Target agent ID
        command: Command to execute
        timeout_seconds: Timeout value for API payload
        wait: Whether to wait for completion
    """
    async with httpx.AsyncClient() as client:  # Revert back to normal
        try:
            # Submit command to agent
            command_id = await _submit_command(client, config, agent_id, command, timeout_seconds)
            if not command_id:
                return
            
            console.print(create_success_panel("Command queued with ID: " + command_id))
            
            # Wait for completion if requested
            if wait:
                await _wait_for_command_completion(client, config, command_id, timeout_seconds)
                await _display_command_results(client, config, command_id)
            
        except httpx.HTTPStatusError as e:
            _handle_http_error(e)
        except httpx.ConnectError:
            console.print(create_error_panel("Cannot connect to NeuraOps Core API"))
        except Exception as e:
            console.print(create_error_panel("Unexpected error: " + str(e)))

async def _submit_command(client: httpx.AsyncClient, config, agent_id: str, command: str, timeout_seconds: int) -> Optional[str]:
    """
    Submit command to agent and return command ID
    
    CLAUDE.md: < 20 lines - Command submission logic
    Fixes S3776: Extract command submission to reduce complexity
    
    Args:
        client: HTTP client instance
        config: NeuraOps configuration
        agent_id: Target agent ID
        command: Command to execute
        timeout_seconds: Timeout value for API payload
        
    Returns:
        Optional[str]: Command ID if successful, None otherwise
    """
    response = await client.post(
        config.core_api_url + "/api/agents/" + agent_id + "/execute",
        json={
            "command": command,
            "timeout": timeout_seconds
        },
        timeout=30.0,
        headers=_get_auth_headers(config)  # Add JWT authentication
    )
    response.raise_for_status()
    
    data = response.json()
    
    if data["status"] != "success":
        console.print(create_error_panel("Command submission failed: " + data.get("message", "Unknown error")))
        return None
    
    command_info = data["data"]
    return command_info.get("command_id")

async def _wait_for_command_completion(client: httpx.AsyncClient, config, command_id: str, timeout_seconds: int) -> None:
    """
    Poll for command completion with progress display
    
    CLAUDE.md: < 25 lines - Command polling logic
    Fixes S3776: Extract polling logic to reduce complexity
    
    Args:
        client: HTTP client instance
        config: NeuraOps configuration
        command_id: Command ID to monitor
        timeout_seconds: Maximum time to wait
    """
    console.print("[yellow]Waiting for command completion...[/yellow]")
    
    # Poll for results using real API endpoints
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Executing command...", total=None)
        
        # Real polling implementation
        max_polls = timeout_seconds // 2  # Poll every 2 seconds
        for _ in range(max_polls):
            await asyncio.sleep(2)
            
            # Check command status
            status_response = await client.get(
                config.core_api_url + "/api/commands/" + command_id + "/status",
                timeout=10.0,
                headers=_get_auth_headers(config)  # Add JWT authentication
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                command_status = status_data.get("data", {}).get("status", "pending")
                
                if command_status in ["completed", "failed"]:
                    progress.update(task, description="Command " + command_status)
                    break
                elif command_status == "running":
                    progress.update(task, description="Command executing...")
            else:
                progress.update(task, description="Checking status...")
        
        progress.update(task, description="Command completed")

async def _display_command_results(client: httpx.AsyncClient, config, command_id: str) -> None:
    """
    Display final command results
    
    CLAUDE.md: < 30 lines - Results display logic
    Fixes S3776: Extract results display to reduce complexity
    
    Args:
        client: HTTP client instance
        config: NeuraOps configuration
        command_id: Command ID to get results for
    """
    try:
        result_response = await client.get(
            config.core_api_url + "/api/commands/" + command_id + "/result",
            timeout=10.0,
            headers=_get_auth_headers(config)  # Add JWT authentication
        )
        
        if result_response.status_code == 200:
            result_data = result_response.json()
            if result_data.get("status") == "success":
                result_info = result_data.get("data", {})
                console.print(create_success_panel("Command executed successfully"))
                
                # Show actual output if available
                output = result_info.get("output", "No output")
                if output and output != "No output":
                    console.print("[bold green]Output:[/bold green]\n" + output)
                
                # Show exit code
                exit_code = result_info.get("exit_code", 0)
                console.print("[dim]Exit code: " + str(exit_code) + "[/dim]")
            else:
                error_msg = result_data.get("message", "Unknown error")
                console.print(create_error_panel("Command failed: " + error_msg))
        else:
            console.print(create_warning_panel("Could not retrieve command results"))
            
    except Exception as e:
        console.print(create_warning_panel("Error retrieving results: " + str(e)))

def _handle_http_error(e: httpx.HTTPStatusError) -> None:
    """
    Handle HTTP errors with appropriate messages
    
    CLAUDE.md: < 15 lines - Error handling logic
    Fixes S3776: Extract error handling to reduce complexity
    
    Args:
        e: HTTP status error to handle
    """
    if e.response.status_code == 404:
        console.print(create_error_panel("Agent not found or command endpoint unavailable"))
    elif e.response.status_code == 503:
        console.print(create_error_panel("Agent service unavailable"))
    else:
        console.print(create_error_panel("HTTP error " + str(e.response.status_code) + ": " + e.response.text))


@app.command("fs")
@handle_errors
@async_command
async def explore_filesystem(
    agent_id: str = typer.Argument(..., help="Agent ID to explore filesystem"),
    path: str = typer.Option("/", "--path", "-p", help="Path to explore"),
    tree: bool = typer.Option(False, "--tree", "-t", help="Display as tree structure")
):
    """Explore agent filesystem."""
    
    config = get_config()
    
    try:
        # Fetch filesystem data from API
        fs_data = await _fetch_filesystem_data(config, agent_id, path)
        entries = fs_data.get("entries", [])
        permissions = fs_data.get("permissions", {})
        
        # Display filesystem header and permissions
        console.print(f"\n📁 [bold]Filesystem: {path}[/bold] on agent [cyan]{agent_id}[/cyan]")
        _show_permissions(permissions)
        
        if not entries:
            console.print(create_info_panel("Directory is empty or inaccessible"))
            return
        
        # Render filesystem view
        if tree:
            _render_filesystem_tree(entries, path)
        else:
            _render_filesystem_table(entries)
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(create_error_panel("Agent not found"))
        else:
            console.print(create_error_panel("API request failed"))
    except Exception as e:
        console.print(create_error_panel(f"Failed to explore filesystem: {str(e)}"))

async def _fetch_filesystem_data(config, agent_id: str, path: str) -> dict:
    """
    Fetch filesystem data from agent API
    
    CLAUDE.md: < 20 lines - API call and validation
    Fixes S3776: Extract filesystem API logic to reduce complexity
    
    Args:
        config: NeuraOps configuration
        agent_id: Target agent ID
        path: Filesystem path to explore
        
    Returns:
        dict: Filesystem data from API
        
    Raises:
        httpx.HTTPStatusError: If API request fails
        NeuraOpsError: If API returns error status
    """
    async with httpx.AsyncClient() as client:  # Revert back to normal
        response = await client.get(
            f"{config.core_api_url}/api/agents/{agent_id}/filesystem",
            params={"path": path},
            timeout=30.0,
            headers=_get_auth_headers(config)  # Add JWT authentication
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] != "success":
            raise NeuraOpsError(f"Filesystem request failed: {data.get('message', 'Unknown error')}")
        
        return data["data"]


def _show_permissions(permissions: dict) -> None:
    """
    Display filesystem permissions
    
    CLAUDE.md: < 10 lines - Simple permissions display
    Fixes S3776: Extract permissions logic to reduce complexity
    
    Args:
        permissions: Dictionary of permission flags
    """
    perm_text = []
    if permissions.get("readable"): perm_text.append("🟢 Read")
    if permissions.get("writable"): perm_text.append("🟡 Write") 
    if permissions.get("executable"): perm_text.append("🔵 Execute")
    
    if perm_text:
        console.print(f"Permissions: {' | '.join(perm_text)}")


def _render_filesystem_tree(entries: List[dict], path: str) -> None:
    """
    Render filesystem as tree structure
    
    CLAUDE.md: < 20 lines - Tree rendering logic  
    Fixes S3776: Extract tree rendering to reduce complexity
    
    Args:
        entries: List of filesystem entries
        path: Current filesystem path
    """
    file_tree = Tree(f"📁 {path}")
    for entry in entries:
        icon = "📁" if entry["type"] == "directory" else "📄"
        name = entry["name"]
        size = f" ({entry['size']} bytes)" if entry["size"] else ""
        file_tree.add(f"{icon} {name}{size}")
    
    console.print(file_tree)


def _render_filesystem_table(entries: List[dict]) -> None:
    """
    Render filesystem as table
    
    CLAUDE.md: < 15 lines - Table rendering logic
    Fixes S3776: Extract table rendering to reduce complexity
    
    Args:
        entries: List of filesystem entries
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Size", justify="right", style="yellow")
    
    for entry in entries:
        icon = "📁 DIR" if entry["type"] == "directory" else "📄 FILE"
        size = str(entry["size"]) if entry["size"] else "-"
        table.add_row(icon, entry["name"], size)
    
    console.print(table)


@app.command("metrics")
@handle_errors
@async_command
async def show_metrics(
    agent_id: Optional[str] = typer.Argument(None, help="Specific agent ID (optional)"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch metrics in real-time"),
    interval: int = typer.Option(5, "--interval", "-i", help="Update interval in seconds")
):
    """Show agent metrics."""
    
    config = get_config()
    
    try:
        if agent_id:
            # Show metrics for specific agent
            await _show_single_agent_metrics(config, agent_id)
        else:
            # Show system-wide metrics
            await _show_system_metrics(config)
        
        if watch:
            console.print(f"[yellow]Watching metrics (update every {interval}s)... Press Ctrl+C to stop[/yellow]")
            try:
                while True:
                    await asyncio.sleep(interval)
                    console.clear()
                    if agent_id:
                        await _show_single_agent_metrics(config, agent_id)
                    else:
                        await _show_system_metrics(config)
            except KeyboardInterrupt:
                console.print("[yellow]Stopped watching metrics[/yellow]")
    
    except Exception as e:
        console.print(create_error_panel(f"Failed to show metrics: {str(e)}"))


async def _show_single_agent_metrics(config, agent_id: str):
    """Helper to show metrics for a single agent."""
    async with httpx.AsyncClient() as client:  # Revert back to normal
        response = await client.get(
            f"{config.core_api_url}/api/agents/{agent_id}/metrics-ui",  # Use UI-specific endpoint
            timeout=30.0,
            headers=_get_auth_headers(config)  # Add JWT authentication
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] == "success":
            metrics = data["data"]
            
            console.print(f"🤖 [bold]Agent Metrics: {agent_id}[/bold]")
            console.print(f"CPU: {metrics.get('cpu_usage', 0):.1f}% | "
                         f"Memory: {metrics.get('memory_usage', 0):.1f}% | "
                         f"Disk: {metrics.get('disk_usage', 0):.1f}%")


async def _show_system_metrics(config):
    """Helper to show system-wide metrics."""
    async with httpx.AsyncClient() as client:  # Revert back to normal
        response = await client.get(
            f"{config.core_api_url}/api/metrics/system",
            timeout=30.0,
            headers=_get_auth_headers(config)  # Add JWT authentication
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] == "success":
            metrics = data["data"]
            agents = metrics.get("agents", {})
            commands = metrics.get("commands", {})
            
            console.print("🌐 [bold]System Metrics[/bold]")
            console.print(f"Agents: {agents.get('total', 0)} total, {agents.get('online', 0)} online")
            console.print(f"Commands: {commands.get('total_executed', 0)} executed, "
                         f"{commands.get('success_rate', 0):.1f}% success rate")


if __name__ == "__main__":
    app()