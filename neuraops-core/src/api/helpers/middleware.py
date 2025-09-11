"""
FastAPI Middleware Configuration

Handles security and request middleware setup.
Follows CLAUDE.md: < 100 lines, Security-First operations.
"""
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

logger = structlog.get_logger()


def configure_security_middleware(app: FastAPI, config) -> None:
    """
    Configure security middleware
    
    CLAUDE.md: Security-First - Essential security headers and CORS
    CLAUDE.md: < 20 lines per function
    """
    # Trusted hosts - Allow specific host:port combinations for CLI and containers
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost", "127.0.0.1", "*.prd.ihmn.fr",  # Base hosts
            "localhost:8000", "127.0.0.1:8000",          # Local development
            "neuraops-core:8000", "neuraops-core"        # Docker container names
        ]
    )
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins.split(",") if config.cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def add_request_middleware(app: FastAPI) -> None:
    """
    Add request timing middleware
    
    CLAUDE.md: < 15 lines - Simple request timing
    """
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response