"""
NeuraOps Core API Module

FastAPI-based REST/WebSocket API for distributed agent orchestration
with gpt-oss-20b via Ollama integration.

Architecture:
- JWT Authentication for distributed agents
- Real-time WebSocket communication
- AI command orchestration with safety validation
- Distributed Redis caching for performance
- Prometheus metrics and health monitoring

Follows CLAUDE.md principles:
- KISS: Simple, direct API endpoints
- YAGNI: Build features when demonstrated
- AI-First: All decisions via gpt-oss-20b structured outputs
- Safety-First: Validation before command execution
- Single Responsibility: Each module < 500 lines
"""