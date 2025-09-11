# src/api/services/agent_command_service.py
"""
Agent Command Service

CLAUDE.md: < 500 lignes, service pour orchestration commandes agent
Coordonne l'exécution des commandes entre Core et Agent
"""
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from src.core.command_classifier import get_command_classifier, ExecutionLocation
from src.api.models.agent_command import (
    AgentCommandRequest, AgentCommandResponse, CommandExecutionStatus,
    CommandStatus, WebSocketCommandMessage
)
from .command_format_service import get_command_format_service


class AgentCommandService:
    """
    Service for coordinating agent command execution
    
    CLAUDE.md: Single responsibility pour orchestration commandes
    """
    
    def __init__(self):
        """Initialize agent command service"""
        self.logger = logging.getLogger(__name__)
        self.classifier = get_command_classifier()
        self.formatter = get_command_format_service()
        
        # Track ongoing command executions
        self.active_executions: Dict[str, CommandExecutionStatus] = {}
        
        # WebSocket connections to agents
        self.agent_connections: Dict[str, Any] = {}  # agent_name -> websocket
        
        # Track cleanup tasks for proper shutdown
        self.cleanup_tasks: Dict[str, Any] = {}
    
    async def execute_command(
        self, 
        command: str, 
        args: List[str], 
        agent_name: str,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Execute command with appropriate routing (agent, core, or hybrid)
        
        Args:
            command: Main command (e.g., 'health')
            args: Command arguments (e.g., ['disk'])
            agent_name: Target agent name
            timeout_seconds: Execution timeout
            
        Returns:
            Command execution result
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        try:
            # Classify command
            classification = self.classifier.classify_command(command, args)
            
            self.logger.info(
                f"Executing command: {command} {' '.join(args)} "
                f"(location: {classification.location}, agent: {agent_name})"
            )
            
            # Track execution
            execution_status = CommandExecutionStatus(
                request_id=request_id,
                command=command,
                agent_name=agent_name,
                status=CommandStatus.PENDING,
                execution_location=classification.location,
                started_at=datetime.now()
            )
            self.active_executions[request_id] = execution_status
            
            # Route based on classification
            if classification.location == ExecutionLocation.AGENT:
                result = await self._execute_on_agent(
                    command, args, agent_name, request_id, timeout_seconds
                )
            elif classification.location == ExecutionLocation.HYBRID:
                result = await self._execute_hybrid(
                    command, args, agent_name, request_id, timeout_seconds
                )
            else:
                # Core execution - no fallback messages needed for core commands
                result = self._execute_on_core(
                    command, args, request_id
                )
                # Ensure clean execution_location for core commands
                result["execution_location"] = "core"
            
            # Update execution status
            execution_status.status = CommandStatus.COMPLETED if result.get("success") else CommandStatus.FAILED
            execution_status.completed_at = datetime.now()
            execution_status.updated_at = datetime.now()
            
            # Format result for CLI display if it's from agent
            if classification.location == ExecutionLocation.AGENT and result.get("success"):
                subcommand = args[0] if args else None
                formatted_output = self.formatter.format_command_output(
                    command=command,
                    subcommand=subcommand,
                    raw_result=result,
                    format_type="cli"
                )
                
                # Update result with formatted output
                result.update({
                    "stdout": formatted_output.get("stdout", ""),
                    "stderr": formatted_output.get("stderr", ""),
                    "formatted": True
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            
            # Update execution status
            if request_id in self.active_executions:
                execution_status = self.active_executions[request_id]
                execution_status.status = CommandStatus.FAILED
                execution_status.completed_at = datetime.now()
                execution_status.updated_at = datetime.now()
            
            return {
                "success": False,
                "return_code": 1,
                "stdout": "",
                "stderr": f"Command execution error: {str(e)}",
                "command": command,
                "agent_name": agent_name,
                "execution_location": "error",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            # Clean up execution tracking after some time
            if request_id in self.active_executions:
                # Keep for 5 minutes for status queries
                cleanup_task = asyncio.create_task(self._cleanup_execution(request_id, delay=300))
                self.cleanup_tasks[request_id] = cleanup_task
    
    async def _execute_on_agent(
        self, 
        command: str, 
        args: List[str], 
        agent_name: str,
        request_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Execute command on specified agent via WebSocket with fallback to core execution"""
        try:
            # Update status
            if request_id in self.active_executions:
                self.active_executions[request_id].status = CommandStatus.EXECUTING
                self.active_executions[request_id].current_step = "Sending command to agent"
            
            # Check if agent is connected via WebSocket
            if agent_name not in self.agent_connections:
                self.logger.info(f"Agent '{agent_name}' not connected via WebSocket, falling back to core execution")
                
                # Fallback to core execution for CLI proxy scenarios
                if request_id in self.active_executions:
                    self.active_executions[request_id].current_step = "Falling back to core execution"
                
                # Execute on core as fallback
                result = self._execute_on_core(command, args, request_id)
                result["execution_location"] = "core-fallback"
                result["fallback_reason"] = f"Agent '{agent_name}' not connected via WebSocket"
                return result
            
            # Send command via WebSocket
            websocket = self.agent_connections[agent_name]
            command_message = WebSocketCommandMessage(
                type="command_request",
                request_id=request_id,
                command=command,
                args=args,
                timeout_seconds=timeout_seconds
            )
            
            await websocket.send_text(command_message.json())
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(
                    self._wait_for_agent_response(request_id),
                    timeout=timeout_seconds
                )
                return response
                
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "return_code": 124,  # Timeout exit code
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout_seconds} seconds",
                    "command": command,
                    "agent_name": agent_name,
                    "execution_location": "agent",
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            self.logger.error(f"Error executing command on agent: {e}")
            return {
                "success": False,
                "return_code": 1,
                "stdout": "",
                "stderr": f"Agent execution error: {str(e)}",
                "command": command,
                "agent_name": agent_name,
                "execution_location": "agent",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def _execute_on_core(
        self, 
        command: str, 
        args: List[str],
        request_id: str
    ) -> Dict[str, Any]:
        """Execute command on core using subprocess to properly capture Rich output"""
        try:
            # Update status
            if request_id in self.active_executions:
                self.active_executions[request_id].status = CommandStatus.EXECUTING
                self.active_executions[request_id].current_step = "Executing on core"
            
            import subprocess
            import sys
            
            # Build command arguments
            cmd_args = [sys.executable, '-m', 'src.main'] + [command] + args
            
            # Execute command using subprocess to capture all output including Rich
            try:
                result = subprocess.run(
                    cmd_args,
                    cwd='.',  # Current working directory
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env=os.environ.copy()
                )
                
                return_code = result.returncode
                stdout_output = result.stdout or ""
                stderr_output = result.stderr or ""
                
                self.logger.debug(f"CLI command completed with code {return_code}")
                
            except subprocess.TimeoutExpired:
                return_code = 124  # Standard timeout exit code
                stdout_output = ""
                stderr_output = "Command timed out after 300 seconds"
                self.logger.warning(f"CLI command timed out: {command} {' '.join(args)}")
                
            except Exception as e:
                return_code = 1
                stdout_output = ""
                stderr_output = f"Subprocess error: {str(e)}"
                self.logger.error(f"Subprocess execution error: {e}")
            
            return {
                "success": return_code == 0,
                "return_code": return_code,
                "stdout": stdout_output,
                "stderr": stderr_output,
                "command": command,
                "agent_name": "core",
                "execution_location": "core",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error executing command on core: {e}")
            return {
                "success": False,
                "return_code": 1,
                "stdout": "",
                "stderr": f"Core execution error: {str(e)}",
                "command": command,
                "agent_name": "core",
                "execution_location": "core",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_hybrid(
        self, 
        command: str, 
        args: List[str], 
        agent_name: str,
        request_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Execute hybrid command (agent data collection + core AI processing)"""
        try:
            # Update status
            if request_id in self.active_executions:
                self.active_executions[request_id].status = CommandStatus.EXECUTING
                self.active_executions[request_id].current_step = "Collecting data from agent"
            
            # Step 1: Collect data from agent
            # For hybrid commands, we need to map to appropriate agent data collection
            if command == "logs" and "analyze" in args:
                # Agent should read the log file
                agent_result = await self._execute_on_agent(
                    "logs", ["read-local"] + args[1:], agent_name, request_id, timeout_seconds
                )
            elif command == "health" and "analyze" in args:
                # Agent should collect health data
                agent_result = await self._execute_on_agent(
                    "health", ["system-health"], agent_name, request_id, timeout_seconds
                )
            else:
                # Fallback: collect basic system info
                agent_result = await self._execute_on_agent(
                    "system", ["info"], agent_name, request_id, timeout_seconds
                )
            
            if not agent_result.get("success"):
                return agent_result  # Return agent error
            
            # Step 2: Process with AI on core
            if request_id in self.active_executions:
                self.active_executions[request_id].current_step = "Processing with AI on core"
            
            # Process with AI on core
            try:
                ai_processed_result = await self._process_with_ai(agent_result, command, args)
                ai_processed_result["execution_location"] = "hybrid"
                return ai_processed_result
            except Exception as ai_error:
                self.logger.warning(f"AI processing failed, returning raw data: {ai_error}")
                agent_result["execution_location"] = "hybrid"
                agent_result["processing_note"] = "Hybrid command: Data collected from agent, AI processing unavailable"
            
            return agent_result
        
        except Exception as e:
            self.logger.error(f"Error executing hybrid command: {e}")
            return {
                "success": False,
                "return_code": 1,
                "stdout": "",
                "stderr": f"Hybrid execution error: {str(e)}",
                "command": command,
                "agent_name": agent_name,
                "execution_location": "hybrid",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _wait_for_agent_response(self, request_id: str) -> Dict[str, Any]:
        """Wait for agent response to command"""
        # This would be implemented with proper WebSocket message handling
        # For now, return a placeholder with request_id for logging
        self.logger.debug(f"Waiting for agent response for request {request_id}")
        await asyncio.sleep(0.1)  # Simulate waiting
        
        return {
            "success": False,
            "return_code": 1,
            "stdout": "",
            "stderr": "WebSocket agent communication not yet implemented",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _process_with_ai(self, agent_data: Dict[str, Any], command: str, args: List[str]) -> Dict[str, Any]:
        """Process agent data with AI for hybrid commands"""
        try:
            # Import DevOpsEngine for AI processing
            from src.core.engine import DevOpsEngine
            
            engine = DevOpsEngine()
            
            # Process based on command and agent data
            if command == "logs" and "analyze" in args:
                ai_analysis = await engine.analyze_logs(agent_data.get("stdout", ""))
                agent_data["ai_analysis"] = ai_analysis
            elif command == "health" and "analyze" in args:
                # Simple AI enhancement for health data
                agent_data["ai_recommendations"] = f"AI analysis: System appears {'healthy' if agent_data.get('success') else 'problematic'}"
            
            return agent_data
            
        except Exception as e:
            # Fallback gracefully if AI processing fails
            self.logger.warning(f"AI processing failed: {e}")
            agent_data["ai_error"] = str(e)
            return agent_data
    
    async def _cleanup_execution(self, request_id: str, delay: int = 0):
        """Clean up execution tracking after delay"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        if request_id in self.active_executions:
            del self.active_executions[request_id]
        if request_id in self.cleanup_tasks:
            del self.cleanup_tasks[request_id]
    
    def register_agent_connection(self, agent_name: str, websocket):
        """Register agent WebSocket connection"""
        self.agent_connections[agent_name] = websocket
        self.logger.info(f"Agent '{agent_name}' connected")
    
    def unregister_agent_connection(self, agent_name: str):
        """Unregister agent WebSocket connection"""
        if agent_name in self.agent_connections:
            del self.agent_connections[agent_name]
            self.logger.info(f"Agent '{agent_name}' disconnected")
    
    def get_execution_status(self, request_id: str) -> Optional[CommandExecutionStatus]:
        """Get status of command execution"""
        return self.active_executions.get(request_id)
    
    def get_connected_agents(self) -> List[str]:
        """Get list of connected agent names"""
        return list(self.agent_connections.keys())
    
    def get_supported_commands(self) -> Dict[str, Dict[str, List[str]]]:
        """Get supported commands by execution location"""
        return {
            "agent": self.classifier.get_supported_agent_commands(),
            "core": self.classifier.get_supported_core_commands(),
            "hybrid": self.classifier.get_supported_hybrid_commands()
        }
    
    async def _cancel_cleanup_tasks(self):
        """Cancel all pending cleanup tasks for proper shutdown"""
        for task_id, task in self.cleanup_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    # Expected behavior when cancelling tasks - continue cleanup
                    self.logger.debug(f"Cleanup task {task_id} cancelled successfully")
                    # Re-raise CancelledError to maintain proper asyncio behavior
                    raise
        self.cleanup_tasks.clear()


# Global service instance
_service_instance: Optional[AgentCommandService] = None


def get_agent_command_service() -> AgentCommandService:
    """Get singleton agent command service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentCommandService()
    return _service_instance