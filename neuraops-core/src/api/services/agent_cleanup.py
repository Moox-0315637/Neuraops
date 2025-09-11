"""
Agent Cleanup Service for NeuraOps API

Agent cleanup and data removal operations following CLAUDE.md: < 500 lines.
Handles complete cleanup of agent data, connections, and requests.
"""
import structlog
import json

from ..dependencies import RedisInterface

logger = structlog.get_logger()


async def cleanup_agent_websocket_connections(agent_id: str, redis_client: RedisInterface) -> bool:
    """Cleanup agent WebSocket connections following CLAUDE.md < 10 lines"""
    try:
        if not redis_client:
            return True
        
        # Remove WebSocket session tracking
        ws_session_key = f"ws_session:{agent_id}"
        await redis_client.delete(ws_session_key)
        
        # Remove active connection tracking
        connection_key = f"active_connection:{agent_id}"
        await redis_client.delete(connection_key)
        
        logger.debug("WebSocket connections cleaned up", agent_id=agent_id)
        return True
    except Exception as e:
        logger.error("Failed to cleanup WebSocket connections", agent_id=agent_id, error=str(e))
        return False


async def cleanup_agent_requests(agent_id: str, redis_client: RedisInterface) -> bool:
    """Cleanup agent requests and pending operations following CLAUDE.md < 10 lines"""
    try:
        if not redis_client:
            return True
        
        # Get all keys related to this agent's requests
        command_keys = await redis_client.keys("agent_command_request:*")
        fs_keys = await redis_client.keys("fs_request:*")
        
        # Filter and cleanup keys for this specific agent
        cleanup_keys = []
        for key in command_keys + fs_keys:
            try:
                key_data = await redis_client.get(key)
                if key_data and agent_id in json.loads(key_data).get("agent_id", ""):
                    cleanup_keys.append(key)
            except Exception:
                continue
        
        # Delete all agent-related request keys
        for key in cleanup_keys:
            await redis_client.delete(key)
        
        logger.debug("Agent requests cleaned up", agent_id=agent_id, keys_cleaned=len(cleanup_keys))
        return True
    except Exception as e:
        logger.error("Failed to cleanup agent requests", agent_id=agent_id, error=str(e))
        return False


async def cleanup_agent_data(agent_id: str, redis_client: RedisInterface) -> bool:
    """Complete agent cleanup following CLAUDE.md < 15 lines"""
    try:
        cleanup_success = True
        
        if redis_client:
            # Remove agent info
            agent_keys = [
                f"agent_info:{agent_id}",
                f"agent_heartbeat:{agent_id}", 
                f"agent_metrics:{agent_id}"
            ]
            
            for key in agent_keys:
                try:
                    await redis_client.delete(key)
                except Exception:
                    cleanup_success = False
            
            # Remove agent from admin list if present
            admin_key = f"admin_agents:{agent_id}"
            await redis_client.delete(admin_key)
        
        # Cleanup agent WebSocket connections and sessions
        websocket_cleanup_success = await cleanup_agent_websocket_connections(agent_id, redis_client)
        if not websocket_cleanup_success:
            cleanup_success = False
        
        # Cleanup agent command requests and filesystem requests
        await cleanup_agent_requests(agent_id, redis_client)
        
        logger.debug("Agent data cleanup completed", agent_id=agent_id, success=cleanup_success)
        return cleanup_success
    except Exception as e:
        logger.error("Failed to cleanup agent data", agent_id=agent_id, error=str(e))
        return False