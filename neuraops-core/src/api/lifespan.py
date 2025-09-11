"""
FastAPI Application Lifespan Management

Handles startup and shutdown procedures for NeuraOps Core API.
Follows CLAUDE.md: < 100 lines, Fail Fast principle.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import structlog

from ..devops_commander.config import get_config
from ..core.engine import DevOpsEngine
from .websocket.manager import ConnectionManager
from .websocket.events import WebSocketEventHandler

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management
    
    CLAUDE.md: Fail Fast - Check Ollama connectivity early
    CLAUDE.md: < 50 lines total for startup/shutdown logic
    """
    # Startup
    logger.info("Starting NeuraOps Core API...")
    
    # Initialize services
    config = get_config()
    engine = DevOpsEngine()
    
    # Health check Ollama connection (CLAUDE.md: Fail Fast)
    try:
        await engine.health_check()
        logger.info("Ollama connection verified", 
                   base_url=config.ollama.base_url,
                   model=config.ollama.model)
    except Exception as e:
        logger.error("Failed to connect to Ollama", error=str(e))
        raise HTTPException(status_code=503, detail="Ollama service unavailable")
    
    # Initialize WebSocket manager
    app.state.websocket_manager = ConnectionManager()
    app.state.websocket_event_handler = WebSocketEventHandler(app.state.websocket_manager)
    app.state.engine = engine
    
    logger.info("NeuraOps Core API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NeuraOps Core API...")
    await app.state.websocket_manager.disconnect_all()
    logger.info("NeuraOps Core API shutdown complete")