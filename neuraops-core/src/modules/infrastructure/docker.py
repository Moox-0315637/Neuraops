"""
NeuraOps Docker Generator Module
AI-powered Docker configuration generation with gpt-oss-20b
Dockerfile, docker-compose, and container management
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ...core.engine import DevOpsEngine
from ...core.structured_output import (
    DevOpsCommand,
    SafetyLevel,
)
from ...core.command_executor import CommandExecutor
from ...devops_commander.config import NeuraOpsConfig
from ...devops_commander.exceptions import InfrastructureError

logger = logging.getLogger(__name__)

# Constants pour éviter duplication de chaînes
DEFAULT_PYTHON_IMAGE = "python:3.11-slim"


class ContainerRuntime(Enum):
    """Supported container runtimes"""

    DOCKER = "docker"
    PODMAN = "podman"
    CONTAINERD = "containerd"


class BaseImage(Enum):
    """Common base images with security focus"""

    UBUNTU_MINIMAL = "ubuntu:22.04-minimal"
    ALPINE = "alpine:3.18"
    DISTROLESS_JAVA = "gcr.io/distroless/java17"
    DISTROLESS_PYTHON = "gcr.io/distroless/python3"
    DISTROLESS_NODEJS = "gcr.io/distroless/nodejs18"
    NGINX_ALPINE = "nginx:alpine"
    PYTHON_SLIM = DEFAULT_PYTHON_IMAGE
    NODE_ALPINE = "node:18-alpine"


@dataclass
class DockerGenerationRequest:
    """Request for Docker configuration generation"""

    app_name: str
    app_type: str  # web, api, worker, database, etc.
    base_image: str = DEFAULT_PYTHON_IMAGE
    language: str = "python"  # python, nodejs, java, go, etc.
    ports: List[int] = field(default_factory=lambda: [80])
    environment_vars: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    security_hardening: bool = True
    multi_stage: bool = True
    health_check: bool = True
    production_ready: bool = True


@dataclass
class DockerGenerationResult:
    """Result of Docker generation"""

    success: bool
    dockerfile: Optional[str] = None
    docker_compose: Optional[str] = None
    dockerignore: Optional[str] = None
    build_script: Optional[str] = None
    security_recommendations: List[str] = field(default_factory=list)
    optimization_tips: List[str] = field(default_factory=list)
    build_commands: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class DockerGenerator:
    """AI-powered Docker configuration generator with gpt-oss-20b"""

    def __init__(self, config: Optional[NeuraOpsConfig] = None):
        self.config = config or NeuraOpsConfig()
        self.engine = DevOpsEngine(config=self.config.ollama)
        # output_manager removed - not essential for core functionality
        self.command_executor = CommandExecutor(config=self.config.security)

        # Templates for different languages/frameworks
        self.dockerfile_templates = self._load_dockerfile_templates()

    def _load_dockerfile_templates(self) -> Dict[str, str]:
        """Load Dockerfile templates for different languages"""
        return {
            "python": """# Multi-stage Python Dockerfile
FROM {DEFAULT_PYTHON_IMAGE} as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM {DEFAULT_PYTHON_IMAGE}

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy dependencies from builder stage
COPY --from=builder /root/.local /home/appuser/.local

WORKDIR /app
COPY . .

