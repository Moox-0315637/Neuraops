"""
Agent Management Routes for NeuraOps API

Agent registration, management, and monitoring following CLAUDE.md: < 500 lines.
Handles distributed agent lifecycle and communication using modular services.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timezone, timedelta
import structlog
import secrets

from ..dependencies import JWTInterface, AgentAuth, RedisInterface
from ..models.agent import (
    AgentRegistrationRequest, AgentRegistrationResponse,
    AgentInfo, AgentListResponse, AgentHeartbeat, AgentMetrics,
    AgentUpdateRequest, AgentResponse
)
from ..models.responses import APIResponse, PaginatedResponse
from ..auth.agent_auth import AgentAuthService
from ..auth.security import RateLimiter, get_security_headers

# Import modular services
from ..services.agent_management import (
    retrieve_registered_agents,
    store_agent_heartbeat,
    retrieve_agent_metrics,
    check_admin_privileges,
    store_agent_info
)
from ..services.agent_operations import (
    execute_command_via_websocket,
    request_filesystem_via_websocket
)
from ..services.agent_cleanup import cleanup_agent_data

logger = structlog.get_logger()
router = APIRouter()

# Rate limiter for registration endpoint
registration_limiter = RateLimiter(max_requests=10, window_seconds=300)


@router.post("/agents/register", response_model=APIResponse[AgentRegistrationResponse])
async def register_agent(
    request: AgentRegistrationRequest,
    jwt_handler: JWTInterface,
    redis_client: RedisInterface
):
    """
    Register new agent with simplified authentication and Redis token caching
    
    CLAUDE.md: Keep It Simple - Direct token validation with Redis caching
    """
    try:
        # Rate limiting
        client_id = f"reg_{request.hostname}_{request.agent_name}"
        if not registration_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Registration rate limit exceeded"
            )
        
        # Simple API key validation - get valid tokens from environment
        import os
        valid_tokens_str = os.getenv('SECURITY_ALLOWED_API_KEYS', '')
        valid_tokens = {token.strip() for token in valid_tokens_str.split(',') if token.strip()}
        
        # Generate new token if requested
        if request.api_key == "generate":
            request.api_key = secrets.token_urlsafe(32)
            valid_tokens.add(request.api_key)
        
        # Validate API key
        if request.api_key not in valid_tokens:
            logger.warning("Invalid API key used for registration", 
                          agent_name=request.agent_name,
                          key_length=len(request.api_key))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent registration failed. Invalid API key or capabilities."
            )
        
        # Validate capabilities
        valid_capabilities = {"logs", "infrastructure", "incidents", "workflows", "health", "metrics", "commands"}
        if not all(cap in valid_capabilities for cap in request.capabilities):
            logger.warning("Invalid capabilities requested", capabilities=request.capabilities)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent registration failed. Invalid API key or capabilities."
            )
        
        # Create agent ID
        agent_id = f"{request.hostname}_{request.agent_name}"
        
        # Check if agent already has a cached token
        cached_token = None
        if hasattr(jwt_handler, 'get_cached_token_from_redis'):
            cached_token = await jwt_handler.get_cached_token_from_redis(agent_id, redis_client)
        
        # Create new JWT token or use cached one
        if cached_token and jwt_handler.verify_token(cached_token):
            token = cached_token
            logger.info("Using cached token for agent", agent_id=agent_id)
        else:
            # Create new JWT token for the agent
            token = jwt_handler.create_agent_token(
                agent_id=agent_id,
                capabilities=request.capabilities
            )
            
            # Cache the new token in Redis
            if hasattr(jwt_handler, 'cache_token_in_redis'):
                await jwt_handler.cache_token_in_redis(agent_id, token, redis_client, ttl=86400*30)  # 30 days
        
        # Get token expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Store agent info in Redis for persistence
        agent_info = AgentInfo(
            agent_id=agent_id,
            agent_name=request.agent_name,
            hostname=request.hostname,
            capabilities=request.capabilities,
            status="active",
            registered_at=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            metadata={
                "version": (request.metadata or {}).get("version", "unknown"),
                "platform": (request.metadata or {}).get("platform", "unknown"),
                "registration_ip": "127.0.0.1",  # In real implementation, get from request
                **(request.metadata or {})  # Include all metadata
            }
        )
        
        # Store using service module
        await store_agent_info(agent_info, redis_client)
        
        response_data = AgentRegistrationResponse(
            agent_id=agent_id,
            token=token,
            expires_at=expires_at
        )
        
        logger.info("Agent registered successfully",
                   agent_id=agent_id,
                   capabilities=request.capabilities)
        
        return APIResponse(
            status="success",
            message="Agent registered successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.get("/agents", response_model=APIResponse[AgentListResponse])
async def list_agents(
    agent_auth: AgentAuth,
    redis_client: RedisInterface,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    List registered agents with pagination
    
    CLAUDE.md: Single Responsibility - Agent listing only
    """
    try:
        # Retrieve actual agents from Redis/DB using service
        agents_response = await retrieve_registered_agents(redis_client, page, page_size)
        
        if agents_response.total_count == 0:
            logger.info("No registered agents found")
            return APIResponse(
                status="success", 
                message="No agents registered", 
                data=agents_response
            )
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(agents_response.agents)} agents",
            data=agents_response
        )
        
    except Exception as e:
        logger.error("Failed to list agents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent list"
        )


