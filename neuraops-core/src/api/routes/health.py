"""
Health Check Routes for NeuraOps API

Health monitoring endpoints following CLAUDE.md: < 150 lines, Fail Fast.
Provides system health status and dependency monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Tuple, Dict
from datetime import datetime, timezone
import time
import psutil
import structlog

from ..dependencies import EngineInterface, RedisInterface
from ..models.responses import HealthResponse, APIResponse
from ...devops_commander.config import get_config, get_ollama_config

logger = structlog.get_logger()
router = APIRouter()

# Track service start time for uptime calculation
SERVICE_START_TIME = time.time()


@router.get("/health", response_model=APIResponse[HealthResponse])
async def health_check(
    engine: EngineInterface,
    redis_client: RedisInterface
):
    """
    Comprehensive health check endpoint
    
    CLAUDE.md: Fail Fast - Check all dependencies
    Returns detailed health status for monitoring
    """
    start_time = time.time()
    
    try:
        # Check all service dependencies
        dependencies, overall_status = await _check_dependencies(engine, redis_client)
        
        # Collect system performance metrics
        system_load = _collect_system_metrics()
        
        # Calculate uptime
        uptime_seconds = int(time.time() - SERVICE_START_TIME)
        
        health_data = HealthResponse(
            status=overall_status,
            uptime_seconds=uptime_seconds,
            dependencies=dependencies,
            system_metrics=system_load
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return APIResponse(
            status="success",
            message="Health check completed",
            data=health_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )


@router.get("/health/ready")
async def readiness_check(engine: EngineInterface):
    """
    Kubernetes readiness probe endpoint
    
    CLAUDE.md: Fail Fast - Essential services only
    """
    try:
        # Check critical dependencies only
        await engine.health_check()
        return {"status": "ready"}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint
    
    Simple endpoint to verify service is alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - SERVICE_START_TIME)
    }


@router.get("/health/dependencies")
async def dependencies_check(
    engine: EngineInterface,
    redis_client: RedisInterface
):
    """
    Detailed dependency status check
    
    Returns status of all external dependencies
    """
    dependencies = {}
    
    # Ollama check
    try:
        config = get_ollama_config()
        await engine.health_check()
        dependencies["ollama"] = {
            "status": "healthy",
            "url": config.base_url,
            "model": config.model,
            "timeout": config.timeout
        }
    except Exception as e:
        dependencies["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    if redis_client:
        try:
            await redis_client.ping()
            info = await redis_client.info()
            dependencies["redis"] = {
                "status": "healthy",
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            dependencies["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        dependencies["redis"] = {"status": "disabled"}
    
    return {"dependencies": dependencies}


async def _check_dependencies(
    engine: EngineInterface, 
    redis_client: RedisInterface
) -> Tuple[Dict[str, str], str]:
    """
    Check all service dependencies and return status
    
    CLAUDE.md: Helper function < 20 lines for dependency checks
    """
    dependencies = {}
    overall_status = "healthy"
    
    # Check Ollama (Critical)
    ollama_status = await _check_ollama_health(engine)
    dependencies["ollama"] = ollama_status
    if ollama_status != "healthy":
        overall_status = "degraded"
    
    # Check Redis (Optional)
    redis_status = await _check_redis_health(redis_client)
    dependencies["redis"] = redis_status
    
    return dependencies, overall_status


def _collect_system_metrics() -> Dict[str, float]:
    """
    Collect system performance metrics
    
    CLAUDE.md: Helper function < 10 lines for metrics collection
    Fixes SonarQube S1481: Now system_load variable is properly used
    """
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }


async def _check_ollama_health(engine: EngineInterface) -> str:
    """
    Check Ollama service health
    
    CLAUDE.md: Helper function < 10 lines for Ollama check
    """
    try:
        await engine.health_check()
        return "healthy"
    except Exception as e:
        logger.warning("Ollama health check failed", error=str(e))
        return "unhealthy"


async def _check_redis_health(redis_client: RedisInterface) -> str:
    """
    Check Redis service health
    
    CLAUDE.md: Helper function < 10 lines for Redis check
    """
    if not redis_client:
        return "disabled"
    
    try:
        await redis_client.ping()
        return "healthy"
    except Exception as e:
        logger.warning("Redis health check failed", error=str(e))
        return "unhealthy"