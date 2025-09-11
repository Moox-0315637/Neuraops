# src/core/command_classifier.py
"""
Command Classification for Agent vs Core Execution

CLAUDE.md: < 500 lignes, single responsibility pour classification des commandes
Détermine où chaque commande doit être exécutée (agent, core, ou hybride)
"""
from enum import Enum
from typing import List, Dict, Set, Optional
from dataclasses import dataclass


class ExecutionLocation(str, Enum):
    """Where a command should be executed"""
    AGENT = "agent"      # Execute on agent host
    CORE = "core"        # Execute on core server
    HYBRID = "hybrid"    # Agent collects data + Core processes with AI


@dataclass
class CommandClassification:
    """Result of command classification"""
    location: ExecutionLocation
    command: str
    subcommand: Optional[str]
    reasoning: str
    requires_ai: bool = False
    requires_local_access: bool = False


class CommandClassifier:
    """
    Classify commands to determine execution location
    
    CLAUDE.md: Keep simple with clear classification rules
    """
    
    # Commands that must run on agent (local system information)
    AGENT_COMMANDS: Dict[str, Set[str]] = {
        "health": {
            "disk", "cpu-memory", "network", "monitor", "processes",
            "system-health", "check-disk-usage", "check-cpu-memory",
            "check-network", "list-processes", "check-disk-status"
        },
        "system": {
            "info", "environment", "show-environment",
            "system-info", "get-system-info"
        }
    }
    
    # Commands that must run on core (AI processing, infrastructure)
    CORE_COMMANDS: Dict[str, Set[str]] = {
        "health": {
            ""  # health command without subcommand runs on core
        },
        "infrastructure": {
            "generate", "deploy", "monitor-infra", "analyze", "scale",
            "ai-generate-infrastructure", "deploy-infrastructure",
            "monitor-infrastructure", "analyze-infrastructure",
            "scale-resource", "apply-manifest", "cost-analysis",
            "security-scan", "compliance-check", "performance-analysis",
            "comprehensive-analysis", "list-available-templates",
            "generate-template"
        },
        "incidents": {
            "detect", "respond", "playbook", "create", "manage",
            "analyze", "predict"
        },
        "workflows": {
            "run", "create", "manage", "list", "status", "cancel"
        },
        "ai": {
            "ask", "predict", "assistant", "analyze", "generate"
        },
        "demo": {
            "run", "list", "interactive", "scenario"
        },
        "agents": {
            "list", "status", "register", "unregister", "manage"
        }
    }
    
    # Commands that require both agent and core (hybrid execution)
    HYBRID_COMMANDS: Dict[str, Set[str]] = {
        "logs": {
            "analyze"  # Agent reads file + Core AI analysis
        },
        "health": {
            "analyze"  # Agent collects + Core AI analysis
        },
        "system": {
            "audit"    # Agent scans + Core security audit
        }
    }
    
    def __init__(self):
        """Initialize command classifier"""
        self._build_command_index()
    
    def _build_command_index(self) -> None:
        """Build internal command index for fast lookup"""
        self._agent_index: Dict[str, ExecutionLocation] = {}
        self._core_index: Dict[str, ExecutionLocation] = {}
        self._hybrid_index: Dict[str, ExecutionLocation] = {}
        
        # Build agent command index
        for module, commands in self.AGENT_COMMANDS.items():
            for cmd in commands:
                key = f"{module}.{cmd}"
                self._agent_index[key] = ExecutionLocation.AGENT
        
        # Build core command index  
        for module, commands in self.CORE_COMMANDS.items():
            for cmd in commands:
                key = f"{module}.{cmd}" if cmd else module  # Handle empty subcommand
                self._core_index[key] = ExecutionLocation.CORE
        
        # Build hybrid command index
        for module, commands in self.HYBRID_COMMANDS.items():
            for cmd in commands:
                key = f"{module}.{cmd}"
                self._hybrid_index[key] = ExecutionLocation.HYBRID
    
    def classify_command(self, command: str, args: List[str]) -> CommandClassification:
        """
        Classify a command to determine execution location
        
        Args:
            command: Main command (e.g., 'health', 'system')
            args: Command arguments (e.g., ['disk'], ['info'])
            
        Returns:
            CommandClassification with execution location and reasoning
        """
        # Determine subcommand
        subcommand = args[0] if args else None
        command_key = f"{command}.{subcommand}" if subcommand else command
        
        # Check hybrid commands first (most specific)
        if command_key in self._hybrid_index:
            return CommandClassification(
                location=ExecutionLocation.HYBRID,
                command=command,
                subcommand=subcommand,
                reasoning=f"Hybrid: {command} {subcommand} requires local data collection + AI processing",
                requires_ai=True,
                requires_local_access=True
            )
        
        # Check core commands first for base commands without subcommands
        if command_key in self._core_index:
            return CommandClassification(
                location=ExecutionLocation.CORE,
                command=command,
                subcommand=subcommand,
                reasoning=f"Core: {command} {subcommand or ''} requires centralized processing",
                requires_ai=True if command != "health" else False
            )
        
        # Check agent commands (local system access)
        if command_key in self._agent_index:
            return CommandClassification(
                location=ExecutionLocation.AGENT,
                command=command,
                subcommand=subcommand,
                reasoning=f"Agent: {command} {subcommand} requires local system information",
                requires_local_access=True
            )
        
        # Check module-level fallbacks - prioritize core for base commands
        if command in self.CORE_COMMANDS:
            return CommandClassification(
                location=ExecutionLocation.CORE,
                command=command,
                subcommand=subcommand,
                reasoning=f"Core: {command} module requires centralized processing",
                requires_ai=True if command != "health" else False
            )
        
        if command in self.AGENT_COMMANDS:
            return CommandClassification(
                location=ExecutionLocation.AGENT,
                command=command,
                subcommand=subcommand,
                reasoning=f"Agent: {command} module handles local system operations",
                requires_local_access=True
            )
        
        # Default fallback to core
        return CommandClassification(
            location=ExecutionLocation.CORE,
            command=command,
            subcommand=subcommand,
            reasoning=f"Core: Unknown command {command} defaults to centralized execution",
            requires_ai=False
        )
    
    def is_agent_command(self, command: str, subcommand: Optional[str] = None) -> bool:
        """Check if command should execute on agent"""
        classification = self.classify_command(command, [subcommand] if subcommand else [])
        return classification.location == ExecutionLocation.AGENT
    
    def is_core_command(self, command: str, subcommand: Optional[str] = None) -> bool:
        """Check if command should execute on core"""
        classification = self.classify_command(command, [subcommand] if subcommand else [])
        return classification.location == ExecutionLocation.CORE
    
    def is_hybrid_command(self, command: str, subcommand: Optional[str] = None) -> bool:
        """Check if command requires hybrid execution"""
        classification = self.classify_command(command, [subcommand] if subcommand else [])
        return classification.location == ExecutionLocation.HYBRID
    
    def get_supported_agent_commands(self) -> Dict[str, List[str]]:
        """Get all supported agent-side commands"""
        return {module: list(commands) for module, commands in self.AGENT_COMMANDS.items()}
    
    def get_supported_core_commands(self) -> Dict[str, List[str]]:
        """Get all supported core-side commands"""
        return {module: list(commands) for module, commands in self.CORE_COMMANDS.items()}
    
    def get_supported_hybrid_commands(self) -> Dict[str, List[str]]:
        """Get all supported hybrid commands"""
        return {module: list(commands) for module, commands in self.HYBRID_COMMANDS.items()}


# Global classifier instance
_classifier_instance: Optional[CommandClassifier] = None


def get_command_classifier() -> CommandClassifier:
    """Get singleton command classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = CommandClassifier()
    return _classifier_instance