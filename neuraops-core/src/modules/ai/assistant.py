"""
NeuraOps AI Assistant
Conversational AI assistant with natural language processing, command suggestions, and context retention
"""

import asyncio
import logging
import re
import shlex
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from ...core.engine import get_engine
from ...core.command_executor import CommandExecutor
from ...core.structured_output import CommandSuggestion, AssistantResponse

from .analysis_engine import AdvancedAIAnalysisEngine

logger = logging.getLogger(__name__)

# Command constants to avoid duplication
CMD_LOGS_ANALYZE = "neuraops logs analyze"
CMD_LOGS_MONITOR = "neuraops logs monitor"
CMD_HEALTH_CHECK = "neuraops health check"
CMD_HEALTH_MONITOR = "neuraops health monitor"
CMD_INFRA_ANALYZE = "neuraops infra analyze"
CMD_INFRA_SECURITY_SCAN = "neuraops infra security-scan"


class MessageRole(Enum):
    """Roles in conversation"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class IntentType(Enum):
    """Types of user intents"""

    QUESTION = "question"  # Information seeking
    COMMAND = "command"  # Execute command
    ANALYSIS = "analysis"  # Analyze data
    TROUBLESHOOT = "troubleshoot"  # Fix an issue
    CONFIGURE = "configure"  # Configure the system
    MONITOR = "monitor"  # Monitor resources
    UNKNOWN = "unknown"  # Unclear intent


@dataclass
class ConversationMessage:
    """Message in conversation history"""

    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for the current conversation"""

    conversation_id: str
    subject: Optional[str] = None
    active_components: List[str] = field(default_factory=list)
    referenced_resources: List[str] = field(default_factory=list)
    session_start: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandIntent:
    """Extracted command intent from natural language"""

    command: str
    args: List[str]
    confidence: float  # 0-1 confidence score
    alternatives: List[str] = field(default_factory=list)
    explanation: Optional[str] = None


class AIAssistant:
    """Conversational AI assistant for NeuraOps"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.analysis_engine = AdvancedAIAnalysisEngine()
        self.conversation_history: Dict[str, List[ConversationMessage]] = {}
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.command_mappings: Dict[str, Dict[str, Any]] = {}
        self.troubleshooting_flows: Dict[str, Dict[str, Any]] = {}

        # Initialize with known command mappings
        self._initialize_command_mappings()
        self._initialize_troubleshooting_flows()

    def _initialize_command_mappings(self):
        """Initialize mappings from natural language to CLI commands"""

        self.command_mappings = {
            # Logs commands
            "analyze logs": {
                "command": CMD_LOGS_ANALYZE,
                "variations": ["check logs", "examine logs", "investigate logs", "review logs"],
                "parameters": {
                    "file": {"flag": "--file", "description": "Log file path"},
                    "format": {"flag": "--format", "description": "Log format"},
                    "limit": {"flag": "--limit", "description": "Maximum number of log entries"},
                },
            },
            "monitor logs": {
                "command": CMD_LOGS_MONITOR,
                "variations": ["watch logs", "track logs", "follow logs"],
                "parameters": {
                    "file": {"flag": "--file", "description": "Log file path"},
                    "interval": {
                        "flag": "--interval",
                        "description": "Refresh interval in seconds",
                    },
                },
            },
            # Health commands
            "check health": {
                "command": CMD_HEALTH_CHECK,
                "variations": ["system health", "health status", "verify health"],
                "parameters": {
                    "components": {"flag": "--components", "description": "Components to check"},
                    "timeout": {"flag": "--timeout", "description": "Timeout in seconds"},
                },
            },
            "monitor system": {
                "command": CMD_HEALTH_MONITOR,
                "variations": ["track system", "system monitoring", "watch resources"],
                "parameters": {
                    "interval": {
                        "flag": "--interval",
                        "description": "Refresh interval in seconds",
                    },
                    "duration": {"flag": "--duration", "description": "Duration in seconds"},
                },
            },
            # Infrastructure commands
            "generate template": {
                "command": "neuraops infra generate",
                "variations": ["create template", "new template", "make template"],
                "parameters": {
                    "output": {"flag": "--output", "description": "Output directory"},
                    "var": {"flag": "--var", "description": "Template variables"},
                },
            },
            "deploy infrastructure": {
                "command": "neuraops infra deploy",
                "variations": ["apply infrastructure", "launch infrastructure"],
                "parameters": {"dry-run": {"flag": "--dry-run", "description": "Validate without deployment"}},
            },
            "analyze infrastructure": {
                "command": CMD_INFRA_ANALYZE,
                "variations": ["check infrastructure", "evaluate infrastructure"],
                "parameters": {
                    "cloud": {"flag": "--cloud", "description": "Include cloud resources"},
                    "output": {"flag": "--output", "description": "Output file for report"},
                },
            },
            "security scan": {
                "command": CMD_INFRA_SECURITY_SCAN,
                "variations": ["scan security", "check security", "audit security"],
                "parameters": {"output": {"flag": "--output", "description": "Output file for report"}},
            },
        }

    def _initialize_troubleshooting_flows(self):
        """Initialize troubleshooting flows for common issues"""

        self.troubleshooting_flows = {
            "high_cpu_usage": {
                "name": "High CPU Usage Troubleshooting",
                "steps": [
                    "Check system load with 'neuraops system info'",
                    "Identify top processes with 'neuraops system processes --sort cpu'",
                    "Analyze resource bottlenecks with 'neuraops infra analyze'",
                    "Monitor CPU usage trend with 'neuraops health monitor --component cpu'",
                ],
            },
            "service_unavailable": {
                "name": "Service Unavailability Troubleshooting",
                "steps": [
                    "Check service status with 'neuraops system services'",
                    "Verify network connectivity with 'neuraops health network'",
                    "Examine recent logs with 'neuraops logs analyze --service {service_name}'",
                    "Check infrastructure health with 'neuraops infra check'",
                ],
            },
            "deployment_failure": {
                "name": "Deployment Failure Troubleshooting",
                "steps": [
                    "Validate deployment configuration with 'neuraops infra deploy --dry-run {config_file}'",
                    "Check for resource conflicts with 'neuraops infra analyze'",
                    "Examine deployment logs with 'neuraops logs analyze --deployment {deployment_name}'",
                    "Verify infrastructure status with 'neuraops infra check'",
                ],
            },
        }

    async def process_message(self, message: str, conversation_id: str = "default") -> AssistantResponse:
        """Process user message and generate response"""

        try:
            # Create or retrieve conversation context
            _ = self._get_or_create_conversation_context(conversation_id)

            # Add message to conversation history
            self._add_message_to_history(conversation_id, MessageRole.USER, message)

            # Analyze user intent
            intent = await self._analyze_intent(message, conversation_id)

            # Process based on intent
            if intent == IntentType.QUESTION:
                response = await self._handle_question(message, conversation_id)
            elif intent == IntentType.COMMAND:
                response = await self._handle_command(message, conversation_id)
            elif intent == IntentType.ANALYSIS:
                response = await self._handle_analysis(message, conversation_id)
            elif intent == IntentType.TROUBLESHOOT:
                response = await self._handle_troubleshooting(message, conversation_id)
            elif intent == IntentType.CONFIGURE:
                response = await self._handle_configuration(message, conversation_id)
            elif intent == IntentType.MONITOR:
                response = await self._handle_monitoring(message, conversation_id)
            else:
                response = await self._generate_general_response(message, conversation_id)

            # Update conversation context
            self._update_conversation_context(conversation_id, message, response)

            # Add response to conversation history
            self._add_message_to_history(conversation_id, MessageRole.ASSISTANT, response.message)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return AssistantResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                commands=[],
                suggestions=[],
                success=False,
                error_message=str(e),
            )

    async def _analyze_intent(self, message: str, _conversation_id: str) -> IntentType:
        """Analyze user intent from message"""

        # Check for common intent patterns
        message_lower = message.lower()

        # Command intent patterns
        if any(keyword in message_lower for keyword in ["run", "execute", "start", "launch"]):
            return IntentType.COMMAND

        # Analysis intent patterns
        if any(keyword in message_lower for keyword in ["analyze", "analyze", "examine", "investigate", "review"]):
            return IntentType.ANALYSIS

        # Troubleshooting intent patterns
        if any(keyword in message_lower for keyword in ["troubleshoot", "debug", "fix", "solve", "issue", "problem", "error"]):
            return IntentType.TROUBLESHOOT

        # Configuration intent patterns
        if any(keyword in message_lower for keyword in ["configure", "setup", "set", "config", "change", "modify"]):
            return IntentType.CONFIGURE

        # Monitoring intent patterns
        if any(keyword in message_lower for keyword in ["monitor", "watch", "track", "observe"]):
            return IntentType.MONITOR

        # Question intent patterns
        if message_lower.startswith(("what", "how", "why", "when", "where", "who", "can you", "could you")) or "?" in message:
            return IntentType.QUESTION

        # For more complex cases, use AI to determine intent
        engine = get_engine()

        prompt = f"""
Determine the primary intent of this user message:
"{message}"

Select ONE of the following intent types:
1. QUESTION - User is asking for information
2. COMMAND - User wants to execute a command
3. ANALYSIS - User wants to analyze data or system state
4. TROUBLESHOOT - User has an issue they need help fixing
5. CONFIGURE - User wants to configure the system
6. MONITOR - User wants to monitor resources

