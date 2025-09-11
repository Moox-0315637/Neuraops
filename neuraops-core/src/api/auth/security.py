"""
Security Utilities for NeuraOps API

Security helpers and validation following CLAUDE.md: < 100 lines.
Rate limiting, capability validation, and security headers.
"""
from typing import List, Dict, Any
from fastapi import HTTPException, status
import time
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """
    Simple rate limiter for API endpoints
    
    CLAUDE.md: Safety-First - Prevent abuse
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # agent_id -> deque of timestamps
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, agent_id: str) -> bool:
        """Check if agent is within rate limits"""
        now = time.time()
        agent_requests = self.requests[agent_id]
        
        # Remove old requests outside the window
        while agent_requests and now - agent_requests[0] > self.window_seconds:
            agent_requests.popleft()
        
        # Check if under limit
        if len(agent_requests) >= self.max_requests:
            logger.warning("Rate limit exceeded", 
                          agent_id=agent_id,
                          requests=len(agent_requests))
            return False
        
        # Add current request
        agent_requests.append(now)
        return True


def validate_agent_capability(required_capability: str, agent_capabilities: List[str]) -> bool:
    """
    Validate that agent has required capability
    
    CLAUDE.md: Safety-First - Capability-based authorization
    """
    if required_capability not in agent_capabilities:
        logger.warning("Insufficient capabilities", 
                      required=required_capability,
                      available=agent_capabilities)
        return False
    return True


def require_capability(capability: str):
    """
    Decorator to require specific capability for endpoint
    
    Usage:
        @require_capability("infrastructure")
        async def generate_terraform(agent_auth: AgentAuth):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract agent_auth from kwargs
            agent_auth = kwargs.get('agent_auth')
            if not agent_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not validate_agent_capability(capability, agent_auth.get("capabilities", [])):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required capability: {capability}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_security_headers() -> Dict[str, str]:
    """Get standard security headers for responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }