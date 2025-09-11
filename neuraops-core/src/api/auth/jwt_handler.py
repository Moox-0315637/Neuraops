"""
JWT Authentication Handler for NeuraOps Agents

Secure token management following CLAUDE.md: < 150 lines, Safety-First validation.
Handles agent authentication with capabilities-based authorization.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from pydantic import BaseModel
import jwt
from jwt.exceptions import InvalidTokenError
import secrets
import structlog

logger = structlog.get_logger()


class TokenData(BaseModel):
    """JWT token payload data"""
    agent_id: str
    capabilities: List[str]
    exp: datetime


class JWTHandler:
    """
    JWT token management for distributed agents
    
    CLAUDE.md: Safety-First - Secure token validation
    CLAUDE.md: Single Responsibility - Only token management
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=24)
    
    def _get_current_timestamp(self) -> datetime:
        """
        Get current UTC timestamp in timezone-aware format
        
        CLAUDE.md: Helper function < 10 lines
        Fixes SonarQube S6903: Replace deprecated datetime.utcnow()
        """
        return datetime.now(timezone.utc)
    
    def _calculate_token_expiration(self, expires_delta: Optional[timedelta]) -> datetime:
        """
        Calculate token expiration time
        
        CLAUDE.md: Helper function < 10 lines for expiration logic
        """
        if expires_delta:
            return self._get_current_timestamp() + expires_delta
        return self._get_current_timestamp() + self.access_token_expire
    
    def _build_token_payload(self, agent_id: str, capabilities: List[str], expire: datetime) -> dict:
        """
        Build JWT token payload with standard claims
        
        CLAUDE.md: Helper function < 10 lines for payload construction
        """
        return {
            "sub": agent_id,
            "capabilities": capabilities,
            "exp": expire,
            "iat": self._get_current_timestamp(),
            "type": "agent"
        }
    
    def create_agent_token(
        self,
        agent_id: str,
        capabilities: List[str],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT token for agent with capabilities
        
        Args:
            agent_id: Unique identifier for agent
            capabilities: List of allowed operations (logs, infra, incidents, etc.)
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        expire = self._calculate_token_expiration(expires_delta)
        
        payload = self._build_token_payload(agent_id, capabilities, expire)
        
        try:
            encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info("Agent token created", 
                       agent_id=agent_id, 
                       capabilities=capabilities,
                       expires_at=expire.isoformat())
            return encoded_jwt
        except Exception as e:
            logger.error("Failed to create agent token", 
                        agent_id=agent_id, 
                        error=str(e))
            raise
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode JWT token
        
        CLAUDE.md: Safety-First - Validate token before operations
        """
        try:
            # Decode token payload
            payload = self._decode_token_payload(token)
            if not payload:
                return None
            
            # Validate required claims
            claims = self._validate_token_claims(payload)
            if not claims:
                return None
            
            agent_id, capabilities, exp_timestamp = claims
            
            # Check expiration
            is_expired, exp_datetime = self._check_token_expiration(exp_timestamp)
            if is_expired:
                logger.warning("Token expired", 
                              agent_id=agent_id,
                              expired_at=exp_datetime.isoformat())
                return None
            
            # Create and return token data
            return self._create_token_data(agent_id, capabilities, exp_datetime)
            
        except InvalidTokenError as e:
            logger.warning("Token validation failed", 
                          error=str(e),
                          token_preview=token[:20] + "..." if len(token) > 20 else token)
            return None
        except Exception as e:
            logger.error("Unexpected token verification error", error=str(e))
            return None
    
    def _decode_token_payload(self, token: str) -> Optional[dict]:
        """
        Decode JWT token and extract payload
        
        CLAUDE.md: Helper function < 10 lines for token decoding
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except InvalidTokenError:
            return None
    
    def _validate_token_claims(self, payload: dict) -> Optional[Tuple[str, List[str], float]]:
        """
        Validate required JWT claims
        
        CLAUDE.md: Helper function < 15 lines for claims validation
        """
        agent_id: str = payload.get("sub")
        capabilities: List[str] = payload.get("capabilities", [])
        exp_timestamp: float = payload.get("exp")
        
        if agent_id is None or exp_timestamp is None:
            logger.warning("Invalid token payload", payload=payload)
            return None
        
        return agent_id, capabilities, exp_timestamp
    
    def _check_token_expiration(self, exp_timestamp: float) -> Tuple[bool, datetime]:
        """
        Check if token is expired and return expiration datetime
        
        CLAUDE.md: Helper function < 10 lines for expiration check
        """
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        is_expired = self._get_current_timestamp() > exp_datetime
        return is_expired, exp_datetime
    
    def _create_token_data(self, agent_id: str, capabilities: List[str], exp_datetime: datetime) -> TokenData:
        """
        Create TokenData object from validated claims
        
        CLAUDE.md: Helper function < 10 lines for object creation
        """
        token_data = TokenData(
            agent_id=agent_id,
            capabilities=capabilities,
            exp=exp_datetime
        )
        
        logger.debug("Token verified successfully", 
                    agent_id=agent_id,
                    capabilities=capabilities)
        
        return token_data

    async def cache_token_in_redis(self, agent_id: str, token: str, redis_client, ttl: int = 3600) -> bool:
        """
        Cache JWT token in Redis for faster validation
        
        CLAUDE.md: Redis token caching for distributed agents
        """
        try:
            if redis_client:
                cache_key = f"jwt_token:{agent_id}"
                await redis_client.setex(cache_key, ttl, token)
                logger.debug("Token cached in Redis", agent_id=agent_id, ttl=ttl)
                return True
            return False
        except Exception as e:
            logger.warning("Failed to cache token in Redis", agent_id=agent_id, error=str(e))
            return False
    
    async def get_cached_token_from_redis(self, agent_id: str, redis_client) -> Optional[str]:
        """
        Retrieve cached JWT token from Redis
        
        CLAUDE.md: Redis token retrieval for validation
        """
        try:
            if redis_client:
                cache_key = f"jwt_token:{agent_id}"
                token = await redis_client.get(cache_key)
                if token:
                    logger.debug("Token retrieved from Redis cache", agent_id=agent_id)
                    return token
            return None
        except Exception as e:
            logger.warning("Failed to retrieve token from Redis", agent_id=agent_id, error=str(e))
            return None
    
    async def invalidate_cached_token(self, agent_id: str, redis_client) -> bool:
        """
        Invalidate cached JWT token in Redis
        
        CLAUDE.md: Token invalidation for security
        """
        try:
            if redis_client:
                cache_key = f"jwt_token:{agent_id}"
                await redis_client.delete(cache_key)
                logger.debug("Token invalidated in Redis", agent_id=agent_id)
                return True
            return False
        except Exception as e:
            logger.warning("Failed to invalidate token in Redis", agent_id=agent_id, error=str(e))
            return False
    
    def generate_api_key(self) -> str:
        """
        Generate secure API key for agent registration
        
        Returns:
            URL-safe random string (32 bytes)
        """
        api_key = secrets.token_urlsafe(32)
        logger.info("API key generated for agent registration")
        return api_key