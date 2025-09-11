"""
Agent Management Service for NeuraOps API

Helper functions for agent lifecycle management following CLAUDE.md: < 500 lines.
Contains all agent-related business logic and Redis operations.
"""
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone
import structlog
import json
import asyncio

from ..dependencies import RedisInterface, AgentAuth
from ..models.agent import (
    AgentInfo, AgentListResponse, AgentHeartbeat, AgentMetrics
)

logger = structlog.get_logger()


async def retrieve_registered_agents(redis_client: RedisInterface, page: int, page_size: int) -> AgentListResponse:
    """Retrieve registered agents from Redis following CLAUDE.md < 15 lines"""
    try:
        if not redis_client:
            return AgentListResponse(agents=[], total_count=0, active_count=0)
        
        agent_keys = await redis_client.keys("agent_info:*")
        agents = []
        
        for key in agent_keys:
            agent_data = await redis_client.get(key)
            if agent_data:
                agent_info = _parse_agent_data(agent_data)
                if agent_info:
                    agents.append(agent_info)
        
        paginated_agents = _apply_pagination(agents, page, page_size)
        active_count = len([a for a in agents if a.status == "active"])
        
        return AgentListResponse(
            agents=paginated_agents,
            total_count=len(agents),
            active_count=active_count
        )
    except Exception as e:
        logger.warning("Failed to retrieve agents from storage", error=str(e))
        return AgentListResponse(agents=[], total_count=0, active_count=0)

def _parse_agent_data(agent_data) -> Optional[AgentInfo]:
    """Parse agent data from Redis following CLAUDE.md < 10 lines"""
    try:
        if isinstance(agent_data, str):
            agent_dict = json.loads(agent_data)
        else:
            agent_dict = agent_data
        
        agent_dict = _convert_agent_capabilities(agent_dict)
        agent_dict = _convert_agent_status(agent_dict)
        return AgentInfo.model_validate(agent_dict)
    except Exception:
        return None


def _convert_agent_capabilities(agent_dict: dict) -> dict:
    """Convert string capabilities to enum values following CLAUDE.md < 10 lines"""
    if 'capabilities' in agent_dict and isinstance(agent_dict['capabilities'], list):
        from ..models.agent import AgentCapability
        agent_dict['capabilities'] = [
            AgentCapability(cap) if isinstance(cap, str) else cap 
            for cap in agent_dict['capabilities']
        ]
    return agent_dict


def _convert_agent_status(agent_dict: dict) -> dict:
    """Convert string status to enum value following CLAUDE.md < 10 lines"""
    if 'status' in agent_dict and isinstance(agent_dict['status'], str):
        from ..models.agent import AgentStatus
        agent_dict['status'] = AgentStatus(agent_dict['status'])
    return agent_dict


def _apply_pagination(agents: List[AgentInfo], page: int, page_size: int) -> List[AgentInfo]:
    """Apply pagination to agents list following CLAUDE.md < 5 lines"""
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return agents[start_idx:end_idx]


async def store_agent_heartbeat(agent_id: str, heartbeat: AgentHeartbeat, redis_client: RedisInterface) -> bool:
    """Store agent heartbeat following CLAUDE.md < 10 lines"""
    try:
        heartbeat_key = f"agent_heartbeat:{agent_id}"
        if redis_client:
            heartbeat_data = {
                "agent_id": agent_id,
                "status": heartbeat.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_info": heartbeat.system_info
            }
            await redis_client.setex(heartbeat_key, 300, json.dumps(heartbeat_data))  # 5min TTL
            logger.debug("Agent heartbeat stored", agent_id=agent_id)
            return True
        return False
    except Exception as e:
        logger.error("Failed to store heartbeat", agent_id=agent_id, error=str(e))
        return False


async def retrieve_agent_metrics(agent_id: str, redis_client: RedisInterface) -> Optional[AgentMetrics]:
    """Retrieve agent metrics following CLAUDE.md < 10 lines"""
    try:
        metrics_key = f"agent_metrics:{agent_id}"
        if redis_client:
            metrics_data = await redis_client.get(metrics_key)
            if metrics_data:
                if isinstance(metrics_data, str):
                    return AgentMetrics.model_validate_json(metrics_data)
                else:
                    return AgentMetrics.model_validate(metrics_data)
        
        # Fallback to heartbeat data
        return await _create_metrics_from_heartbeat(agent_id, redis_client)
    except Exception as e:
        logger.warning("Failed to retrieve agent metrics", agent_id=agent_id, error=str(e))
        return None

async def _create_metrics_from_heartbeat(agent_id: str, redis_client: RedisInterface) -> Optional[AgentMetrics]:
    """Create metrics from heartbeat data following CLAUDE.md < 15 lines"""
    try:
        heartbeat_key = f"agent_heartbeat:{agent_id}"
        heartbeat_data = await redis_client.get(heartbeat_key)
        if heartbeat_data:
            hb_info = json.loads(heartbeat_data)
            system_info = hb_info.get("system_info", {})
            return AgentMetrics(
                agent_id=agent_id, 
                timestamp=datetime.now(timezone.utc),
                cpu_usage=system_info.get("cpu_percent", 0.0),
                memory_usage=system_info.get("memory_percent", 0.0),
                disk_usage=system_info.get("disk_percent", 0.0),
                active_tasks=system_info.get("active_tasks", 0),
                completed_tasks=system_info.get("completed_tasks", 0),
                error_count=system_info.get("error_count", 0),
                uptime_seconds=system_info.get("uptime_seconds", 0)
            )
        return None
    except Exception:
        return None


async def check_admin_privileges(agent_auth: AgentAuth, redis_client: RedisInterface) -> bool:
    """Check admin privileges for agent following CLAUDE.md < 10 lines"""
    try:
        agent_id = agent_auth["agent_id"]
        capabilities = agent_auth.get("capabilities", [])
        
        # Check for admin capability
        if "admin" in capabilities:
            return True
            
        # Check admin list in Redis
        if redis_client:
            admin_key = f"admin_agents:{agent_id}"
            is_admin = await redis_client.get(admin_key)
            if is_admin:
                return True
        
        return False
    except Exception as e:
        logger.error("Failed to check admin privileges", agent_id=agent_auth.get("agent_id"), error=str(e))
        return False


async def store_agent_info(agent_info: AgentInfo, redis_client: RedisInterface) -> bool:
    """Store agent info in Redis following CLAUDE.md < 10 lines"""
    try:
        if redis_client:
            agent_key = f"agent_info:{agent_info.agent_id}"
            await redis_client.setex(agent_key, 86400 * 30, agent_info.json())  # 30 days TTL
            logger.debug("Agent info stored in Redis", agent_id=agent_info.agent_id)
            return True
        return False
    except Exception as e:
        logger.error("Failed to store agent info", agent_id=agent_info.agent_id, error=str(e))
        return False