Respond with ONLY the intent type (e.g., "QUESTION").
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are determining user intent for an AI assistant. Respond with only the intent type.",
            max_tokens=10,
        )

        # Parse response
        response = response.strip().upper()
        try:
            return IntentType[response]
        except (KeyError, ValueError):
            # Default to UNKNOWN if the response doesn't match an intent type
            return IntentType.UNKNOWN

    async def _handle_question(self, message: str, conversation_id: str) -> AssistantResponse:
        """Handle information-seeking questions"""

        engine = get_engine()
        context = self._get_conversation_context(conversation_id)

        # Get relevant context from conversation history
        history_context = self._get_relevant_history(conversation_id)

        prompt = f"""
User question: {message}

Conversation context:
{history_context}

Answer the user's question based on your knowledge of DevOps, infrastructure, and system administration.
Provide a helpful, accurate, and concise response.
If you don't know the answer, say so rather than speculating.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a DevOps assistant providing helpful information about systems, infrastructure, and best practices.",
            max_tokens=1024,
        )

        # Generate command suggestions based on the question
        suggestions = await self._generate_command_suggestions(message, context)

        return AssistantResponse(message=response, commands=[], suggestions=suggestions, success=True)

    async def _handle_command(self, message: str, conversation_id: str) -> AssistantResponse:
        """Handle command execution requests"""

        context = self._get_conversation_context(conversation_id)

        # Extract command intent from natural language
        command_intent = await self._extract_command_intent(message, context)

        if command_intent.confidence < 0.7:
            # Confidence too low to execute, offer suggestions instead
            return AssistantResponse(
                message="I'm not entirely sure what command you'd like to run. Did you mean one of these?\n\n" + "\n".join([f"- `{alt}`" for alt in command_intent.alternatives]),
                commands=[],
                suggestions=[CommandSuggestion(command=alt) for alt in command_intent.alternatives],
                success=True,
            )

        # Prepare response with command explanation if available
        response_text = f"Running command: `{command_intent.command}`"
        if command_intent.explanation:
            response_text += f"\n\n{command_intent.explanation}"

        return AssistantResponse(message=response_text, commands=[command_intent.command], suggestions=[], success=True)

    async def _handle_analysis(self, message: str, conversation_id: str) -> AssistantResponse:
        """Handle analysis requests"""

        engine = get_engine()
        context = self._get_conversation_context(conversation_id)

        # Determine what to analyze
        analysis_target = await self._determine_analysis_target(message, context)

        # Generate appropriate analysis command based on target
        if analysis_target == "logs":
            command = self._build_logs_analysis_command(message, context)
        elif analysis_target == "infrastructure":
            command = self._build_infra_analysis_command(message)
        elif analysis_target == "performance":
            command = "neuraops infra performance-analysis"
        else:
            return await self._generate_generic_analysis_response(message, engine)

        # Explain what analysis will be performed
        explanation = f"I'll analyze your {analysis_target} with `{command}`"
        return AssistantResponse(message=explanation, commands=[command], suggestions=[], success=True)

    def _build_logs_analysis_command(self, message: str, context: ConversationContext) -> str:
        """Build logs analysis command with appropriate flags"""
        command = CMD_LOGS_ANALYZE

        if "error" in message.lower() or "issue" in message.lower():
            command += " --filter severity=error"
        if "recent" in message.lower() or "latest" in message.lower():
            command += " --limit 100"
        if any(resource in message.lower() for resource in context.referenced_resources):
            for resource in context.referenced_resources:
                if resource in message.lower():
                    command += f" --resource {resource}"
                    break
        return command

    def _build_infra_analysis_command(self, message: str) -> str:
        """Build infrastructure analysis command with appropriate flags"""
        command = CMD_INFRA_ANALYZE

        if "cloud" in message.lower():
            command += " --cloud"
        if "cost" in message.lower() or "spending" in message.lower():
            command = "neuraops infra cost-analysis"
        if "security" in message.lower() or "vulnerabilit" in message.lower():
            command = CMD_INFRA_SECURITY_SCAN
        return command

    async def _generate_generic_analysis_response(self, message: str, engine) -> AssistantResponse:
        """Generate generic analysis response when target is unclear"""
        prompt = f"""
The user wants to analyze something: "{message}"

