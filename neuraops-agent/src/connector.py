"""Core connector for WebSocket/HTTP communication with NeuraOps Core."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import websockets
import httpx
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from .config import AgentConfig


class CoreConnector:
    """Manages connection to NeuraOps Core via WebSocket and HTTP."""
    
    def __init__(self, config: AgentConfig):
        """Initialize connector with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.connected = False
        self.jwt_token: Optional[str] = None  # JWT token for authenticated requests
        
        # Message handling
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.pending_commands: Dict[str, asyncio.Future] = {}
        
        # Connection management
        self.reconnect_task: Optional[asyncio.Task] = None
        self.receive_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> None:
        """Establish connection to NeuraOps Core."""
        # Create HTTP client for initial registration
        self.http_client = httpx.AsyncClient(
            base_url=self.config.core_url,
            timeout=30.0,
            headers={
                "User-Agent": f"NeuraOps-Agent/{self.config.agent_name}",
            }
        )
        
        # Test HTTP connectivity first
        try:
            response = await self.http_client.get("/api/health")
            response.raise_for_status()
            self.logger.info("HTTP connection to Core established")
        except httpx.RequestError as e:
            self.logger.error(f"Failed to connect to Core via HTTP: {e}")
            raise ConnectionError(f"Core unreachable at {self.config.core_url}")
        
        # Register agent and get JWT token
        jwt_token = await self._register_agent()
        if not jwt_token:
            raise ConnectionError("Failed to register agent and get JWT token")
        
        # Update HTTP client with JWT token
        await self.http_client.aclose()
        self.http_client = httpx.AsyncClient(
            base_url=self.config.core_url,
            timeout=30.0,
            headers={
                "User-Agent": f"NeuraOps-Agent/{self.config.agent_name}",
                "Authorization": f"Bearer {jwt_token}"
            }
        )
        
        # Store JWT token
        self.jwt_token = jwt_token
        self.connected = True
        
        # Try to establish WebSocket connection
        websocket_connected = await self._try_websocket_connection()
        
        if websocket_connected:
            self.logger.info("Agent connected successfully (HTTP + WebSocket mode)")
        else:
            self.logger.info("Agent connected successfully (HTTP-only mode)")

    async def _try_websocket_connection(self) -> bool:
        """
        Try to establish WebSocket connection with graceful fallback
        
        CLAUDE.md: Helper function < 15 lines for WebSocket attempt
        """
        try:
            self.logger.info("Establishing WebSocket connection...")
            await self._connect_websocket()
            
            # Start background tasks for WebSocket maintenance
            self.receive_task = asyncio.create_task(self._receive_loop())
            self.reconnect_task = asyncio.create_task(self._reconnect_loop())
            
            return True
            
        except Exception as e:
            self.logger.warning(f"WebSocket connection failed: {e}")
            return False

    async def _register_agent(self) -> Optional[str]:
        """Register agent with Core and get JWT token."""
        registration_data = {
            "agent_name": self.config.agent_name,
            "hostname": self.config.agent_name.split('_')[0] if '_' in self.config.agent_name else "localhost",  
            "capabilities": ["logs", "health", "metrics", "commands", "infrastructure", "incidents"],
            "api_key": self.config.auth_token,
            "metadata": {
                "version": "1.0.0",
                "platform": "Docker",
                "docker_mode": True,
                "host_access": True
            }
        }
        
        try:
            response = await self.http_client.post("/api/agents/register", json=registration_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == "success":
                jwt_token = result["data"]["token"]
                self.logger.info(f"Agent registered successfully with ID: {result['data']['agent_id']}")
                return jwt_token
            else:
                self.logger.error(f"Agent registration failed: {result}")
                return None
                
        except httpx.RequestError as e:
            self.logger.error(f"Registration request failed: {e}")
            return None
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Registration failed with status {e.response.status_code}: {e.response.text}")
            return None
        
    async def disconnect(self) -> None:
        """Disconnect from NeuraOps Core."""
        self.logger.info("Disconnecting from Core...")
        
        self.connected = False
        
        # Cancel background tasks
        if self.reconnect_task:
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                self.logger.debug("Reconnect task cancelled")
                raise  # S7497: Re-raise CancelledError for proper propagation
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                self.logger.debug("Receive task cancelled")
                raise  # S7497: Re-raise CancelledError for proper propagation
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        # Close HTTP client
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        self.logger.info("Disconnected from Core")
    
    async def _connect_websocket(self) -> None:
        """Connect to Core via WebSocket."""
        # Use agent_id as the WebSocket path parameter
        agent_id = f"{self.config.agent_name.split('_')[0] if '_' in self.config.agent_name else 'localhost'}_{self.config.agent_name}"
        ws_url = self.config.core_url.replace("http", "ws") + f"/ws/{agent_id}"
        
        try:
            # Use additional_headers for compatibility
            headers = {
                "Authorization": f"Bearer {getattr(self, 'jwt_token', self.config.auth_token)}",
                "X-Agent-Name": self.config.agent_name
            }
            
            self.websocket = await websockets.connect(
                ws_url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            # Send authentication/registration message
            auth_msg = {
                "type": "auth",
                "agent_name": self.config.agent_name,
                "auth_token": getattr(self, 'jwt_token', self.config.auth_token),
                "capabilities": {
                    "command_execution": self.config.enable_command_execution,
                    "metrics_collection": True,
                    "filesystem_access": True
                }
            }
            
            await self.websocket.send(json.dumps(auth_msg))
            
            # Wait for authentication response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            auth_response = json.loads(response)
            
            if auth_response.get("type") == "auth_success":
                self.connected = True
                self.logger.info("WebSocket connection authenticated")
            else:
                raise ConnectionError(f"Authentication failed: {auth_response}")
                
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            raise
    
    async def _reconnect_loop(self) -> None:
        """Background task to maintain WebSocket connection."""
        while self.connected:
            try:
                if not self.websocket or self.websocket.closed:
                    self.logger.info("Reconnecting to Core...")
                    await self._connect_websocket()
                
                await asyncio.sleep(self.config.reconnect_interval)
                
            except asyncio.CancelledError:
                self.logger.debug("Reconnect loop cancelled")
                raise  # S7497: Re-raise CancelledError for proper propagation
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(5)  # Short retry delay
    
    async def _receive_loop(self) -> None:
        """Background task to receive messages from Core."""
        while self.connected:
            try:
                if not self.websocket:
                    await asyncio.sleep(1)
                    continue
                
                message = await self.websocket.recv()
                data = json.loads(message)
                
                await self._handle_message(data)
                
            except asyncio.CancelledError:
                self.logger.debug("Receive loop cancelled")
                raise  # S7497: Re-raise CancelledError for proper propagation
            except ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
                if self.websocket:
                    self.websocket = None
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Error receiving message: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming message from Core."""
        msg_type = data.get("type")
        
        if msg_type == "command":
            # Queue command for execution
            await self.command_queue.put(data)
            
        elif msg_type == "ping":
            # Respond to ping
            pong_msg = {"type": "pong", "timestamp": datetime.now().isoformat()}
            await self._send_message(pong_msg)
            
        elif msg_type == "command_response":
            # Handle response to a command we sent
            command_id = data.get("command_id")
            if command_id in self.pending_commands:
                future = self.pending_commands.pop(command_id)
                future.set_result(data)
        
        else:
            self.logger.debug(f"Unknown message type: {msg_type}")
    
    async def _send_message(self, data: Dict[str, Any]) -> None:
        """Send message to Core via WebSocket."""
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("WebSocket not connected")
        
        try:
            message = json.dumps(data)
            await self.websocket.send(message)
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def send_metrics(self, metrics: Dict[str, Any]) -> None:
        """Send metrics to Core via WebSocket or HTTP fallback."""
        # Try WebSocket first if available
        if self.websocket and not self.websocket.closed:
            message = {
                "type": "metrics",
                "agent_name": self.config.agent_name,
                "timestamp": datetime.now().isoformat(),
                "data": metrics
            }
            
            try:
                await self._send_message(message)
                return
            except Exception as e:
                self.logger.warning(f"WebSocket metrics failed, trying HTTP fallback: {e}")
        
        # HTTP fallback - send to /api/metrics/agents/{agent_id}
        try:
            await self._send_metrics_http(metrics)
        except Exception as e:
            self.logger.error(f"Failed to send metrics via HTTP: {e}")
            raise

    async def _send_metrics_http(self, metrics: Dict[str, Any]) -> None:
        """Send metrics via HTTP POST to /api/metrics/agents/{agent_id}."""
        agent_id = f"{self.config.agent_name.split('_')[0] if '_' in self.config.agent_name else 'localhost'}_{self.config.agent_name}"
        
        # Extract nested metrics data from DockerMetricsCollector format
        metrics_data = metrics.get("metrics", metrics)  # Handle both nested and flat formats
        
        # Handle disk usage - extract percentage from nested structure
        disk_usage_val = 0.0
        disk_usage = metrics_data.get("disk_usage", {})
        if isinstance(disk_usage, dict):
            # Prefer host disk usage, fallback to container
            if "host" in disk_usage and "percent" in disk_usage["host"]:
                disk_usage_val = float(disk_usage["host"]["percent"])
            elif "container" in disk_usage and "percent" in disk_usage["container"]:
                disk_usage_val = float(disk_usage["container"]["percent"])
        elif isinstance(disk_usage, (int, float)):
            disk_usage_val = float(disk_usage)
        
        # Handle network I/O - calculate rates from byte counters  
        network_io = metrics_data.get("network_io", {})
        network_in_mbps = 0.0
        network_out_mbps = 0.0
        
        if isinstance(network_io, dict):
            bytes_recv = network_io.get("bytes_recv", 0)
            bytes_sent = network_io.get("bytes_sent", 0)
            packets_recv = network_io.get("packets_recv", 0)
            packets_sent = network_io.get("packets_sent", 0)
            
            # Simple heuristic: convert total bytes to MB and estimate rate
            # (This is rough - ideally we'd track deltas over time intervals)
            if bytes_recv > 0:
                network_in_mbps = min(bytes_recv / (1024 * 1024 * 1000), 100.0)  # Cap at reasonable value
            if bytes_sent > 0:
                network_out_mbps = min(bytes_sent / (1024 * 1024 * 1000), 100.0)
        
        # Handle load average
        load_avg = metrics_data.get("cpu_load_avg", [0.0, 0.0, 0.0])
        if not isinstance(load_avg, list) or len(load_avg) != 3:
            load_avg = [0.0, 0.0, 0.0]
        
        # Convert metrics to AgentMetrics format expected by API
        agent_metrics = {
            "agent_id": agent_id,
            "cpu_usage": float(metrics_data.get("cpu_percent", 0.0)),
            "memory_usage": float(metrics_data.get("memory_percent", 0.0)),
            "disk_usage": disk_usage_val,
            "active_tasks": int(metrics_data.get("active_tasks", 0)),
            "completed_tasks": int(metrics_data.get("completed_tasks", 0)),
            "error_count": int(metrics_data.get("error_count", 0)),
            "uptime_seconds": int(metrics_data.get("uptime_seconds", 0)),
            "network_in": network_in_mbps,
            "network_out": network_out_mbps,
            "load_average": load_avg,
            "timestamp": datetime.now().isoformat()
        }
        
        # Debug logging to verify field mapping
        self.logger.debug(f"Mapping metrics - CPU: {metrics_data.get('cpu_percent', 'MISSING')} -> {agent_metrics['cpu_usage']}")
        self.logger.debug(f"Mapping metrics - Memory: {metrics_data.get('memory_percent', 'MISSING')} -> {agent_metrics['memory_usage']}")
        self.logger.debug(f"Mapping metrics - Disk: {disk_usage} -> {agent_metrics['disk_usage']}")
        self.logger.debug(f"Mapping metrics - Uptime: {metrics_data.get('uptime_seconds', 'MISSING')} -> {agent_metrics['uptime_seconds']}")
        self.logger.debug(f"Mapping metrics - Network: in:{network_in_mbps:.4f} out:{network_out_mbps:.4f}")
        self.logger.debug(f"Mapping metrics - Load avg: {load_avg}")
        
        url = f"/api/metrics/agents/{agent_id}"
        
        response = await self.http_client.post(url, json=agent_metrics)
        if response.status_code != 200:
            error_text = await response.aread()
            # Use specific httpx.HTTPStatusError instead of generic Exception
            raise httpx.HTTPStatusError(
                f"HTTP {response.status_code}: {error_text}",
                request=response.request,
                response=response
            )
        
        self.logger.debug(f"Metrics sent successfully via HTTP to {agent_id}")
    
    async def send_heartbeat(self) -> None:
        """Send heartbeat to Core."""
        message = {
            "type": "heartbeat",
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat(),
            "status": "online"
        }
        
        try:
            await self._send_message(message)
        except Exception as e:
            self.logger.debug(f"Failed to send heartbeat: {e}")
    
    async def send_command_result(self, command_id: str, result: Dict[str, Any]) -> None:
        """Send command execution result to Core."""
        message = {
            "type": "command_result", 
            "command_id": command_id,
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        try:
            await self._send_message(message)
        except Exception as e:
            self.logger.error(f"Failed to send command result: {e}")
    
    async def receive_command(self) -> Optional[Dict[str, Any]]:
        """Receive command from Core (non-blocking)."""
        try:
            # Non-blocking get with short timeout
            command = await asyncio.wait_for(self.command_queue.get(), timeout=0.1)
            return command
        except asyncio.TimeoutError:
            return None
    
    async def send_cli_command(self, command: str, args: list) -> Dict[str, Any]:
        """Send CLI command to Core for execution."""
        if not self.http_client:
            raise ConnectionError("HTTP client not initialized")
        
        payload = {
            "command": command,
            "args": args,
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = await self.http_client.post("/api/cli/execute", json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            self.logger.error(f"CLI command failed: {e}")
            return {
                "success": False,
                "error": f"Connection error: {e}",
                "stdout": "",
                "stderr": str(e)
            }
        except httpx.HTTPStatusError as e:
            self.logger.error(f"CLI command returned error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {
                    "success": False,
                    "error": error_data.get("detail", "Unknown error"),
                    "stdout": "",
                    "stderr": error_data.get("detail", str(e))
                }
            except ValueError as json_err:  # S5713: Remove redundant JSONDecodeError - it's a subclass of ValueError
                self.logger.warning(f"Failed to parse error response JSON: {json_err}")
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}",
                    "stdout": "",
                    "stderr": str(e)
                }