"""
Agent Business Logic Service for NeuraOps API

Agent management and orchestration following CLAUDE.md: < 300 lines.
Coordinates agent registration, health monitoring, and task assignment.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import structlog

from ..auth.agent_auth import AgentAuthService
from ..auth.jwt_handler import JWTHandler
from ..models.agent import AgentInfo, AgentRegistrationRequest, AgentMetrics
from ...integration.redis_client import RedisClient
from ...integration.postgres_client import PostgreSQLClient
from ..websocket.manager import ConnectionManager

logger = structlog.get_logger()


class AgentService:
    """
    Business logic service for agent management
    
    CLAUDE.md: Single Responsibility - Agent operations only
    CLAUDE.md: AI-First - Intelligent agent orchestration
    """
    
    def __init__(
        self,
        jwt_handler: JWTHandler,
        redis_client: Optional[RedisClient] = None,
        postgres_client: Optional[PostgreSQLClient] = None,
        websocket_manager: Optional[ConnectionManager] = None
    ):
        self.auth_service = AgentAuthService(jwt_handler)
        self.redis_client = redis_client
        self.postgres_client = postgres_client
        self.websocket_manager = websocket_manager
        
        # In-memory fallback storage
        self.agents_cache: Dict[str, AgentInfo] = {}
        self.metrics_cache: Dict[str, List[AgentMetrics]] = {}
    
    def _get_current_timestamp(self) -> datetime:
        """
        Get current UTC timestamp in timezone-aware format
        
        CLAUDE.md: Helper function < 10 lines
        Fixes SonarQube S6903: Replace deprecated datetime.utcnow()
        """
        return datetime.now(timezone.utc)

    def _agent_exists_in_cache(self, agent_id: str) -> bool:
        """
        Check if agent exists in cache
        
        CLAUDE.md: Helper function < 10 lines for validation
        Fixes SonarQube S3516: Used for conditional validation
        """
        return agent_id in self.agents_cache

    def _validate_metrics_data(self, metrics: 'AgentMetrics') -> bool:
        """
        Validate metrics data integrity
        
        CLAUDE.md: Helper function < 15 lines for validation
        Fixes SonarQube S3516: Enables conditional returns
        """
        if not metrics:
            return False
        # Basic validation of required fields
        if not hasattr(metrics, 'cpu_usage') or not hasattr(metrics, 'memory_usage'):
            return False
        if not (0 <= metrics.cpu_usage <= 100) or not (0 <= metrics.memory_usage <= 100):
            return False
        return True

    def _store_in_cache(self, agent_id: str, metrics: 'AgentMetrics') -> bool:
        """
        Store metrics in memory cache with size management
        
        CLAUDE.md: Helper function < 15 lines for cache management
        Fixes SonarQube S3516: Returns success/failure based on operation
        """
        try:
            if agent_id not in self.metrics_cache:
                self.metrics_cache[agent_id] = []
            
            self.metrics_cache[agent_id].append(metrics)
            
            # Keep only recent metrics (last 100)
            if len(self.metrics_cache[agent_id]) > 100:
                self.metrics_cache[agent_id] = self.metrics_cache[agent_id][-100:]
            
            return True
        except Exception:
            return False
    
    async def register_agent(self, request: AgentRegistrationRequest) -> Optional[Dict[str, Any]]:
        """
        Register new agent with full persistence
        
        CLAUDE.md: Safety-First - Comprehensive validation
        """
        try:
            # Authenticate and validate
            token = self._authenticate_agent(request)
            if not token:
                return None
            
            agent_id = f"{request.hostname}_{request.agent_name}"
            
            # Create and cache agent info
            agent_info = self._create_agent_info(request, agent_id)
            self.agents_cache[agent_id] = agent_info
            
            # Persist data
            await self._persist_agent_data(agent_id, agent_info, request)
            
            logger.info("Agent registered successfully",
                       agent_id=agent_id,
                       capabilities=[cap.value for cap in request.capabilities])
            
            return {
                "agent_id": agent_id,
                "token": token,
                "agent_info": agent_info
            }
            
        except Exception as e:
            logger.error("Agent registration failed", error=str(e))
            return None
    
    def _authenticate_agent(self, request: AgentRegistrationRequest) -> Optional[str]:
        """
        Authenticate agent registration request
        
        CLAUDE.md: Helper function < 10 lines for authentication
        """
        token = self.auth_service.register_agent(request)
        if not token:
            logger.warning("Agent registration failed - invalid credentials",
                          agent_name=request.agent_name)
        return token
    
    def _create_agent_info(self, request: AgentRegistrationRequest, agent_id: str) -> AgentInfo:
        """
        Create AgentInfo object from registration request
        
        CLAUDE.md: Helper function < 10 lines for object creation
        """
        return AgentInfo(
            agent_id=agent_id,
            agent_name=request.agent_name,
            hostname=request.hostname,
            capabilities=request.capabilities,
            status="active",
            registered_at=self._get_current_timestamp()
        )
    
    async def _persist_agent_data(self, agent_id: str, agent_info: AgentInfo, request: AgentRegistrationRequest):
        """
        Handle agent data persistence in Redis and PostgreSQL
        
        CLAUDE.md: Helper function < 20 lines for persistence
        """
        # Store in Redis for fast access
        if self.redis_client:
            await self.redis_client.set_agent_data(
                agent_id, 
                agent_info.dict(),
                ttl=86400  # 24 hours
            )
        
        # Store in PostgreSQL for persistence
        if self.postgres_client:
            await self.postgres_client.register_agent({
                "agent_id": agent_id,
                "agent_name": request.agent_name,
                "hostname": request.hostname,
                "capabilities": [cap.value for cap in request.capabilities],
                "metadata": request.metadata
            })
    
    async def get_agent_list(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Get paginated list of registered agents
        
        CLAUDE.md: Simple pagination with fallback
        """
        try:
            # Get agents from database or cache
            agents, total_count = await self._get_paginated_agents(page, page_size)
            
            # Enrich with real-time status
            agents = self._enrich_with_realtime_status(agents)
            
            active_count = len([a for a in agents if a.status in ["active", "connected"]])
            
            return {
                "agents": agents,
                "total_count": total_count,
                "active_count": active_count,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error("Failed to get agent list", error=str(e))
            return {
                "agents": [],
                "total_count": 0,
                "active_count": 0,
                "page": page,
                "page_size": page_size
            }
    
    async def _get_paginated_agents(self, page: int, page_size: int) -> Tuple[List[AgentInfo], int]:
        """
        Get paginated agents from database or cache
        
        CLAUDE.md: Helper function < 30 lines for data retrieval
        """
        # Try PostgreSQL first
        if self.postgres_client:
            return await self._get_agents_from_db(page_size, (page - 1) * page_size)
        
        # Fallback to cache
        elif self.agents_cache:
            return self._get_agents_from_cache(page, page_size)
        
        return [], 0
    
    async def _get_agents_from_db(self, page_size: int, offset: int) -> Tuple[List[AgentInfo], int]:
        """
        Get agents from PostgreSQL with pagination
        
        CLAUDE.md: Helper function < 20 lines for DB access
        """
        db_agents = await self.postgres_client.get_agent_list(page_size, offset)
        
        agents = [
            AgentInfo(
                agent_id=agent["agent_id"],
                agent_name=agent["agent_name"],
                hostname=agent["hostname"],
                capabilities=agent["capabilities"],
                status=agent["status"],
                registered_at=agent["registered_at"],
                last_seen=agent.get("last_seen"),
                metadata=agent.get("metadata", {})
            )
            for agent in db_agents
        ]
        
        return agents, len(db_agents)  # In production, use separate count query
    
    def _get_agents_from_cache(self, page: int, page_size: int) -> Tuple[List[AgentInfo], int]:
        """
        Get agents from memory cache with pagination
        
        CLAUDE.md: Helper function < 10 lines for cache access
        """
        all_agents = list(self.agents_cache.values())
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        agents = all_agents[start_idx:end_idx]
        return agents, len(all_agents)
    
    def _enrich_with_realtime_status(self, agents: List[AgentInfo]) -> List[AgentInfo]:
        """
        Enrich agents with real-time WebSocket connection status
        
        CLAUDE.md: Helper function < 20 lines for status enrichment
        Fixes SonarQube S3516: Conditional return based on WebSocket availability
        """
        # Early return if no websocket manager
        if not self.websocket_manager:
            return agents  # Unmodified agents
        
        # Check if there are active connections
        connected_agents = set(self.websocket_manager.active_connections.keys())
        if not connected_agents:
            return agents  # No connections, return unmodified
        
        # Enrich agents with connection status
        current_time = self._get_current_timestamp()
        modified_agents = []
        
        for agent in agents:
            # Create a copy to avoid modifying original
            enriched_agent = agent.copy()
            if agent.agent_id in connected_agents:
                enriched_agent.status = "connected"
                enriched_agent.last_seen = current_time
            modified_agents.append(enriched_agent)
        
        return modified_agents  # Always return modified list
    
    async def update_agent_heartbeat(self, agent_id: str, heartbeat_data: Dict[str, Any]) -> bool:
        """
        Update agent heartbeat and status with validation
        
        CLAUDE.md: Simple heartbeat processing with proper validation
        Fixes SonarQube S3516: Conditional returns based on validation and operation success
        """
        # Input validation
        if not agent_id or not heartbeat_data:
            logger.warning("Invalid heartbeat data", agent_id=agent_id)
            return False
        
        # Check if agent exists in cache
        if not self._agent_exists_in_cache(agent_id):
            logger.warning("Agent not found for heartbeat", agent_id=agent_id)
            return False
        
        try:
            # Update cache
            self._update_cache_heartbeat(agent_id, heartbeat_data)
            
            # Persist in Redis
            await self._persist_heartbeat_data(agent_id, heartbeat_data)
            
            logger.debug("Agent heartbeat updated", agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update agent heartbeat", 
                        agent_id=agent_id, error=str(e))
            return False
    
    def _update_cache_heartbeat(self, agent_id: str, heartbeat_data: Dict[str, Any]):
        """
        Update agent heartbeat in memory cache
        
        CLAUDE.md: Helper function < 10 lines for cache update
        """
        if agent_id in self.agents_cache:
            self.agents_cache[agent_id].last_seen = self._get_current_timestamp()
            self.agents_cache[agent_id].status = heartbeat_data.get("status", "active")
    
    async def _persist_heartbeat_data(self, agent_id: str, heartbeat_data: Dict[str, Any]):
        """
        Persist heartbeat data in Redis
        
        CLAUDE.md: Helper function < 15 lines for persistence
        """
        if self.redis_client:
            await self.redis_client.set_agent_data(
                agent_id,
                {
                    "last_heartbeat": self._get_current_timestamp().isoformat(),
                    "status": heartbeat_data.get("status", "active"),
                    "system_info": heartbeat_data.get("system_info", {})
                },
                ttl=300  # 5 minutes
            )
    
    async def store_agent_metrics(self, agent_id: str, metrics: AgentMetrics) -> bool:
        """
        Store agent performance metrics with comprehensive validation
        
        CLAUDE.md: Simple metrics storage with Redis and validation
        Fixes SonarQube S3516: Conditional returns based on validation and operation success
        """
        # Validate input metrics
        if not self._validate_metrics_data(metrics):
            logger.warning("Invalid metrics data", agent_id=agent_id)
            return False
        
        # Check if agent is authorized to submit metrics
        if not self._agent_exists_in_cache(agent_id):
            logger.warning("Unknown agent submitting metrics", agent_id=agent_id)
            return False
        
        try:
            # Store in Redis with success tracking
            redis_success = True
            if self.redis_client:
                try:
                    await self.redis_client.store_metrics(agent_id, metrics.dict())
                except Exception as e:
                    logger.warning("Redis metrics storage failed", agent_id=agent_id, error=str(e))
                    redis_success = False
            
            # Store in memory cache
            cache_success = self._store_in_cache(agent_id, metrics)
            
            # Return success only if cache succeeded (Redis is optional)
            if cache_success:
                logger.debug("Agent metrics stored",
                            agent_id=agent_id,
                            cpu=metrics.cpu_usage,
                            memory=metrics.memory_usage,
                            redis_success=redis_success)
                return True
            else:
                logger.warning("Cache storage failed", agent_id=agent_id)
                return False
            
        except Exception as e:
            logger.error("Failed to store agent metrics", 
                        agent_id=agent_id, error=str(e))
            return False
    
    async def get_agent_metrics(self, agent_id: str, minutes: int = 60) -> List[AgentMetrics]:
        """
        Get recent agent metrics
        
        CLAUDE.md: Simple metrics retrieval
        """
        try:
            # Try Redis first
            if self.redis_client:
                metrics_data = await self.redis_client.get_recent_metrics(agent_id, minutes)
                return [AgentMetrics(**data) for data in metrics_data if data]
            
            # Fallback to memory cache
            elif agent_id in self.metrics_cache:
                cutoff = self._get_current_timestamp() - timedelta(minutes=minutes)
                recent_metrics = [
                    m for m in self.metrics_cache[agent_id]
                    if m.timestamp >= cutoff
                ]
                return recent_metrics
            
            return []
            
        except Exception as e:
            logger.error("Failed to get agent metrics", 
                        agent_id=agent_id, error=str(e))
            return []
    
    def get_connected_agents(self) -> List[str]:
        """
        Get list of currently connected agents
        
        CLAUDE.md: Real-time connection status
        """
        if self.websocket_manager:
            return list(self.websocket_manager.active_connections.keys())
        return []
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information from cache"""
        return self.agents_cache.get(agent_id)