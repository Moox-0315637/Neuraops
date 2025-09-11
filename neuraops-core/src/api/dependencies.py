"""
Dependency Injection Container for NeuraOps API

FastAPI dependencies for core services following CLAUDE.md: < 100 lines.
Provides singleton access to DevOpsEngine, Redis, and configuration.
"""
from functools import lru_cache
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import redis.asyncio as redis
import structlog

from ..core.engine import DevOpsEngine
from ..devops_commander.config import get_config, get_ollama_config
from .auth.jwt_handler import JWTHandler

logger = structlog.get_logger()
security = HTTPBearer()


def _validate_token_data(token_data) -> bool:
    """
    Validate decoded token data for both agents and users
    
    CLAUDE.md: Helper function < 10 lines for validation
    """
    if token_data is None:
        return False
    
    # Check for agent token (has agent_id)
    if hasattr(token_data, 'agent_id'):
        return True
    
    # Check for user token (has 'sub' field)
    if isinstance(token_data, dict) and 'sub' in token_data:
        return True
    
    return False


def _build_auth_response(token_data) -> dict:
    """
    Build authentication response dict for both agents and users
    
    CLAUDE.md: Helper function < 10 lines for response building
    """
    # For agent tokens
    if hasattr(token_data, 'agent_id'):
        return {
            "agent_id": token_data.agent_id,
            "capabilities": token_data.capabilities,
            "expires_at": token_data.exp
        }
    
    # For user tokens (dict with 'sub' field)
    if isinstance(token_data, dict) and 'sub' in token_data:
        return {
            "user_id": token_data.get("user_id"),
            "username": token_data.get("sub"),
            "role": token_data.get("role", "user"),
            "expires_at": token_data.get("exp")
        }
    
    # Fallback
    return {"authenticated": True}


def _handle_token_validation_error(error: Exception) -> HTTPException:
    """
    Handle token validation errors consistently
    
    CLAUDE.md: Helper function < 10 lines for error handling
    """
    logger.warning("Token validation failed", error=str(error))
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache()
def get_engine() -> DevOpsEngine:
    """
    Get singleton DevOpsEngine instance
    
    CLAUDE.md: Fail Fast - Check Ollama connectivity early
    """
    return DevOpsEngine()


@lru_cache()
def get_jwt_handler() -> JWTHandler:
    """Get singleton JWT handler"""
    config = get_config()
    return JWTHandler(secret_key=config.jwt_secret)


async def get_redis_client():
    """
    Get Redis client for distributed caching
    
    CLAUDE.md: Single Responsibility - Cache management
    """
    config = get_config()
    try:
        client = redis.from_url(
            config.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )
        # Test connection
        await client.ping()
        return client
    except Exception as e:
        logger.warning("Redis connection failed, using memory cache", error=str(e))
        # Return None to fallback to in-memory cache
        return None


def verify_agent_token(
    token: Annotated[str, Depends(security)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)]
) -> dict:
    """
    Verify JWT token for both agents and users (unified authentication)
    
    CLAUDE.md: Safety-First - Validate authentication before operations
    Supports both agent tokens and user tokens from web UI
    """
    try:
        # First, try to decode as an agent token using JWTHandler
        try:
            token_data = jwt_handler.verify_token(token.credentials)
            if _validate_token_data(token_data):
                return _build_auth_response(token_data)
        except Exception:
            # Agent token verification failed, try user token
            pass
        
        # If agent token fails, try to decode as user token using the same method as auth.py
        import jwt
        from ..devops_commander.config import get_config
        
        config = get_config()
        # Get JWT secret from config (must be set via environment variable)
        secret_key = getattr(config, 'jwt_secret', None)
        if not secret_key:
            raise HTTPException(
                status_code=500,
                detail="JWT secret not configured - set NEURAOPS_JWT_SECRET environment variable"
            )
        
        try:
            # Decode user JWT token
            payload = jwt.decode(token.credentials, secret_key, algorithms=["HS256"])
            if _validate_token_data(payload):
                return _build_auth_response(payload)
        except jwt.PyJWTError:
            pass
        
        # If both methods fail, raise authentication error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise _handle_token_validation_error(e)


# Type aliases for dependency injection
EngineInterface = Annotated[DevOpsEngine, Depends(get_engine)]
RedisInterface = Annotated[redis.Redis | None, Depends(get_redis_client)]
AgentAuth = Annotated[dict, Depends(verify_agent_token)]
JWTInterface = Annotated[JWTHandler, Depends(get_jwt_handler)]