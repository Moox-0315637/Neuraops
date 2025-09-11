"""Transparent CLI proxy for NeuraOps commands."""

import asyncio
import sys
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from src.config import load_config, AgentConfig
from src.connector import CoreConnector


# Constants
INTERACTIVE_EXIT_MESSAGE = "Type 'exit' or Ctrl+C to quit"


class NeuraOpsProxy:
    """Transparent proxy for NeuraOps CLI commands to Core."""
    
    def __init__(self):
        """Initialize CLI proxy."""
        self.config = load_config()
        self.connector: Optional[CoreConnector] = None
        
        # Setup basic logging for proxy
        logging.basicConfig(
            level=logging.WARNING,  # Less verbose for CLI
            format="%(message)s"
        )
        self.logger = logging.getLogger(__name__)
    
    async def run(self, args: List[str]) -> int:
        """Main entry point for proxy execution."""
        try:
            # Check if Core is configured
            if not self.config.core_url:
                self._print_error("NeuraOps Core URL not configured")
                self._print_error("Run: neuraops-agent config --core-url <url>")
                return 1
            
            # Initialize connector
            self.connector = CoreConnector(self.config)
            
            # Handle special proxy commands
            if args and args[0] in ["--proxy-help", "--proxy-status"]:
                return await self._handle_proxy_command(args[0])
            
            # Forward command to Core
            return await self._forward_command(args)
            
        except KeyboardInterrupt:
            self._print_error("\nOperation cancelled by user")
            return 130
        except Exception as e:
            self._print_error(f"Proxy error: {e}")
            return 1
        finally:
            if self.connector:
                await self.connector.disconnect()
    
    async def _handle_proxy_command(self, command: str) -> int:
        """Handle proxy-specific commands."""
        if command == "--proxy-help":
            self._print_proxy_help()
            return 0
        elif command == "--proxy-status":
            return await self._show_proxy_status()
        
        return 1
    
    def _print_proxy_help(self) -> None:
        """Print proxy help information."""
        print("NeuraOps CLI Proxy - Transparent connection to NeuraOps Core")
        print()
        print("This command forwards all NeuraOps CLI commands to the Core platform.")
        print("All AI features, workflows, and analysis are handled by the Core.")
        print()
        print("Examples:")
        print("  neuraops logs analyze /var/log/app.log")
        print("  neuraops ai ask 'How to optimize PostgreSQL?'")
        print("  neuraops workflow run backup-database")
        print("  neuraops infra scan")
        print()
        print("Proxy Commands:")
        print("  --proxy-help     Show this help")
        print("  --proxy-status   Check Core connectivity")
        print()
        print(f"Core URL: {self.config.core_url}")
        print(f"Agent: {self.config.agent_name}")
    
    async def _get_jwt_token(self) -> Optional[str]:
        """Register agent and get JWT token."""
        try:
            import httpx
            
            async with httpx.AsyncClient(base_url=self.config.core_url, timeout=10.0) as client:
                # Register agent with API key
                registration_data = {
                    "agent_name": self.config.agent_name,
                    "hostname": self.config.agent_name.split('_')[0] if '_' in self.config.agent_name else "localhost",
                    "capabilities": ["logs", "health", "metrics", "commands"],
                    "api_key": self.config.auth_token,
                    "metadata": {"platform": "cli-proxy", "version": "1.0.0"}
                }
                
                response = await client.post("/api/agents/register", json=registration_data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        return result["data"]["token"]
                    
                self.logger.debug(f"Registration failed: {response.text}")
                return None
                
        except Exception as e:
            self.logger.debug(f"Failed to get JWT token: {e}")
            return None
    
    async def _show_proxy_status(self) -> int:
        """Show proxy and Core connectivity status."""
        print("NeuraOps CLI Proxy Status")  # S3457: Regular string, no f-string needed
        print(f"Agent Name: {self.config.agent_name}")
        print(f"Core URL: {self.config.core_url}")
        print()
        
        # Test Core connectivity
        try:
            # Quick HTTP test without full WebSocket setup
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.core_url}/api/health")
                response.raise_for_status()
                
                health_data = response.json()
                print("✅ Core Connection: OK")
                print(f"   Core Version: {health_data.get('version', 'Unknown')}")
                print(f"   Core Status: {health_data.get('status', 'Unknown')}")
                return 0
                
        except Exception as e:
            print("❌ Core Connection: FAILED")
            print(f"   Error: {e}")
            print()
            print("Troubleshooting:")
            print("1. Check Core URL in configuration")
            print("2. Ensure Core is running and accessible")
            print("3. Verify network connectivity")
            return 1
    
    def _build_local_command(self, command: str, args: List[str]) -> List[str]:
        """Build local command args following CLAUDE.md < 10 lines"""
        # Handle special command argument order for logs
        if command == "logs" and len(args) >= 2 and args[0] == "analyze":
            file_path = args[1]
            subcommand = args[0]
            remaining_args = args[2:] if len(args) > 2 else []
            final_args = [file_path, subcommand, file_path] + remaining_args
        else:
            final_args = args
        
        return ["uv", "run", "python", "-m", "src.main", command] + final_args
    
    def _get_core_path(self) -> str:
        """Get core path following CLAUDE.md < 5 lines"""
        return "/Users/maximedegournay/projet/gitlab/NeuraOps/neuraops-core"
    
    async def _execute_command_locally(self, command: str, args: List[str]) -> int:
        """
        Execute command locally using async subprocess following CLAUDE.md < 15 lines
        Fixes S7503 + S7487: async subprocess for async function
        """
        try:
            cmd_args = self._build_local_command(command, args)
            self.logger.info(f"Executing command locally: {command} {' '.join(args)}")
            
            # Execute with async subprocess (S7487 fix)
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self._get_core_path(),
                stdout=None,  # Let output go directly to terminal
                stderr=None,
                env=os.environ.copy()
            )
            
            return_code = await process.wait()
            return return_code
            
        except Exception as e:
            self._print_error(f"Local execution failed: {e}")
            return 1

    async def _validate_and_authenticate(self) -> Optional[str]:
        """Validate connection and get JWT token following CLAUDE.md < 15 lines"""
        jwt_token = await self._get_jwt_token()
        if not jwt_token:
            self._print_error("Failed to authenticate with Core")
            return None
        return jwt_token
    
    def _create_http_client(self, jwt_token: str) -> "httpx.AsyncClient":
        """Create HTTP client with JWT auth following CLAUDE.md < 15 lines"""
        import httpx
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=30.0)
        return httpx.AsyncClient(
            base_url=self.config.core_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Agent-Name": self.config.agent_name,
                "Content-Type": "application/json"
            }
        )
    
    def _prepare_command_payload(self, args: List[str]) -> Dict[str, Any]:
        """Prepare command payload following CLAUDE.md < 15 lines"""
        return {
            "command": args[0] if args else "",
            "args": args[1:] if len(args) > 1 else [],
            "agent_name": self.config.agent_name,
            "cwd": os.getcwd(),
            "env": {
                "USER": os.environ.get("USER", "unknown"),
                "HOME": os.environ.get("HOME", "/tmp"),
                "PATH": os.environ.get("PATH", "")
            }
        }
    
    async def _process_success_response(self, result: Dict[str, Any], args: List[str]) -> int:
        """Process successful API response following CLAUDE.md < 15 lines"""
        if "data" in result:
            data = result["data"]
            error_text = data.get("stderr", "") + " " + data.get("stdout", "")
            has_asyncio_error = "asyncio.run() cannot be called" in error_text
            has_connection_error = "not connected" in error_text
            
            if ((not data.get("success") and has_connection_error) or 
                has_asyncio_error) and args and args[0] in ["health", "system", "logs", "infra"]:
                self._print_error("Agent not connected to Core, trying local execution...")
                return await self._execute_command_locally(args[0], args[1:])
            
            return self._handle_command_result(data)
        else:
            return self._handle_command_result(result)
    
    def _process_error_response(self, response: "httpx.Response") -> int:
        """Process API error response following CLAUDE.md < 15 lines"""
        if response.status_code == 404:
            self._print_error("Core CLI endpoint not available")
            self._print_error("This feature requires NeuraOps Core v2.0+")
        elif response.status_code == 401:
            self._print_error("Authentication failed")
            self._print_error("Check your agent token configuration")
        else:
            self._print_error(f"Core returned error: HTTP {response.status_code}")
            try:
                error_data = response.json()
                self._print_error(f"Details: {error_data.get('detail', 'Unknown error')}")
            except ValueError:
                pass  # Response may not be valid JSON
        return 1
    
    async def _handle_api_response(self, response: "httpx.Response", args: List[str]) -> int:
        """Handle API response and fallback following CLAUDE.md < 15 lines"""
        if response.status_code == 200:
            result = response.json()
            return await self._process_success_response(result, args)
        
        return self._process_error_response(response)
    
    def _handle_connection_error(self, error: Exception) -> int:
        """Handle connection errors following CLAUDE.md < 10 lines"""
        import httpx
        if isinstance(error, httpx.ConnectError):
            self._print_error(f"Cannot connect to NeuraOps Core at {self.config.core_url}")
            self._print_error("Is the Core running and accessible?")
        elif isinstance(error, httpx.TimeoutException):
            self._print_error("Command timed out")
            self._print_error("Core may be processing or unresponsive")
        else:
            self._print_error(f"Proxy connection error: {error}")
        return 1
    
    async def _forward_command(self, args: List[str]) -> int:
        """Forward command to NeuraOps Core following CLAUDE.md < 15 lines"""
        try:
            jwt_token = await self._validate_and_authenticate()
            if not jwt_token:
                return 1
                
            async with self._create_http_client(jwt_token) as client:
                payload = self._prepare_command_payload(args)
                response = await client.post("/api/cli/execute", json=payload)
                return await self._handle_api_response(response, args)
                
        except (Exception,) as e:
            return self._handle_connection_error(e)
    
    def _handle_command_result(self, result: Dict[str, Any]) -> int:
        """Handle and display command result from Core."""
        # Display stdout if present
        stdout = result.get("stdout", "")
        if stdout:
            print(stdout, end="", flush=True)
        
        # Display stderr if present  
        stderr = result.get("stderr", "")
        if stderr:
            print(stderr, end="", file=sys.stderr, flush=True)
        
        # Handle streaming output if supported
        if "stream" in result:
            for chunk in result["stream"]:
                if chunk.get("type") == "stdout":
                    print(chunk["content"], end="")
                elif chunk.get("type") == "stderr":
                    print(chunk["content"], end="", file=sys.stderr)
        
        # Return exit code
        return_code = result.get("return_code", result.get("returncode", 0))
        
        # Handle error state
        if result.get("error"):
            if not stderr:  # Only print error if not already in stderr
                self._print_error(f"Error: {result['error']}")
            return 1
        
        return return_code
    
    def _print_error(self, message: str) -> None:
        """Print error message to stderr."""
        print(f"neuraops-proxy: {message}", file=sys.stderr)


# Interactive mode support
class InteractiveProxy:
    """Interactive mode proxy for real-time Core communication."""
    
    def __init__(self, config: AgentConfig):
        """Initialize interactive proxy."""
        self.config = config
        self.connector = CoreConnector(config)
    
    async def start_interactive(self) -> int:
        """Start interactive mode with Core."""
        print("NeuraOps Interactive Mode - Connected to Core")
        print(INTERACTIVE_EXIT_MESSAGE)
        print()
        
        try:
            # Ensure WebSocket connection
            await self.connector.connect()
            
            # Interactive WebSocket loop with fallback
            return await self._interactive_websocket_loop()
            
        except Exception as e:
            print(f"WebSocket interactive mode failed: {e}")
            print("Falling back to HTTP mode...")
            return await self._interactive_http_fallback()
    
    async def _send_interactive_command(self, command: str) -> Dict[str, Any]:
        """Send interactive command via WebSocket following CLAUDE.md < 15 lines"""
        if not self.connector.websocket or self.connector.websocket.closed:
            # Fallback to HTTP if WebSocket not available
            proxy = NeuraOpsProxy()
            await proxy._forward_command(command.split())
            return {"status": "sent_via_http"}
        
        # Send via WebSocket for real-time interaction
        command_msg = {
            "type": "interactive_command",
            "command": command,
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connector._send_message(command_msg)
        return {"status": "sent_via_websocket"}
    
    async def _wait_for_interactive_response(self) -> Optional[Dict]:
        """Wait for interactive command response using timeout context manager following CLAUDE.md < 15 lines"""
        try:
            # Use asyncio.timeout context manager (Python 3.11+) or asyncio.wait_for for older versions
            async with asyncio.timeout(30.0):  # 30 second timeout
                while True:
                    response = await asyncio.wait_for(
                        self.connector.receive_command(),
                        timeout=1.0
                    )
                    
                    if response and response.get("type") == "interactive_response":
                        return response
                        
        except (asyncio.TimeoutError, TimeoutError):
            return None  # Timeout after 30 seconds
    
    def _display_interactive_response(self, response: Dict[str, Any]) -> None:
        """Display interactive command response following CLAUDE.md < 10 lines"""
        if "output" in response:
            print(response["output"])
        
        if "error" in response:
            print(f"Error: {response['error']}", file=sys.stderr)
        
        if "status" in response:
            print(f"Status: {response['status']}")
    
    async def _interactive_websocket_loop(self) -> int:
        """WebSocket interactive command loop following CLAUDE.md < 15 lines"""
        print("NeuraOps Interactive Mode - WebSocket Connected to Core")
        print(INTERACTIVE_EXIT_MESSAGE)
        print()
        
        while True:
            try:
                command = await asyncio.to_thread(input, "neuraops-ws> ")
                command = command.strip()
                
                if command.lower() in ["exit", "quit"]:
                    break
                
                if not command:
                    continue
                
                # Send via WebSocket and wait for response
                await self._send_interactive_command(command)
                response = await self._wait_for_interactive_response()
                
                if response:
                    self._display_interactive_response(response)
            
            except (EOFError, KeyboardInterrupt):
                break
        
        print("Goodbye!")
        return 0
    
    async def _interactive_http_fallback(self) -> int:
        """HTTP fallback for interactive mode following CLAUDE.md < 10 lines"""
        print("NeuraOps Interactive Mode - Using HTTP mode (WebSocket unavailable)")
        print(INTERACTIVE_EXIT_MESSAGE)
        print()
        
        while True:
            try:
                command = await asyncio.to_thread(input, "neuraops-http> ")
                command = command.strip()
                
                if command.lower() in ["exit", "quit"]:
                    break
                
                if command:
                    proxy = NeuraOpsProxy()
                    await proxy._forward_command(command.split())
                    
            except (EOFError, KeyboardInterrupt):
                break
        
        print("Goodbye!")
        return 0


# Main CLI entry point
async def main() -> int:
    """Main entry point for CLI proxy."""
    args = sys.argv[1:]  # Remove script name
    
    # Handle special interactive mode
    if args and args[0] in ["-i", "--interactive"]:
        config = load_config()
        interactive = InteractiveProxy(config)
        return await interactive.start_interactive()
    
    # Standard proxy mode
    proxy = NeuraOpsProxy()
    return await proxy.run(args)


def sync_main() -> int:
    """Synchronous wrapper for async main."""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(sync_main())