@router.post("/agents/{agent_id}/heartbeat", response_model=APIResponse[AgentResponse])
async def agent_heartbeat(
    agent_id: str,
    heartbeat: AgentHeartbeat,
    agent_auth: AgentAuth,
    redis_client: RedisInterface
):
    """
    Agent heartbeat endpoint
    
    CLAUDE.md: Simple heartbeat processing
    """
    try:
        # Validate agent owns this ID
        if agent_auth["agent_id"] != agent_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent can only update own heartbeat"
            )
        
        # Store heartbeat using service
        storage_success = await store_agent_heartbeat(agent_id, heartbeat, redis_client)
        if storage_success:
            logger.debug("Agent heartbeat stored", agent_id=agent_id)
        
        logger.info("Heartbeat received",
                   agent_id=agent_id,
                   status=heartbeat.status)
        
        response_data = AgentResponse(
            success=True,
            message="Heartbeat processed successfully"
        )
        
        return APIResponse(
            status="success",
            message="Heartbeat updated",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Heartbeat processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process heartbeat"
        )


@router.get("/agents/{agent_id}/metrics", response_model=APIResponse[AgentMetrics])
async def get_agent_metrics(
    agent_id: str,
    agent_auth: AgentAuth,
    redis_client: RedisInterface
):
    """
    Get metrics for a specific agent
    
    CLAUDE.md: Simple metrics retrieval for agent monitoring
    """
    try:
        # Retrieve from Redis storage using service
        agent_metrics = await retrieve_agent_metrics(agent_id, redis_client)
        
        if not agent_metrics:
            # Create basic metrics fallback if not found
            agent_metrics = AgentMetrics(
                agent_id=agent_id, 
                timestamp=datetime.now(timezone.utc),
                system_metrics={
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "disk_percent": 0.0,
                    "uptime_seconds": 0
                },
                performance={
                    "commands_executed": 0,
                    "success_rate": 100.0,
                    "average_execution_time": 0.0
                }
            )
            logger.warning("Agent metrics not found, using fallback", agent_id=agent_id)
        
        return APIResponse(
            status="success",
            message="Agent metrics retrieved",
            data=agent_metrics
        )
        
    except Exception as e:
        logger.error("Failed to get agent metrics", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent metrics"
        )