Based on the request, explain what you can analyze and how to proceed.
Suggest specific commands they might want to run for different types of analysis.
"""
        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a DevOps assistant helping users analyze their systems and infrastructure.",
            max_tokens=768,
        )

        return AssistantResponse(
            message=response,
            commands=[],
            suggestions=[
                CommandSuggestion(command=CMD_LOGS_ANALYZE, description="Analyze system logs"),
                CommandSuggestion(command=CMD_INFRA_ANALYZE, description="Analyze infrastructure"),
                CommandSuggestion(
                    command=CMD_INFRA_SECURITY_SCAN,
                    description="Scan for security issues",
                ),
            ],
            success=True,
        )

    async def _handle_troubleshooting(self, message: str, conversation_id: str) -> AssistantResponse:
        """Handle troubleshooting requests"""

        engine = get_engine()
        context = self._get_conversation_context(conversation_id)

        # Determine issue type
        issue_type = await self._identify_issue_type(message, context)

        # Check if we have a predefined troubleshooting flow
        if issue_type in self.troubleshooting_flows:
            flow = self.troubleshooting_flows[issue_type]

            # Customize flow for specific context if needed
            if "{service_name}" in str(flow):
                service_name = self._extract_service_name(message, context)
                flow = {
                    "name": flow["name"],
                    "steps": [step.replace("{service_name}", service_name) for step in flow["steps"]],
                }

            if "{deployment_name}" in str(flow):
                deployment_name = self._extract_deployment_name(message, context)
                flow = {
                    "name": flow["name"],
                    "steps": [step.replace("{deployment_name}", deployment_name) for step in flow["steps"]],
                }

            # Present troubleshooting flow
            steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(flow["steps"])])
            response_text = f"Let's troubleshoot the {flow['name']}:\n\n{steps_text}\n\nShall we start with step 1?"

            # Suggest first command
            first_command = flow["steps"][0].split("'")[1] if "'" in flow["steps"][0] else ""

            return AssistantResponse(
                message=response_text,
                commands=[],
                suggestions=[CommandSuggestion(command=first_command)] if first_command else [],
                success=True,
            )

        # For unknown issues, generate AI-based troubleshooting guide
        prompt = f"""
The user is experiencing an issue: "{message}"

Create a step-by-step troubleshooting guide to help identify and resolve the problem.
Include specific commands to run and what to look for in the output.
Focus on practical diagnostic steps and potential solutions.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a DevOps troubleshooting expert helping diagnose and fix technical issues.",
            max_tokens=1024,
        )

        # Extract potential commands from the response
        commands = self._extract_commands_from_text(response)

        return AssistantResponse(
            message=response,
            commands=[],
            suggestions=[CommandSuggestion(command=cmd) for cmd in commands[:3]],
            success=True,
        )

    async def _handle_configuration(self, message: str, conversation_id: str) -> AssistantResponse:
        """Handle system configuration requests"""

        engine = get_engine()
        context = self._get_conversation_context(conversation_id)

        # Determine what the user wants to configure
        config_target = await self._determine_config_target(message, context)

        # For configuration, we often want to guide rather than execute directly
        prompt = f"""
The user wants to configure {config_target}: "{message}"

Provide a helpful response that:
1. Explains how to properly configure {config_target}
2. Includes specific commands or steps
3. Mentions important considerations or best practices
4. Asks clarifying questions if needed
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a DevOps configuration expert helping users set up and configure their systems.",
            max_tokens=1024,
        )

        # Extract potential commands from the response
        commands = self._extract_commands_from_text(response)

        return AssistantResponse(
            message=response,
            commands=[],
            suggestions=[CommandSuggestion(command=cmd) for cmd in commands[:3]],
            success=True,
        )

    async def _handle_monitoring(self, message: str, conversation_id: str) -> AssistantResponse:
        """Handle monitoring requests"""

        context = self._get_conversation_context(conversation_id)

        # Determine what to monitor
        monitor_target = await self._determine_monitor_target(message, context)

        # Generate appropriate monitoring command based on target
        if monitor_target == "logs":
            command = self._build_logs_monitor_command(message, context)
        elif monitor_target == "infrastructure":
            command = self._build_infra_monitor_command(message)
        elif monitor_target == "system":
            command = self._build_health_monitor_command(message)
        else:
            return self._generate_monitoring_menu()

        # Add duration and generate explanation
        duration = self._extract_monitor_duration(message)
        command = self._add_duration_to_command(command, duration)
        explanation = f"I'll monitor your {monitor_target} for {duration} seconds with `{command}`"

        return AssistantResponse(message=explanation, commands=[command], suggestions=[], success=True)

    def _build_logs_monitor_command(self, message: str, context: ConversationContext) -> str:
        """Build logs monitoring command with appropriate flags"""
        command = CMD_LOGS_MONITOR

        if "error" in message.lower():
            command += " --filter severity=error"
        if any(resource in message.lower() for resource in context.referenced_resources):
            for resource in context.referenced_resources:
                if resource in message.lower():
                    command += f" --resource {resource}"
                    break
        return command

    def _build_infra_monitor_command(self, message: str) -> str:
        """Build infrastructure monitoring command with appropriate flags"""
        command = "neuraops infra monitor"

        if "kubernetes" in message.lower() or "k8s" in message.lower():
            command += " --namespace default"
        if "cloud" in message.lower():
            command += " --cloud"
        return command

    def _build_health_monitor_command(self, message: str) -> str:
        """Build health monitoring command with appropriate flags"""
        command = CMD_HEALTH_MONITOR

        if "cpu" in message.lower():
            command += " --component cpu"
        elif "memory" in message.lower():
            command += " --component memory"
        elif "disk" in message.lower():
            command += " --component disk"
        elif "network" in message.lower():
            command += " --component network"
        return command

    def _generate_monitoring_menu(self) -> AssistantResponse:
        """Generate generic monitoring menu when target is unclear"""
        return AssistantResponse(
            message="I can help you monitor different aspects of your system. What would you like to monitor?",
            commands=[],
            suggestions=[
                CommandSuggestion(command=CMD_LOGS_MONITOR, description="Monitor system logs"),
                CommandSuggestion(command="neuraops infra monitor", description="Monitor infrastructure"),
                CommandSuggestion(command=CMD_HEALTH_MONITOR, description="Monitor system health"),
            ],
            success=True,
        )

    def _extract_monitor_duration(self, message: str) -> int:
        """Extract monitoring duration from message, default to 60 seconds"""
        duration = 60  # Default to 60 seconds
        for word in message.lower().split():
            if word.isdigit():
                duration = int(word)
                break
        return duration

    def _add_duration_to_command(self, command: str, duration: int) -> str:
        """Add duration flag to command if applicable"""
        if "infra monitor" in command or "health monitor" in command:
            command += f" --duration {duration}"
        return command

    async def _generate_general_response(self, message: str, conversation_id: str) -> AssistantResponse:
        """Generate general response when intent is unclear"""

        engine = get_engine()
        context = self._get_conversation_context(conversation_id)
        history = self._get_relevant_history(conversation_id)

        prompt = f"""
