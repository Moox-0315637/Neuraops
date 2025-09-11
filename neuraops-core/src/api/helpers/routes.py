"""
FastAPI Routes Configuration

Handles API routes and root endpoint setup.
Follows CLAUDE.md: < 50 lines, Single Responsibility.
"""
from fastapi import FastAPI
import structlog

from ..routes import agents, commands, workflows, health, metrics
from ..routes import auth, workflows_ui, system, agents_ui, documentation, alerts, cli

logger = structlog.get_logger()


def include_api_routes(app: FastAPI) -> None:
    """
    Include API routes with prefix
    
    CLAUDE.md: Routes pour UI + API existante
    """
    # Routes API existantes
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(agents.router, prefix="/api", tags=["Agents"])
    app.include_router(commands.router, prefix="/api", tags=["Commands"])
    app.include_router(workflows.router, prefix="/api", tags=["Workflows"])
    app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
    
    # Nouvelles routes pour l'UI
    app.include_router(auth.router, prefix="/api", tags=["Authentication"])
    app.include_router(workflows_ui.router, prefix="/api", tags=["Workflow Management"])
    app.include_router(system.router, prefix="/api", tags=["System & Monitoring"])
    app.include_router(agents_ui.router, prefix="/api", tags=["Agent UI Actions"])
    app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
    app.include_router(cli.router, prefix="/api", tags=["CLI"])
    app.include_router(documentation.router, prefix="/api", tags=["Documentation"])


def add_root_endpoint(app: FastAPI) -> None:
    """
    Add root endpoint
    
    CLAUDE.md: < 15 lines - Simple root endpoint
    """
    @app.get("/", include_in_schema=False)
    async def root():
        """API root endpoint"""
        return {
            "name": "NeuraOps Core API",
            "version": "1.1.0",
            "description": "AI-powered DevOps assistant for distributed agents",
            "docs": "/api/docs",
            "health": "/api/health",
            "websocket": "/ws/{agent_id}"
        }