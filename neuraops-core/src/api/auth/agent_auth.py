"""
Agent Authentication Service

Handles agent registration and authentication following CLAUDE.md: < 100 lines.
Integrates with JWT handler for secure token-based authentication.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import structlog

from .jwt_handler import JWTHandler
from ...core.structured_output import SafetyLevel

logger = structlog.get_logger()


class AgentRegistration(BaseModel):
    """Agent registration request"""
    agent_name: str
    hostname: str
    capabilities: List[str]
    api_key: str


class AgentInfo(BaseModel):
    """Agent information"""
    agent_id: str
    agent_name: str
    hostname: str
    capabilities: List[str]
    registered_at: str
    status: str = "active"


class AgentAuthService:
    """
    Simplified agent authentication service
    
    CLAUDE.md: Keep It Simple - Direct token validation from config
    """
    
    def __init__(self, jwt_handler: JWTHandler):
        self.jwt_handler = jwt_handler
        self.registered_agents: Dict[str, AgentInfo] = {}
        
        # Get security config directly
        from ...devops_commander.config import get_security_config
        self.security_config = get_security_config()
        
        logger.info("AgentAuthService initialized with simple token validation")
    
    def is_valid_api_key(self, api_key: str) -> bool:
        """Simple validation - check if key is in config or matches user token"""
        # Get valid keys from config
        valid_keys = self.security_config.get_valid_api_keys()
        
        # Check if API key is in the valid keys list
        return api_key in valid_keys
    
    def generate_api_key(self) -> str:
        """Generate new API key"""
        return self.jwt_handler.generate_api_key()
    
    def register_agent(self, registration: AgentRegistration) -> Optional[str]:
        """
        Simple agent registration
        """
        # Handle "generate" case
        if registration.api_key == "generate":
            registration.api_key = self.generate_api_key()
        
        # Simple validation
        if not self.is_valid_api_key(registration.api_key):
            logger.warning("Invalid API key", 
                          agent_name=registration.agent_name,
                          key_length=len(registration.api_key))
            return None
        
        # Validate capabilities
        valid_capabilities = {"logs", "infrastructure", "incidents", "workflows", "health", "metrics", "commands"}
        if not all(cap in valid_capabilities for cap in registration.capabilities):
            logger.warning("Invalid capabilities", capabilities=registration.capabilities)
            return None
        
        # Create agent
        agent_id = f"{registration.hostname}_{registration.agent_name}"
        
        # Store agent info
        from datetime import datetime, timezone
        agent_info = AgentInfo(
            agent_id=agent_id,
            agent_name=registration.agent_name,
            hostname=registration.hostname,
            capabilities=registration.capabilities,
            registered_at=datetime.now(timezone.utc).isoformat()
        )
        self.registered_agents[agent_id] = agent_info
        
        # Create JWT token
        token = self.jwt_handler.create_agent_token(
            agent_id=agent_id,
            capabilities=registration.capabilities
        )
        
        logger.info("Agent registered successfully", agent_id=agent_id)
        return token
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info"""
        return self.registered_agents.get(agent_id)