User message: {message}

Conversation context:
{history}

Provide a helpful response. If the user's intent is unclear, suggest possible options to help them.
Focus on DevOps, infrastructure, and system administration topics.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a helpful DevOps assistant. Provide guidance and suggest useful commands or actions.",
            max_tokens=768,
        )

        # Generate command suggestions
        suggestions = await self._generate_command_suggestions(message, context)

        return AssistantResponse(message=response, commands=[], suggestions=suggestions, success=True)

    def _extract_command_from_backticks(self, message: str) -> Optional[CommandIntent]:
        """Extract command from backticks in user message"""
        command_match = re.search(r"`([^`]+)`", message)
        if command_match:
            command = command_match.group(1).strip()
            args = shlex.split(command)[1:] if len(shlex.split(command)) > 1 else []
            return CommandIntent(
                command=command,
                args=args,
                confidence=0.95,
                alternatives=[],
                explanation="Executing the exact command you specified.",
            )
        return None

    def _check_message_match(self, message: str, key: str, mapping: Dict[str, Any]) -> bool:
        """Check if message matches a command mapping key or variations"""
        return key in message.lower() or any(variation in message.lower() for variation in mapping.get("variations", []))

    def _extract_parameters_from_message(self, message: str, mapping: Dict[str, Any], base_command: str) -> str:
        """Extract parameters from message and build command with parameters"""
        command_with_params = base_command

        for param_name, param_info in mapping.get("parameters", {}).items():
            if param_name in message.lower():
                pattern = rf"{param_name}\s+(\w+)"
                param_match = re.search(pattern, message.lower())
                if param_match:
                    value = param_match.group(1)
                    command_with_params += f" {param_info['flag']} {value}"

        return command_with_params

    def _generate_command_alternatives(self, mapping: Dict[str, Any]) -> List[str]:
        """Generate alternative commands from mapping variations"""
        alternatives = [mapping["command"]]
        for variation in mapping.get("variations", [])[:2]:
            alternatives.append(f"{mapping['command']} # ({variation})")
        return alternatives

    def _match_known_command_mappings(self, message: str) -> Optional[CommandIntent]:
        """Match message against known command mappings"""
        for key, mapping in self.command_mappings.items():
            if self._check_message_match(message, key, mapping):
                base_command = mapping["command"]
                command_with_params = self._extract_parameters_from_message(message, mapping, base_command)
                alternatives = self._generate_command_alternatives(mapping)

                return CommandIntent(
                    command=command_with_params,
                    args=[],
                    confidence=0.85,
                    alternatives=alternatives,
                    explanation=f"Executing the '{key}' command with relevant parameters.",
                )
        return None

    async def _generate_ai_command_intent(self, message: str, engine) -> CommandIntent:
        """Generate command intent using AI when no direct matches found"""
        prompt = f"""
The user wants to execute a command: "{message}"

Determine the most appropriate NeuraOps CLI command to run based on their request.
The available command categories include:
- neuraops logs (for log analysis and monitoring)
- neuraops health (for system health checks and monitoring)
- neuraops system (for system information and management)
- neuraops infra (for infrastructure management)

Respond with ONLY the command to run, including any relevant parameters.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are determining the most appropriate CLI command to run. Respond with only the command.",
            max_tokens=128,
        )

        # Generate alternatives
        alt_prompt = f"""