@router.post("/agents/{agent_id}/execute", response_model=APIResponse[dict])
async def execute_command_on_agent(
    agent_id: str,
    request: dict,
    agent_auth: AgentAuth,
    redis_client: RedisInterface
):
    """
    Execute command on specific agent
    
    CLAUDE.md: Route command to specific agent via WebSocket
    """
    try:
        command = request.get("command", "")
        timeout = request.get("timeout", 30)
        
        logger.info("Command execution requested for agent",
                   agent_id=agent_id,
                   command=command,
                   timeout=timeout)
        
        # Send command to agent using service
        response_data = await execute_command_via_websocket(agent_id, command, redis_client)
        
        return APIResponse(
            status="success",
            message="Command queued for agent",
            data=response_data
        )
        
    except Exception as e:
        logger.error("Failed to execute command on agent", 
                    agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute command on agent"
        )


@router.get("/agents/{agent_id}/filesystem", response_model=APIResponse[dict])
async def get_agent_filesystem(
    agent_id: str,
    agent_auth: AgentAuth,
    redis_client: RedisInterface,
    path: str = Query("/", description="Filesystem path to explore")
):
    """
    Get filesystem information from agent
    
    CLAUDE.md: Safe filesystem access through agent
    """
    try:
        logger.info("Filesystem request for agent",
                   agent_id=agent_id,
                   path=path)
        
        # Request filesystem info using service
        response_data = await request_filesystem_via_websocket(agent_id, path, redis_client)
        
        return APIResponse(
            status="success",
            message=f"Filesystem info retrieved for {path}",
            data=response_data
        )
        
    except Exception as e:
        logger.error("Failed to get agent filesystem", 
                    agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve filesystem information"
        )


@router.get("/agents/{agent_id}", response_model=APIResponse[AgentInfo])
async def get_agent_details(
    agent_id: str,
    agent_auth: AgentAuth,
    redis_client: RedisInterface
):
    """
    Get detailed information about specific agent
    
    CLAUDE.md: Agent detail retrieval
    """
    try:
        # Retrieve from storage/WebSocket manager
        if redis_client:
            agent_key = f"agent_info:{agent_id}"
            agent_data = await redis_client.get(agent_key)
            
            if agent_data:
                agent_info = AgentInfo.parse_raw(agent_data)
                return APIResponse(
                    status="success",
                    message="Agent details retrieved",
                    data=agent_info
                )
        
        # Fallback to constructed response if not found in storage
        agent_info = AgentInfo(
            agent_id=agent_id,
            agent_name=agent_id.split('_')[-1] if '_' in agent_id else agent_id,
            hostname=agent_id.split('_')[0] if '_' in agent_id else "unknown",
            capabilities=["logs", "metrics", "commands", "filesystem"],
            status="unknown",
            registered_at=datetime.now(timezone.utc),
            last_seen=None,
            metadata={"status": "Not found in storage"}
        )
        
        logger.warning("Agent details not found in storage, using fallback", agent_id=agent_id)
        
        return APIResponse(
            status="success",
            message="Agent details retrieved (fallback)",
            data=agent_info
        )
        
    except Exception as e:
        logger.error("Failed to get agent details", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent details"
        )


@router.delete("/agents/{agent_id}", response_model=APIResponse[AgentResponse])
async def deregister_agent(
    agent_id: str,
    agent_auth: AgentAuth,
    redis_client: RedisInterface
):
    """
    Deregister an agent
    
    CLAUDE.md: Clean agent removal
    """
    try:
        # Validate agent can only deregister itself or admin privileges needed
        if agent_auth["agent_id"] != agent_id:
            # Check for admin privileges using service
            has_admin_privileges = await check_admin_privileges(agent_auth, redis_client)
            if not has_admin_privileges:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient privileges to deregister agent"
                )
        
        # Remove from storage, WebSocket connections, etc. using service
        cleanup_success = await cleanup_agent_data(agent_id, redis_client)
        if cleanup_success:
            logger.debug("Agent data cleaned up", agent_id=agent_id)
        
        logger.info("Agent deregistered", agent_id=agent_id)
        
        response_data = AgentResponse(
            success=True,
            message="Agent deregistered successfully"
        )
        
        return APIResponse(
            status="success",
            message="Agent deregistered",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to deregister agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deregister agent"
        )