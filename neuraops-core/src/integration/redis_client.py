"""
Redis Integration Client for NeuraOps API

Distributed caching and session management following CLAUDE.md: < 150 lines.
Provides Redis operations for agent data, metrics, and cache.
"""
from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timedelta, timezone
import redis.asyncio as redis
import structlog

from ..devops_commander.config import get_config

logger = structlog.get_logger()


class RedisClient:
    """
    Redis client wrapper for NeuraOps operations
    
    CLAUDE.md: Single Responsibility - Redis operations only
    CLAUDE.md: Fail Fast - Handle Redis connection failures
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        config = get_config()
        self.redis_url = redis_url or getattr(config, 'redis_url', 'redis://localhost:6379')
        self.client: Optional[redis.Redis] = None
        self.connected = False
    
    def _get_current_utc_timestamp(self) -> int:
        """
        Get current UTC timestamp in timezone-aware format
        
        CLAUDE.md: Helper function < 10 lines
        Fixes SonarQube S6903: Replace deprecated datetime.utcnow()
        """
        return int(datetime.now(timezone.utc).timestamp())

    def _calculate_cutoff_timestamp(self, minutes: int) -> int:
        """
        Calculate cutoff timestamp for time range queries
        
        CLAUDE.md: Helper function < 10 lines
        Fixes SonarQube S6903: Replace deprecated datetime.utcnow()
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return int(cutoff_time.timestamp())
    
    async def connect(self) -> bool:
        """
        Establish Redis connection
        
        CLAUDE.md: Fail Fast - Early connection validation
        """
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.client.ping()
            self.connected = True
            
            logger.info("Redis connection established", url=self.redis_url)
            return True
            
        except Exception as e:
            logger.error("Failed to connect to Redis", 
                        url=self.redis_url, error=str(e))
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Redis connection closed")
    
    async def set_agent_data(self, agent_id: str, data: Dict[str, Any], ttl: int = 3600):
        """
        Store agent data with TTL using agent_info: prefix for UI compatibility
        
        CLAUDE.md: Simple data storage with expiration
        """
        if not self.connected or not self.client:
            return False
        
        try:
            # Use agent_info: prefix to match retrieve_registered_agents() expectations
            key = f"agent_info:{agent_id}"
            await self.client.setex(key, ttl, json.dumps(data))
            logger.debug("Agent data stored", agent_id=agent_id, ttl=ttl, key=key)
            return True
            
        except Exception as e:
            logger.error("Failed to store agent data", 
                        agent_id=agent_id, error=str(e))
            return False
    
    async def get_agent_data(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent data from cache"""
        if not self.connected or not self.client:
            return None
        
        try:
            key = f"agent:{agent_id}:data"
            data = await self.client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error("Failed to retrieve agent data", 
                        agent_id=agent_id, error=str(e))
            return None
    
    async def store_command_execution(self, command_id: str, execution_data: Dict[str, Any]):
        """
        Store command execution details
        
        CLAUDE.md: Safety-First - Persist command history
        """
        if not self.connected or not self.client:
            return False
        
        try:
            key = f"command:{command_id}"
            await self.client.setex(key, 86400, json.dumps(execution_data))  # 24h TTL
            
            # Add to command history list
            history_key = "command:history"
            await self.client.lpush(history_key, command_id)
            await self.client.ltrim(history_key, 0, 999)  # Keep last 1000 commands
            
            logger.debug("Command execution stored", command_id=command_id)
            return True
            
        except Exception as e:
            logger.error("Failed to store command execution", 
                        command_id=command_id, error=str(e))
            return False
    
    async def get_command_execution(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve command execution details"""
        if not self.connected or not self.client:
            return None
        
        try:
            key = f"command:{command_id}"
            data = await self.client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error("Failed to retrieve command execution", 
                        command_id=command_id, error=str(e))
            return None
    
    async def store_metrics(self, agent_id: str, metrics: Dict[str, Any]):
        """
        Store agent metrics with timestamp
        
        CLAUDE.md: Simple metrics storage
        """
        if not self.connected or not self.client:
            return False
        
        try:
            timestamp = self._get_current_utc_timestamp()
            key = f"metrics:{agent_id}:{timestamp}"
            
            # Store individual metric
            await self.client.setex(key, 3600, json.dumps(metrics))  # 1h TTL
            
            # Add to metrics timeline (sorted set)
            timeline_key = f"metrics_timeline:{agent_id}"
            await self.client.zadd(timeline_key, {key: timestamp})
            
            # Keep only recent metrics (last hour)
            cutoff = timestamp - 3600
            await self.client.zremrangebyscore(timeline_key, 0, cutoff)
            
            logger.debug("Metrics stored", agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error("Failed to store metrics", 
                        agent_id=agent_id, error=str(e))
            return False
    
    async def get_recent_metrics(self, agent_id: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent metrics for agent"""
        if not self.connected or not self.client:
            return []
        
        try:
            timeline_key = f"metrics_timeline:{agent_id}"
            cutoff = self._calculate_cutoff_timestamp(minutes)
            
            # Get recent metric keys
            metric_keys = await self.client.zrangebyscore(timeline_key, cutoff, "+inf")
            
            if not metric_keys:
                return []
            
            # Retrieve metric data
            metrics = []
            for key in metric_keys:
                data = await self.client.get(key)
                if data:
                    metrics.append(json.loads(data))
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to retrieve recent metrics", 
                        agent_id=agent_id, error=str(e))
            return []