Generate 3 alternative commands that might satisfy this user request: "{message}"
Respond with only the commands, one per line.
"""

        alt_response = await engine.generate_text(
            prompt=alt_prompt,
            system_prompt="You are generating alternative CLI commands. Respond with only the commands.",
            max_tokens=128,
        )

        alternatives = [line.strip() for line in alt_response.strip().split("\n") if line.strip()]

        return CommandIntent(
            command=response.strip(),
            args=[],
            confidence=0.7,
            alternatives=alternatives,
            explanation="I've determined this command based on your request.",
        )

    async def _extract_command_intent(self, message: str, context: ConversationContext) -> CommandIntent:
        """Extract command intent from natural language"""
        engine = get_engine()

        # Try exact command patterns first
        command_intent = self._extract_command_from_backticks(message)
        if command_intent:
            return command_intent

        # Try known command mappings
        command_intent = self._match_known_command_mappings(message)
        if command_intent:
            return command_intent

        # Use AI for unknown patterns
        return await self._generate_ai_command_intent(message, engine)

    async def _determine_analysis_target(self, message: str, context: ConversationContext) -> str:
        """Determine what the user wants to analyze"""
        # Make function truly async
        await asyncio.sleep(0)

        message_lower = message.lower()

        # Simple keyword matching
        if any(keyword in message_lower for keyword in ["log", "logs", "error", "warning"]):
            return "logs"

        if any(
            keyword in message_lower
            for keyword in [
                "infrastructure",
                "system",
                "resource",
                "cloud",
                "cluster",
                "kubernetes",
                "k8s",
                "docker",
            ]
        ):
            return "infrastructure"

        if any(
            keyword in message_lower
            for keyword in [
                "performance",
                "slow",
                "speed",
                "response time",
                "latency",
                "throughput",
            ]
        ):
            return "performance"

        if any(keyword in message_lower for keyword in ["security", "vulnerability", "threat", "compliance", "risk"]):
            return "security"

        # Look at recent conversation context
        for component in context.active_components:
            if component in ["logs", "infrastructure", "security", "performance"]:
                return component

        # Default to infrastructure if unclear
        return "infrastructure"

    async def _identify_issue_type(self, message: str, context: ConversationContext) -> str:
        """Identify the type of issue from troubleshooting request"""

        message_lower = message.lower()

        # Match against known issue patterns
        if any(keyword in message_lower for keyword in ["cpu", "processor", "load", "high usage"]):
            return "high_cpu_usage"

        if any(keyword in message_lower for keyword in ["service", "unavailable", "down", "stopped", "not working"]):
            return "service_unavailable"

        if any(keyword in message_lower for keyword in ["deploy", "deployment", "failed", "failure", "not deploying"]):
            return "deployment_failure"

        # Use AI to determine issue type for complex cases
        engine = get_engine()

        prompt = f"""
The user is reporting an issue: "{message}"

Categorize this issue into one of these types:
1. high_cpu_usage - Issues related to high CPU utilization
2. service_unavailable - Service availability problems
3. deployment_failure - Issues with deployment processes
4. unknown - None of the above