# Security: Change ownership and switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Add local bins to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]""",
            "nodejs": """# Multi-stage Node.js Dockerfile
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine

# Security: Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

WORKDIR /app

# Copy dependencies from builder stage
COPY --from=builder /app/node_modules ./node_modules
COPY . .

# Security: Change ownership and switch to non-root user
RUN chown -R nodejs:nodejs /app
USER nodejs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "server.js"]""",
            "go": """# Multi-stage Go Dockerfile
FROM golang:1.21-alpine as builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

FROM alpine:3.18

# Security: Create non-root user and install CA certificates
RUN apk --no-cache add ca-certificates && \
    addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001

WORKDIR /root/

# Copy binary from builder stage
COPY --from=builder /app/main .

# Security: Change ownership and switch to non-root user
RUN chown appuser:appuser main
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["./main"]""",
        }

    async def generate_dockerfile(self, request: DockerGenerationRequest) -> DockerGenerationResult:
        """Generate optimized Dockerfile with AI enhancement"""

        try:
            logger.info(f"Generating Dockerfile for {request.app_name} ({request.language})")

            # Build AI prompt
            system_prompt = self._build_dockerfile_system_prompt(request)
            user_prompt = self._build_dockerfile_user_prompt(request)

            # Generate with gpt-oss-20b
            dockerfile_content = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Generate complementary files
            dockerignore = self._generate_dockerignore(request)
            docker_compose = await self._generate_docker_compose(request)
            build_script = self._generate_build_script(request)

            # Generate recommendations
            security_recs = await self._generate_docker_security_recommendations(dockerfile_content)
            optimization_tips = self._generate_optimization_tips(request)

            # Generate build commands
            build_commands = self._generate_build_commands(request)

            return DockerGenerationResult(
                success=True,
                dockerfile=dockerfile_content,
                docker_compose=docker_compose,
                dockerignore=dockerignore,
                build_script=build_script,
                security_recommendations=security_recs,
                optimization_tips=optimization_tips,
                build_commands=build_commands,
            )

        except Exception as e:
            logger.error(f"Dockerfile generation failed: {str(e)}")
            return DockerGenerationResult(success=False, error_message=str(e))

    def _build_dockerfile_system_prompt(self, request: DockerGenerationRequest) -> str:
        """Build system prompt for Dockerfile generation"""

        return f"""You are an expert DevOps engineer specializing in Docker and container security.

Generate a production-ready Dockerfile for a {request.language} application with these requirements:

SECURITY REQUIREMENTS:
- Use multi-stage builds to minimize image size
- Run as non-root user with specific UID/GID
- Use minimal base images (Alpine, Distroless when possible)
- Remove unnecessary packages and files
- Set proper file permissions
- Include security scanning annotations

OPTIMIZATION REQUIREMENTS:
- Minimize number of layers
- Use .dockerignore effectively
- Cache dependencies separately from application code
- Use specific package versions
- Optimize build context

OPERATIONAL REQUIREMENTS:
- Include health checks
- Set proper working directory
- Use COPY instead of ADD when possible
- Set reasonable resource limits
- Include labels for metadata

LANGUAGE SPECIFIC ({request.language}):
- Follow {request.language} best practices
- Use appropriate package managers
- Set correct runtime environment
- Include proper dependency management

OUTPUT FORMAT:
Return ONLY the Dockerfile content without markdown formatting.
Do not include explanations before or after the Dockerfile."""

    def _build_dockerfile_user_prompt(self, request: DockerGenerationRequest) -> str:
        """Build user prompt for specific requirements"""

        prompt_parts = [
            f"Generate Dockerfile for {request.language} application: {request.app_name}",
            f"Application type: {request.app_type}",
            f"Base image preference: {request.base_image}",
            f"Exposed ports: {', '.join(map(str, request.ports))}",
        ]

        if request.dependencies:
            prompt_parts.append(f"Dependencies: {', '.join(request.dependencies)}")

        if request.environment_vars:
            env_vars = ", ".join([f"{k}={v}" for k, v in request.environment_vars.items()])
            prompt_parts.append(f"Environment variables: {env_vars}")

        # Add specific requirements
        requirements = []
        if request.security_hardening:
            requirements.append("security hardening")
        if request.multi_stage:
            requirements.append("multi-stage build")
        if request.health_check:
            requirements.append("health check")
        if request.production_ready:
            requirements.append("production-ready configuration")

        if requirements:
            prompt_parts.append(f"Requirements: {', '.join(requirements)}")

        return "\n".join(prompt_parts)

    def _generate_dockerignore(self, request: DockerGenerationRequest) -> str:
        """Generate .dockerignore file"""

        common_patterns = [
            "# Git and version control",
            ".git",
            ".gitignore",
            ".github",
            "README.md",
            "CHANGELOG.md",
            "",
            "# Documentation",
            "docs/",
            "*.md",
            "",
            "# Testing",
            "tests/",
            "test/",
            "*.test.js",
            "*.spec.js",
            "coverage/",
            "",
            "# Development",
            ".vscode/",
            ".idea/",
            "*.log",
            "*.tmp",
            "*.temp",
            "",
            "# OS generated",
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
        ]

        # Language-specific patterns
        language_patterns = {
            "python": [
                "# Python",
                "__pycache__/",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".Python",
                "env/",
                "venv/",
                ".env",
                "pip-log.txt",
                "pip-delete-this-directory.txt",
                ".pytest_cache/",
                "*.egg-info/",
            ],
            "nodejs": [
                "# Node.js",
                "node_modules/",
                "npm-debug.log*",
                "yarn-debug.log*",
                "yarn-error.log*",
                ".npm",
                ".yarn-integrity",
                ".cache/",
            ],
            "go": ["# Go", "*.exe", "*.exe~", "*.dll", "*.so", "*.dylib", "vendor/"],
        }

        patterns = common_patterns
        if request.language in language_patterns:
            patterns.extend([""] + language_patterns[request.language])

        return "\n".join(patterns)

    async def _generate_docker_compose(self, request: DockerGenerationRequest) -> str:
        """Generate docker-compose.yml for development"""

        system_prompt = """Generate a development-focused docker-compose.yml file.
        Include:
        - Service definitions with proper networking
        - Volume mounts for development
        - Environment variables
        - Health checks
        - Dependency management
        - Development-friendly configurations

        Return only valid YAML without markdown formatting."""

        user_prompt = f"""Generate docker-compose.yml for {request.language} application:
        - App name: {request.app_name}
        - Ports: {request.ports}
        - Environment: {request.environment_vars}
        - Type: {request.app_type}

        Include development volumes and networking."""

        try:
            compose_yaml = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Validate YAML
            yaml.safe_load(compose_yaml)
            return compose_yaml

        except Exception as e:
            logger.warning(f"Docker Compose generation failed, using template: {str(e)}")

            # Fallback template
            ports_mapping = "\n".join([f'      - "{port}:{port}"' for port in request.ports])
            env_mapping = "\n".join([f"      - {k}={v}" for k, v in request.environment_vars.items()])

            compose_template = f"""version: '3.8'

services:
  {request.app_name}:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
{ports_mapping}
    environment:
{env_mapping}
    volumes:
      - .:/app
      - /app/node_modules  # Prevent overwriting node_modules in container
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{request.ports[0]}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s"""

            return compose_template

    def _generate_build_script(self, request: DockerGenerationRequest) -> str:
        """Generate build script for Docker image"""

        script_lines = [
            "#!/bin/bash",
            "set -e",
            "",
            "# NeuraOps Generated Docker Build Script",
            f"# Application: {request.app_name}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "echo 'Building Docker image...'",
            "",
            "# Build arguments",
            f'APP_NAME="{request.app_name}"',
            'BUILD_VERSION="$(date +%Y%m%d-%H%M%S)"',
            'IMAGE_TAG="${APP_NAME}:${BUILD_VERSION}"',
            "",
            "# Security scan before build (if trivy available)",
            "if command -v trivy &> /dev/null; then",
            "    echo 'Running security scan...'",
            "    trivy fs . --exit-code 1 --severity HIGH,CRITICAL || {",
            "        echo 'Security scan failed. Fix vulnerabilities before building.'",
            "        exit 1",
            "    }",
            "fi",
            "",
            "# Build image",
            "echo 'Building image: $IMAGE_TAG'",
            "docker build -t $IMAGE_TAG .",
            "docker tag $IMAGE_TAG ${APP_NAME}:latest",
            "",
            "# Security scan of built image",
            "if command -v trivy &> /dev/null; then",
            "    echo 'Scanning built image...'",
            "    trivy image $IMAGE_TAG --exit-code 1 --severity HIGH,CRITICAL",
            "fi",
            "",
            "# Size optimization check",
            "echo 'Image size:'",
            "docker images ${APP_NAME}:latest --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'",
            "",
            "echo 'Build completed successfully!'",
            "echo 'Image: $IMAGE_TAG'",
            "echo 'Latest: ${APP_NAME}:latest'",
            "",
            "# Optional: Push to registry",
            "# docker push $IMAGE_TAG",
            "# docker push ${APP_NAME}:latest",
        ]

        return "\n".join(script_lines)

    async def _generate_docker_security_recommendations(self, dockerfile_content: str) -> List[str]:
        """Generate security recommendations for Dockerfile"""

        system_prompt = """You are a Docker security expert.
        Analyze the provided Dockerfile and provide specific security recommendations.

        Focus on:
        - Base image security and vulnerabilities
        - User privilege escalation
        - File permissions and ownership
        - Secret management
        - Network exposure
        - Runtime security
        - Image scanning and compliance

        Return specific, actionable security recommendations."""

        user_prompt = f"""Analyze this Dockerfile for security improvements:

        ```dockerfile
        {dockerfile_content[:2000]}
        ```

        Provide specific security recommendations as a numbered list."""

        try:
            recommendations_text = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.2)

            # Parse recommendations
            recommendations = []
            for line in recommendations_text.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                    clean_line = line.lstrip("0123456789.-* ").strip()
                    if clean_line:
                        recommendations.append(clean_line)

            return recommendations[:8]

        except Exception as e:
            logger.error(f"Security recommendations failed: {str(e)}")
            return ["Security analysis unavailable"]

    def _generate_optimization_tips(self, request: DockerGenerationRequest) -> List[str]:
        """Generate optimization tips for Docker image"""

        tips = [
            "Use multi-stage builds to reduce image size",
            "Order Dockerfile commands by frequency of change",
            "Use specific package versions for reproducibility",
            "Minimize the number of RUN instructions",
            "Use .dockerignore to exclude unnecessary files",
            "Consider using distroless images for production",
            "Pin base image versions with digest",
            "Use docker buildkit for faster builds",
        ]

        # Add language-specific tips
        if request.language == "python":
            tips.extend(
                [
                    "Use pip install --no-cache-dir to reduce image size",
                    "Consider using poetry or pipenv for dependency management",
                    "Use python -m pip instead of pip for better compatibility",
                ]
            )
        elif request.language == "nodejs":
            tips.extend(
                [
                    "Use npm ci instead of npm install for production",
                    "Delete npm cache after installation",
                    "Consider using node_modules cache mounting in development",
                ]
            )
        elif request.language == "go":
            tips.extend(
                [
                    "Use CGO_ENABLED=0 for static binaries",
                    "Consider using scratch or distroless base for minimal images",
                    "Use go mod download in separate layer for better caching",
                ]
            )

        return tips

    def _generate_build_commands(self, request: DockerGenerationRequest) -> List[str]:
        """Generate Docker build and run commands"""

        commands = [
            "# Build the image",
            f"docker build -t {request.app_name}:latest .",
            "",
            "# Run the container",
            f"docker run -d --name {request.app_name}-container",
        ]

        # Add port mappings
        for port in request.ports:
            commands.append(f"  -p {port}:{port}")

        # Add environment variables
        for key, value in request.environment_vars.items():
            commands.append(f"  -e {key}={value}")

        commands.extend(
            [
                f"  {request.app_name}:latest",
                "",
                "# Check container status",
                f"docker ps | grep {request.app_name}",
                "",
                "# View logs",
                f"docker logs {request.app_name}-container",
                "",
                "# Stop and cleanup",
                f"docker stop {request.app_name}-container",
                f"docker rm {request.app_name}-container",
            ]
        )

        return commands

    async def generate_python_app(self, app_name: str, framework: str = "fastapi", port: int = 8000) -> DockerGenerationResult:
        """Generate Docker configuration for Python application"""

        dependencies = []
        env_vars = {}

        if framework.lower() == "fastapi":
            dependencies = ["fastapi", "uvicorn", "pydantic"]
            env_vars["PORT"] = str(port)
        elif framework.lower() == "flask":
            dependencies = ["flask", "gunicorn"]
            env_vars["FLASK_APP"] = "app.py"
            env_vars["FLASK_ENV"] = "production"
        elif framework.lower() == "django":
            dependencies = ["django", "gunicorn", "psycopg2-binary"]
            env_vars["DJANGO_SETTINGS_MODULE"] = "settings.production"

        request = DockerGenerationRequest(
            app_name=app_name,
            app_type="web",
            language="python",
            base_image=DEFAULT_PYTHON_IMAGE,
            ports=[port],
            dependencies=dependencies,
            environment_vars=env_vars,
            security_hardening=True,
            multi_stage=True,
            health_check=True,
        )

        return await self.generate_dockerfile(request)

    async def generate_nodejs_app(self, app_name: str, framework: str = "express", port: int = 3000) -> DockerGenerationResult:
        """Generate Docker configuration for Node.js application"""

        dependencies = []
        env_vars = {"NODE_ENV": "production", "PORT": str(port)}

        if framework.lower() == "express":
            dependencies = ["express", "helmet", "cors"]
        elif framework.lower() == "nestjs":
            dependencies = ["@nestjs/core", "@nestjs/common", "reflect-metadata"]
        elif framework.lower() == "nextjs":
            dependencies = ["next", "react", "react-dom"]
            env_vars["NEXT_TELEMETRY_DISABLED"] = "1"

        request = DockerGenerationRequest(
            app_name=app_name,
            app_type="web",
            language="nodejs",
            base_image="node:18-alpine",
            ports=[port],
            dependencies=dependencies,
            environment_vars=env_vars,
            security_hardening=True,
            multi_stage=True,
            health_check=True,
        )

        return await self.generate_dockerfile(request)

    async def generate_from_description(self, description: str) -> DockerGenerationResult:
        """Generate Docker configuration from natural language description"""

        # Use AI to parse description
        system_prompt = """Parse the user's application description into Docker requirements.
        Extract: app name, language/framework, ports, dependencies, type.

        Return a JSON object:
        {
          "app_name": "string",
          "language": "python|nodejs|go|java",
          "app_type": "web|api|worker|database",
          "ports": [numbers],
          "dependencies": ["list"],
          "environment_vars": {}
        }"""

        user_prompt = f"""Parse this application description for Docker containerization:
        "{description}"

        Extract specific requirements for containerization."""

        try:
            requirements_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            requirements = json.loads(requirements_json)

            docker_request = DockerGenerationRequest(
                app_name=requirements.get("app_name", "myapp"),
                language=requirements.get("language", "python"),
                app_type=requirements.get("app_type", "web"),
                ports=requirements.get("ports", [8000]),
                dependencies=requirements.get("dependencies", []),
                environment_vars=requirements.get("environment_vars", {}),
            )

            return await self.generate_dockerfile(docker_request)

        except Exception as e:
            logger.error(f"Description parsing failed: {str(e)}")
            # Fallback to basic Python app
            request = DockerGenerationRequest(app_name="myapp", language="python", app_type="web")
            return await self.generate_dockerfile(request)

    def save_docker_files(self, result: DockerGenerationResult, output_dir: str = "./docker-config") -> List[str]:
        """Save generated Docker files"""

        if not result.success:
            raise InfrastructureError(f"Cannot save failed generation: {result.error_message}")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        saved_files = []

        # Save Dockerfile
        if result.dockerfile:
            dockerfile_path = output_path / "Dockerfile"
            dockerfile_path.write_text(result.dockerfile)
            saved_files.append(str(dockerfile_path))

        # Save docker-compose.yml
        if result.docker_compose:
            compose_path = output_path / "docker-compose.yml"
            compose_path.write_text(result.docker_compose)
            saved_files.append(str(compose_path))

        # Save .dockerignore
        if result.dockerignore:
            dockerignore_path = output_path / ".dockerignore"
            dockerignore_path.write_text(result.dockerignore)
            saved_files.append(str(dockerignore_path))

        # Save build script
        if result.build_script:
            script_path = output_path / "build.sh"
            script_path.write_text(result.build_script)
            script_path.chmod(0o755)
            saved_files.append(str(script_path))

        # Save build commands
        if result.build_commands:
            commands_text = "\n".join(result.build_commands)
            commands_path = output_path / "docker-commands.txt"
            commands_path.write_text(commands_text)
            saved_files.append(str(commands_path))

        logger.info(f"Saved {len(saved_files)} Docker files to {output_dir}")
        return saved_files


# Convenience functions for CLI usage
async def quick_generate_python_webapp(app_name: str = "webapp") -> DockerGenerationResult:
    """Quick Python web app Docker generation"""
    generator = DockerGenerator()
    return await generator.generate_python_app(app_name, "fastapi")


async def quick_generate_nodejs_api(app_name: str = "api") -> DockerGenerationResult:
    """Quick Node.js API Docker generation"""
    generator = DockerGenerator()
    return await generator.generate_nodejs_app(app_name, "express")


async def generate_docker_from_description(description: str) -> DockerGenerationResult:
    """Generate Docker configuration from natural language"""
    generator = DockerGenerator()
    return await generator.generate_from_description(description)
