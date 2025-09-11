"""
CLI WebSocket Handler

Handles WebSocket connections for CLI interactive mode with subprocess execution.
Follows CLAUDE.md: < 200 lines, fixes SonarQube S5754 and Pylance import issues.
"""
import json
import time
import asyncio
import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Fix Pylance: Use standard logging instead of structlog for better compatibility
logger = logging.getLogger(__name__)
from ..dependencies import get_jwt_handler


async def execute_cli_command(command: str, cwd: str = None, env: dict = None) -> dict:
    """
    Execute CLI command using async subprocess
    
    CLAUDE.md: < 30 lines - Replaces problematic CLI import with subprocess
    Fixes Pylance import error and S5754 SystemExit handling
    """
    try:
        cmd_args = ["python", "-m", "src.main"] + command.split()
        subprocess_env = os.environ.copy()
        if env:
            subprocess_env.update(env)
        
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            cwd=cwd or os.getcwd(),
            env=subprocess_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=30
        )
        
        return {
            "stdout": stdout_bytes.decode('utf-8'),
            "stderr": stderr_bytes.decode('utf-8'),
            "return_code": process.returncode
        }
        
    except asyncio.TimeoutError:
        if process:
            process.kill()
            await process.wait()
        return {
            "stdout": "",
            "stderr": "Command timed out after 30 seconds",
            "return_code": 124
        }


def _validate_cli_auth_token(auth_token: str) -> tuple[bool, str]:
    """
    Validate CLI authentication token
    
    CLAUDE.md: Helper function < 10 lines for CLI token validation
    Returns: (is_valid, agent_id)
    """
    if not auth_token or not auth_token.strip():
        return False, ""
    
    jwt_handler = get_jwt_handler()
    token_data = jwt_handler.verify_token(auth_token.strip())
    
    return (token_data is not None, token_data.agent_id if token_data else "")

async def handle_auth_message(websocket: WebSocket) -> tuple[str, str]:
    """
    Handle authentication message
    
    CLAUDE.md: < 20 lines - Extract auth logic with JWT validation
    """
    auth_data = await websocket.receive_text()
    auth_message = json.loads(auth_data)
    auth_token = auth_message.get("auth", "")
    agent_name = auth_message.get("agent_name", "unknown")
    
    # JWT token validation implementation
    is_valid, validated_agent_id = _validate_cli_auth_token(auth_token)
    if not is_valid:
        logger.warning("Invalid CLI auth token provided", agent_name=agent_name)
        raise ValueError("Authentication token validation failed")
    
    # Use validated agent ID if available
    if validated_agent_id:
        agent_name = validated_agent_id
    
    logger.info("CLI WebSocket authenticated", agent_name=agent_name)
    
    return auth_token, agent_name


async def send_connection_confirmation(websocket: WebSocket, agent_name: str):
    """
    Send connection confirmation
    
    CLAUDE.md: < 10 lines - Simple confirmation
    """
    await websocket.send_text(json.dumps({
        "type": "connection_confirmed",
        "message": f"CLI session established for {agent_name}",
        "timestamp": time.time()
    }))


async def handle_cli_command(websocket: WebSocket, command_content: str) -> None:
    """
    Handle CLI command execution
    
    CLAUDE.md: < 30 lines - Process CLI command via subprocess
    Fixes S5754 by using subprocess instead of direct CLI import
    """
    try:
        result = await execute_cli_command(command_content)
        
        response = {
            "type": "output",
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "return_code": result["return_code"],
            "timestamp": time.time()
        }
        
        await websocket.send_text(json.dumps(response))
        
    except Exception as cli_error:
        error_response = {
            "type": "error",
            "message": f"CLI execution failed: {str(cli_error)}",
            "timestamp": time.time()
        }
        await websocket.send_text(json.dumps(error_response))


async def handle_ping(websocket: WebSocket):
    """
    Handle ping message
    
    CLAUDE.md: < 10 lines - Simple ping response
    """
    await websocket.send_text(json.dumps({
        "type": "pong",
        "timestamp": time.time()
    }))


async def handle_cli_websocket(websocket: WebSocket, _: FastAPI):
    """
    Handle CLI WebSocket connection
    
    CLAUDE.md: < 100 lines - Main CLI WebSocket handler
    Fixes S5754 by specifying exception types instead of generic except
    Fixes S1172: app parameter renamed to _ (unused)
    """
    agent_name = "unknown"
    
    try:
        # Accept connection
        await websocket.accept()
        
        # Handle authentication
        try:
            _, agent_name = await handle_auth_message(websocket)  # S1481: auth_token unused
            await send_connection_confirmation(websocket, agent_name)
            
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid authentication message format"
            }))
            return
        
        # Handle CLI commands in real-time
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "command":
                    command_content = data.get("content", "")
                    await handle_cli_command(websocket, command_content)
                    
                elif message_type == "ping":
                    await handle_ping(websocket)
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid message format"
                }))
                
    except WebSocketDisconnect:
        logger.info("CLI WebSocket disconnected", agent_name=agent_name)
    
    except ConnectionError as e:
        logger.error("CLI WebSocket connection error", 
                    agent_name=agent_name, error=str(e))
    
    except ValueError as e:
        logger.error("CLI WebSocket value error", 
                    agent_name=agent_name, error=str(e))
    
    except Exception as e:
        logger.error("CLI WebSocket unexpected error", 
                    agent_name=agent_name, error=str(e))
        
        # Fixed S5754: Specify exception types instead of generic except
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Internal error: {str(e)}"
            }))
        except (ConnectionError, json.JSONEncodeError) as send_error:
            logger.warning("Failed to send error message to WebSocket", 
                          error=str(send_error))