Respond with ONLY the issue type (e.g., "high_cpu_usage").
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are categorizing a user-reported issue. Respond with only the issue type.",
            max_tokens=16,
        )

        response = response.strip().lower()
        return response if response in ["high_cpu_usage", "service_unavailable", "deployment_failure"] else "unknown"

    async def _determine_config_target(self, message: str, context: ConversationContext) -> str:
        """Determine what the user wants to configure"""
        # Make function truly async
        await asyncio.sleep(0)

        message_lower = message.lower()

        # Simple keyword matching
        if any(keyword in message_lower for keyword in ["log", "logging", "log level"]):
            return "logging"

        if any(keyword in message_lower for keyword in ["alert", "notification", "monitoring threshold"]):
            return "alerts"

        if any(keyword in message_lower for keyword in ["infrastructure", "template", "deployment"]):
            return "infrastructure"

        if any(keyword in message_lower for keyword in ["system", "environment", "variable", "env var"]):
            return "system environment"

        if any(keyword in message_lower for keyword in ["security", "authentication", "permission", "access"]):
            return "security"

        # Default
        return "system settings"

    async def _determine_monitor_target(self, message: str, context: ConversationContext) -> str:
        """Determine what the user wants to monitor"""
        # Make function truly async
        await asyncio.sleep(0)

        message_lower = message.lower()

        # Simple keyword matching
        if any(keyword in message_lower for keyword in ["log", "logs", "error", "warning"]):
            return "logs"

        if any(
            keyword in message_lower
            for keyword in [
                "infrastructure",
                "kubernetes",
                "k8s",
                "docker",
                "container",
                "pod",
                "cluster",
            ]
        ):
            return "infrastructure"

        if any(keyword in message_lower for keyword in ["system", "cpu", "memory", "disk", "network", "load"]):
            return "system"

        # Look at recent conversation context
        for component in context.active_components:
            if component in ["logs", "infrastructure", "system"]:
                return component

        # Default
        return "system"

    def _extract_service_name(self, message: str, context: ConversationContext) -> str:
        """Extract service name from message"""

        # Look for service name in message
        service_match = re.search(r"service\s+(\w+)", message.lower())
        if service_match:
            return service_match.group(1)

        # Look for service name in context
        for resource in context.referenced_resources:
            if "service" in resource.lower():
                return resource

        # Default
        return "unknown-service"

    def _extract_deployment_name(self, message: str, context: ConversationContext) -> str:
        """Extract deployment name from message"""

        # Look for deployment name in message
        deployment_match = re.search(r"deployment\s+(\w+)", message.lower())
        if deployment_match:
            return deployment_match.group(1)

        # Look for deployment name in context
        for resource in context.referenced_resources:
            if "deploy" in resource.lower():
                return resource

        # Default
        return "unknown-deployment"

    def _extract_commands_from_text(self, text: str) -> List[str]:
        """Extract command suggestions from text"""

        commands = []

        # Look for commands in backticks
        backtick_commands = re.findall(r"`([^`]+)`", text)
        commands.extend([cmd for cmd in backtick_commands if cmd.startswith("neuraops")])

        # Look for commands prefixed with common markers
        line_commands = re.findall(r"(?:^|\n)(?:Run|Execute|Type|Use):\s*(\S+(?:\s+\S+)*)", text, re.IGNORECASE)
        commands.extend([cmd for cmd in line_commands if cmd.startswith("neuraops")])

        return list(set(commands))  # Remove duplicates

    def _get_or_create_conversation_context(self, conversation_id: str) -> ConversationContext:
        """Get existing conversation context or create a new one"""

        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                subject="General Assistance",
                active_components=["system"],
                referenced_resources=[],
                session_start=datetime.now(),
                last_updated=datetime.now(),
            )

        return self.conversation_contexts[conversation_id]

    def _get_conversation_context(self, conversation_id: str) -> ConversationContext:
        """Get conversation context, create if it doesn't exist"""

        return self._get_or_create_conversation_context(conversation_id)

    def _add_message_to_history(self, conversation_id: str, role: MessageRole, content: str) -> None:
        """Add message to conversation history"""

        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []

        self.conversation_history[conversation_id].append(ConversationMessage(role=role, content=content))

        # Trim history if it gets too long (keep last 20 messages)
        if len(self.conversation_history[conversation_id]) > 20:
            self.conversation_history[conversation_id] = self.conversation_history[conversation_id][-20:]

    def _get_relevant_history(self, conversation_id: str, max_messages: int = 5) -> str:
        """Get relevant conversation history formatted for context"""

        if conversation_id not in self.conversation_history:
            return "No previous conversation."

        history = self.conversation_history[conversation_id][-max_messages:]

        formatted_history = []
        for msg in history:
            role_name = "User" if msg.role == MessageRole.USER else "Assistant"
            formatted_history.append(f"{role_name}: {msg.content}")

        return "\n\n".join(formatted_history)

    def _update_conversation_context(self, conversation_id: str, message: str, response: AssistantResponse) -> None:
        """Update conversation context based on message and response"""

        context = self._get_conversation_context(conversation_id)

        # Update timestamp
        context.last_updated = datetime.now()

        # Update active components based on message content
        message_lower = message.lower()
        if "log" in message_lower:
            self._add_unique(context.active_components, "logs")
        if any(word in message_lower for word in ["infrastructure", "kubernetes", "docker", "deploy"]):
            self._add_unique(context.active_components, "infrastructure")
        if any(word in message_lower for word in ["health", "system", "cpu", "memory", "disk"]):
            self._add_unique(context.active_components, "system")
        if any(word in message_lower for word in ["security", "vulnerability", "compliance"]):
            self._add_unique(context.active_components, "security")

        # Extract referenced resources
        self._extract_and_update_resources(context, message)

        # Update subject if needed
        if len(self.conversation_history.get(conversation_id, [])) <= 2:
            # This is a new conversation, try to set subject
            context.subject = self._determine_conversation_subject(message)

    def _extract_and_update_resources(self, context: ConversationContext, message: str) -> None:
        """Extract and update referenced resources in context"""

        # Simple resource extraction patterns
        resource_patterns = [
            (r"service\s+(\w+)", "service"),
            (r"deployment\s+(\w+)", "deployment"),
            (r"container\s+(\w+)", "container"),
            (r"pod\s+(\w+)", "pod"),
            (r"cluster\s+(\w+)", "cluster"),
            (r"node\s+(\w+)", "node"),
            (r"server\s+(\w+)", "server"),
            (r"database\s+(\w+)", "database"),
            (r"file\s+(\S+)", "file"),
        ]

        for pattern, resource_type in resource_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                resource_name = match.group(1)
                resource = f"{resource_type}:{resource_name}"
                self._add_unique(context.referenced_resources, resource)

    def _determine_conversation_subject(self, message: str) -> str:
        """Determine the subject of a conversation from initial message"""

        # Simple subject extraction
        if "log" in message.lower():
            return "Log Analysis"
        if any(word in message.lower() for word in ["health", "status", "check"]):
            return "System Health"
        if any(word in message.lower() for word in ["infrastructure", "kubernetes", "docker", "deploy"]):
            return "Infrastructure Management"
        if any(word in message.lower() for word in ["security", "vulnerability", "compliance"]):
            return "Security & Compliance"
        if any(word in message.lower() for word in ["performance", "optimize", "slow", "fast"]):
            return "Performance Optimization"
        if any(word in message.lower() for word in ["troubleshoot", "debug", "issue", "problem", "error"]):
            return "Troubleshooting"

        return "General Assistance"

    def _add_unique(self, target_list: List[str], item: str) -> None:
        """Add item to list if not already present"""

        if item not in target_list:
            target_list.append(item)

    async def _generate_command_suggestions(self, message: str, context: ConversationContext) -> List[CommandSuggestion]:
        """Generate contextual command suggestions"""
        # Make function truly async
        await asyncio.sleep(0)

        suggestions = []

        # Get active components
        components = context.active_components

        # Suggest commands based on components and message context
        if "logs" in components or "log" in message.lower():
            suggestions.append(
                CommandSuggestion(
                    command=CMD_LOGS_ANALYZE,
                    description="Analyze logs for patterns and issues",
                )
            )

        if "infrastructure" in components or any(word in message.lower() for word in ["infrastructure", "kubernetes", "k8s", "docker"]):
            suggestions.append(CommandSuggestion(command="neuraops infra check", description="Check infrastructure health"))

            if "security" in message.lower():
                suggestions.append(
                    CommandSuggestion(
                        command=CMD_INFRA_SECURITY_SCAN,
                        description="Scan for security vulnerabilities",
                    )
                )

            if "cost" in message.lower() or "spending" in message.lower():
                suggestions.append(
                    CommandSuggestion(
                        command="neuraops infra cost-analysis",
                        description="Analyze infrastructure costs",
                    )
                )

        if "system" in components or any(word in message.lower() for word in ["system", "health", "cpu", "memory"]):
            suggestions.append(CommandSuggestion(command=CMD_HEALTH_CHECK, description="Check system health"))
            suggestions.append(CommandSuggestion(command="neuraops system info", description="Get system information"))

        # Always keep some general suggestions if no specific ones match
        if not suggestions:
            suggestions = [
                CommandSuggestion(command="CMD_HEALTH_CHECK", description="Check system health"),
                CommandSuggestion(command=CMD_LOGS_ANALYZE, description="Analyze logs"),
                CommandSuggestion(command="neuraops infra analyze", description="Analyze infrastructure"),
            ]

        return suggestions[:3]  # Limit to top 3 suggestions

    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get statistics about a conversation"""

        if conversation_id not in self.conversation_history:
            return {"error": "Conversation not found"}

        history = self.conversation_history[conversation_id]
        context = self._get_conversation_context(conversation_id)

        user_messages = [msg for msg in history if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in history if msg.role == MessageRole.ASSISTANT]

        start_time = context.session_start
        duration = (datetime.now() - start_time).total_seconds() / 60  # minutes

        return {
            "conversation_id": conversation_id,
            "subject": context.subject,
            "total_messages": len(history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "duration_minutes": round(duration, 2),
            "active_components": context.active_components,
            "referenced_resources": context.referenced_resources,
            "start_time": start_time.isoformat(),
            "last_updated": context.last_updated.isoformat(),
        }

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history and context"""

        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]

        if conversation_id in self.conversation_contexts:
            del self.conversation_contexts[conversation_id]

        return True


# Convenience functions for assistant integration
async def process_user_query(query: str, conversation_id: str = "default") -> AssistantResponse:
    """Process user query with AI assistant"""

    assistant = AIAssistant()
    return await assistant.process_message(query, conversation_id)


async def suggest_commands(query: str) -> List[CommandSuggestion]:
    """Suggest commands based on user query"""

    assistant = AIAssistant()
    context = assistant._get_or_create_conversation_context("temp")
    return await assistant._generate_command_suggestions(query, context)


async def explain_command(command: str) -> str:
    """Generate explanation for a command"""

    engine = get_engine()

    prompt = f"""
Explain what this command does: {command}

Provide a clear explanation of:
1. The purpose of the command
2. What each parameter/flag does
3. What the expected output would be
4. Any important considerations when using this command
"""

    explanation = await engine.generate_text(
        prompt=prompt,
        system_prompt="You are a helpful assistant explaining command usage and functionality.",
        max_tokens=512,
    )

    return explanation
