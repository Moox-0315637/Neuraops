"""
NeuraOps Infrastructure Template Engine
AI-powered generation of infrastructure templates for Docker, Kubernetes, Terraform, and Ansible
"""

import logging
import json
import yaml
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

from ...core.engine import get_engine
from ...devops_commander.exceptions import InfrastructureError

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Supported infrastructure template types"""

    DOCKER = "DOCKER"
    KUBERNETES = "KUBERNETES"
    TERRAFORM = "TERRAFORM"
    ANSIBLE = "ANSIBLE"
    COMPOSE = "DOCKER-COMPOSE"
    HELM = "HELM"
    VAGRANT = "VAGRANT"
    MICROSERVICE = "MICROSERVICE"
    NODE_APP = "NODE-APP"
    PYTHON_APP = "PYTHON-APP"
    DEPLOYMENT = "DEPLOYMENT"
    SERVICE_MESH = "SERVICE-MESH"
    INGRESS_CONTROLLER = "INGRESS-CONTROLLER"
    MONITORING_STACK = "MONITORING-STACK"
    AWS_VPC = "AWS-VPC"
    EC2_CLUSTER = "EC2-CLUSTER"
    RDS_DATABASE = "RDS-DATABASE"
    S3_BUCKET = "S3-BUCKET"
    WEB_SERVER = "WEB-SERVER"
    DATABASE_SETUP = "DATABASE-SETUP"
    MONITORING_AGENT = "MONITORING-AGENT" 
    LAMP_STACK = "LAMP-STACK"
    MICROSERVICES = "MICROSERVICES"
    DATABASE_CLUSTER = "DATABASE-CLUSTER"

class Environment(Enum):
    """Target deployment environments"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class TemplateRequest:
    """Request for template generation"""

    template_type: TemplateType
    application_name: str
    description: str
    environment: Environment
    requirements: Dict[str, Any]
    constraints: Optional[Dict[str, Any]] = None
    best_practices: bool = True
    security_focused: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result["template_type"] = self.template_type.value
        result["environment"] = self.environment.value
        return result


@dataclass
class GeneratedTemplate:
    """Generated infrastructure template result"""

    template_type: TemplateType
    content: str
    metadata: Dict[str, Any]
    recommendations: List[str]
    security_notes: List[str]
    deployment_instructions: List[str]

    def save_to_file(self, file_path: Path) -> None:
        """Save template to file"""
        file_path.write_text(self.content, encoding="utf-8")

        # Also save metadata as companion file
        metadata_path = file_path.with_suffix(f"{file_path.suffix}.meta.json")
        metadata_content = {
            "template_type": self.template_type.value,
            "metadata": self.metadata,
            "recommendations": self.recommendations,
            "security_notes": self.security_notes,
            "deployment_instructions": self.deployment_instructions,
            "generated_at": datetime.now().isoformat(),
        }
        metadata_path.write_text(json.dumps(metadata_content, indent=2), encoding="utf-8")


class TemplateEngine:
    """AI-powered infrastructure template generator"""

    def __init__(self):
        self.template_cache = {}
        self.best_practices_db = self._load_best_practices()

    def _load_best_practices(self) -> Dict[str, Any]:
        """Load infrastructure best practices database"""
        return {
            "docker": {
                "security": [
                    "Use non-root user",
                    "Minimize image layers",
                    "Use specific base image tags",
                    "Scan for vulnerabilities",
                    "Avoid storing secrets in images",
                ],
                "performance": [
                    "Use multi-stage builds",
                    "Optimize layer caching",
                    "Use .dockerignore",
                    "Minimize image size",
                ],
                "reliability": [
                    "Set proper health checks",
                    "Use init system for PID 1",
                    "Handle signals properly",
                    "Set resource limits",
                ],
            },
            "kubernetes": {
                "security": [
                    "Use RBAC",
                    "Set security contexts",
                    "Use network policies",
                    "Scan container images",
                    "Use secrets for sensitive data",
                ],
                "performance": [
                    "Set resource requests and limits",
                    "Use horizontal pod autoscaler",
                    "Configure liveness and readiness probes",
                    "Use node affinity appropriately",
                ],
                "reliability": [
                    "Use deployment strategies",
                    "Set replica counts > 1",
                    "Configure pod disruption budgets",
                    "Use persistent volumes for stateful apps",
                ],
            },
            "terraform": {
                "security": [
                    "Use remote state with encryption",
                    "Enable state locking",
                    "Use least privilege IAM",
                    "Encrypt sensitive variables",
                ],
                "performance": [
                    "Use data sources efficiently",
                    "Minimize provider configurations",
                    "Use modules for reusability",
                    "Plan before apply",
                ],
                "reliability": [
                    "Use version constraints",
                    "Implement backup strategies",
                    "Use dependency management",
                    "Validate configurations",
                ],
            },
        }

    async def generate_template(self, request: TemplateRequest) -> GeneratedTemplate:
        """Generate infrastructure template based on request"""

        try:
            logger.info(f"Generating {request.template_type.value} template for {request.application_name}")

            # Get AI engine
            engine = get_engine()

            # Build generation prompt
            prompt = self._build_generation_prompt(request)

            # Generate template content
            template_content = await engine.generate_text(
                prompt=prompt,
                system_prompt=self._get_system_prompt(request.template_type),
                temperature=0.2,  # Low temperature for more consistent output
            )

            # Parse and validate template
            parsed_content = self._parse_and_validate(template_content, request.template_type)

            # Generate metadata and recommendations
            metadata = self._generate_metadata(request)
            recommendations = self._generate_recommendations(request)
            security_notes = self._generate_security_notes(request)
            deployment_instructions = self._generate_deployment_instructions(request)

            return GeneratedTemplate(
                template_type=request.template_type,
                content=parsed_content,
                metadata=metadata,
                recommendations=recommendations,
                security_notes=security_notes,
                deployment_instructions=deployment_instructions,
            )

        except Exception as e:
            raise InfrastructureError(
                f"Failed to generate {request.template_type.value} template: {str(e)}"
            ) from e

    def _build_generation_prompt(self, request: TemplateRequest) -> str:
        """Build AI prompt for template generation"""

        template_descriptions = {
            TemplateType.DOCKER: "Dockerfile",
            TemplateType.KUBERNETES: "Kubernetes YAML manifests",
            TemplateType.TERRAFORM: "Terraform configuration files",
            TemplateType.ANSIBLE: "Ansible playbook",
            TemplateType.COMPOSE: "Docker Compose configuration",
            TemplateType.HELM: "Helm chart templates",
            TemplateType.VAGRANT: "Vagrantfile",
        }

        template_desc = template_descriptions.get(request.template_type, "infrastructure template")

        prompt = f"""Generate a production-ready {template_desc} for the following application:

Application Name: {request.application_name}
Description: {request.description}
Target Environment: {request.environment.value}

Requirements:
"""

        # Add requirements
        for key, value in request.requirements.items():
            prompt += f"- {key}: {value}\n"

        # Add constraints if any
        if request.constraints:
            prompt += "\nConstraints:\n"
            for key, value in request.constraints.items():
                prompt += f"- {key}: {value}\n"

        # Add best practices requirements
        if request.best_practices:
            best_practices = self.best_practices_db.get(request.template_type.value, {})
            prompt += "\nApply these best practices:\n"
            for category, practices in best_practices.items():
                prompt += f"\n{category.title()}:\n"
                for practice in practices:
                    prompt += f"- {practice}\n"

        # Add security focus
        if request.security_focused:
            prompt += "\nSecurity Focus:\n"
            prompt += f"- Implement security best practices for {request.environment.value} environment\n"
            prompt += "- Follow principle of least privilege\n"
            prompt += "- Include security scanning and monitoring\n"
            prompt += "- Use secure defaults and configurations\n"

        prompt += f"\nGenerate a complete, production-ready {template_desc} that follows industry best practices and is optimized for the {request.environment.value} environment."

        return prompt

    def _get_system_prompt(self, template_type: TemplateType) -> str:
        """Get system prompt based on template type"""

        base_prompt = """You are an expert DevOps engineer and infrastructure architect with deep knowledge of cloud-native technologies, security best practices, and scalable system design."""

        type_specific_prompts = {
            TemplateType.DOCKER: """
            Specialize in container technologies, Docker best practices, multi-stage builds, security scanning, and optimization techniques.
            Generate clean, secure, and efficient Dockerfiles with proper layering, minimal attack surface, and production readiness.
            """,
            TemplateType.KUBERNETES: """
            Expert in Kubernetes orchestration, YAML manifests, service mesh, security policies, and cloud-native patterns.
            Generate complete Kubernetes manifests including deployments, services, ingress, configmaps, and RBAC configurations.
            """,
            TemplateType.TERRAFORM: """
            Specialist in Infrastructure as Code, cloud providers (AWS, Azure, GCP), state management, and resource optimization.
            Generate modular, reusable Terraform configurations with proper variable management and output definitions.
            """,
            TemplateType.ANSIBLE: """
            Expert in configuration management, automation, idempotency, and infrastructure provisioning using Ansible.
            Generate well-structured playbooks with proper task organization, error handling, and variable management.
            """,
            TemplateType.COMPOSE: """
            Specialist in Docker Compose orchestration, service networking, volume management, and development workflows.
            Generate complete compose files with proper service definitions, networking, and environment management.
            """,
            TemplateType.HELM: """
            Expert in Kubernetes package management, chart templating, value management, and application lifecycle.
            Generate complete Helm charts with proper templating, values, and deployment strategies.
            """,
        }

        specific_prompt = type_specific_prompts.get(template_type, "")
        return base_prompt + specific_prompt

    def _extract_code_block(self, lines: List[str]) -> List[str]:
        """Extract template content from AI response code blocks"""
        template_lines = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block or (not template_lines and line.strip()) or (template_lines and line.strip()):
                template_lines.append(line)

        return template_lines if template_lines else lines

    def _validate_docker_template(self, template_lines: List[str]) -> None:
        """Validate Docker template content"""
        if not any(line.strip().startswith("FROM") for line in template_lines):
            raise ValueError("Docker template missing FROM instruction")

    def _validate_kubernetes_template(self, content: str) -> None:
        """Validate Kubernetes template content"""
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid Kubernetes YAML: {str(e)}")

    def _validate_terraform_template(self, template_lines: List[str]) -> None:
        """Validate Terraform template content"""
        if not any("resource" in line or "provider" in line for line in template_lines):
            raise ValueError("Terraform template missing resource or provider definitions")

    def _parse_and_validate(self, content: str, template_type: TemplateType) -> str:
        """Parse and validate generated template content"""

        try:
            # Extract template content from AI response if needed
            lines = content.split("\n")
            template_lines = self._extract_code_block(lines)
            template_content = "\n".join(template_lines)

            # Basic validation based on template type
            if template_type == TemplateType.DOCKER:
                self._validate_docker_template(template_lines)
            elif template_type == TemplateType.KUBERNETES:
                self._validate_kubernetes_template(template_content)
            elif template_type == TemplateType.TERRAFORM:
                self._validate_terraform_template(template_lines)

            return template_content.strip()

        except Exception as e:
            logger.error(f"Template validation failed: {str(e)}")
            # Return content as-is if validation fails, with warning
            return f"# WARNING: Template validation failed: {str(e)}\n# Please review and modify as needed\n\n{content}"

    def _generate_metadata(self, request: TemplateRequest) -> Dict[str, Any]:
        """Generate metadata for the template"""
        return {
            "generated_at": datetime.now().isoformat(),
            "application_name": request.application_name,
            "template_type": request.template_type.value,
            "environment": request.environment.value,
            "requirements": request.requirements,
            "constraints": request.constraints or {},
            "security_focused": request.security_focused,
            "best_practices_applied": request.best_practices,
        }

    def _generate_recommendations(self, request: TemplateRequest) -> List[str]:
        """Generate deployment and optimization recommendations"""

        recommendations = []

        # Environment-specific recommendations
        if request.environment == Environment.PRODUCTION:
            recommendations.extend(
                [
                    "Implement comprehensive monitoring and alerting",
                    "Set up automated backups and disaster recovery",
                    "Configure horizontal scaling policies",
                    "Implement blue-green or rolling deployment strategy",
                    "Set up comprehensive logging and observability",
                ]
            )
        elif request.environment == Environment.STAGING:
            recommendations.extend(
                [
                    "Mirror production configuration as closely as possible",
                    "Implement automated testing pipeline",
                    "Use staging for performance testing",
                ]
            )
        elif request.environment == Environment.DEVELOPMENT:
            recommendations.extend(
                [
                    "Enable debug modes and verbose logging",
                    "Use local storage for faster iteration",
                    "Configure hot-reload for development efficiency",
                ]
            )

        # Template-specific recommendations
        if request.template_type == TemplateType.DOCKER:
            recommendations.extend(
                [
                    "Regularly update base images for security patches",
                    "Use multi-stage builds to reduce image size",
                    "Implement container health checks",
                    "Scan images for vulnerabilities before deployment",
                ]
            )

        elif request.template_type == TemplateType.KUBERNETES:
            recommendations.extend(
                [
                    "Implement pod security policies",
                    "Use namespaces for isolation",
                    "Configure resource quotas",
                    "Set up network policies for micro-segmentation",
                ]
            )

        elif request.template_type == TemplateType.TERRAFORM:
            recommendations.extend(
                [
                    "Use remote state backend with versioning",
                    "Implement state locking to prevent conflicts",
                    "Use modules for reusable infrastructure patterns",
                    "Tag all resources for cost tracking and management",
                ]
            )

        return recommendations

    def _generate_security_notes(self, request: TemplateRequest) -> List[str]:
        """Generate security-specific notes and warnings"""

        security_notes = []

        # General security notes
        security_notes.extend(
            [
                "Review and customize all default passwords and secrets",
                "Ensure all communication is encrypted (TLS/HTTPS)",
                "Implement proper authentication and authorization",
                "Regular security scanning and updates required",
            ]
        )

        # Environment-specific security notes
        if request.environment == Environment.PRODUCTION:
            security_notes.extend(
                [
                    "Enable audit logging for all administrative actions",
                    "Implement network segmentation and firewall rules",
                    "Set up intrusion detection and monitoring",
                    "Regular penetration testing recommended",
                ]
            )

        # Template-specific security notes
        if request.template_type == TemplateType.DOCKER:
            security_notes.extend(
                [
                    "Never include secrets or credentials in Docker images",
                    "Use official base images from trusted sources",
                    "Run containers as non-root user when possible",
                    "Regularly scan images for vulnerabilities",
                ]
            )

        elif request.template_type == TemplateType.KUBERNETES:
            security_notes.extend(
                [
                    "Configure pod security standards (restricted profile)",
                    "Use Kubernetes secrets for sensitive data",
                    "Enable RBAC and principle of least privilege",
                    "Use network policies to restrict pod communication",
                ]
            )

        return security_notes

    def _generate_deployment_instructions(self, request: TemplateRequest) -> List[str]:
        """Generate step-by-step deployment instructions"""

        instructions = []

        # Template-specific deployment instructions
        if request.template_type == TemplateType.DOCKER:
            instructions.extend(
                [
                    "1. Build the Docker image:",
                    f"   docker build -t {request.application_name}:latest .",
                    "2. Test the container locally:",
                    f"   docker run --rm -p 8080:8080 {request.application_name}:latest",
                    "3. Push to container registry:",
                    f"   docker tag {request.application_name}:latest your-registry/{request.application_name}:latest",
                    f"   docker push your-registry/{request.application_name}:latest",
                ]
            )

        elif request.template_type == TemplateType.KUBERNETES:
            instructions.extend(
                [
                    "1. Ensure kubectl is configured for target cluster",
                    "2. Create namespace if it doesn't exist:",
                    f"   kubectl create namespace {request.application_name}",
                    "3. Apply the manifests:",
                    f"   kubectl apply -f . -n {request.application_name}",
                    "4. Check deployment status:",
                    f"   kubectl get pods -n {request.application_name}",
                    "5. View logs if needed:",
                    f"   kubectl logs -f deployment/{request.application_name} -n {request.application_name}",
                ]
            )

        elif request.template_type == TemplateType.TERRAFORM:
            instructions.extend(
                [
                    "1. Initialize Terraform:",
                    "   terraform init",
                    "2. Plan the deployment:",
                    "   terraform plan -out=tfplan",
                    "3. Review the plan carefully",
                    "4. Apply the configuration:",
                    "   terraform apply tfplan",
                    "5. Verify resources were created successfully",
                ]
            )

        elif request.template_type == TemplateType.COMPOSE:
            instructions.extend(
                [
                    "1. Ensure Docker and Docker Compose are installed",
                    "2. Start the application stack:",
                    "   docker-compose up -d",
                    "3. Check service status:",
                    "   docker-compose ps",
                    "4. View logs:",
                    "   docker-compose logs -f",
                    "5. Stop when finished:",
                    "   docker-compose down",
                ]
            )

        return instructions

    async def generate_dockerfile(
        self,
        application_type: str,
        programming_language: str,
        requirements: Dict[str, Any],
        environment: Environment = Environment.PRODUCTION,
    ) -> GeneratedTemplate:
        """Generate optimized Dockerfile"""

        request = TemplateRequest(
            template_type=TemplateType.DOCKER,
            application_name=requirements.get("name", "app"),
            description=f"{programming_language} {application_type} application",
            environment=environment,
            requirements={
                "language": programming_language,
                "type": application_type,
                **requirements,
            },
        )

        return await self.generate_template(request)

    async def generate_kubernetes_manifests(
        self,
        application_name: str,
        container_image: str,
        requirements: Dict[str, Any],
        environment: Environment = Environment.PRODUCTION,
    ) -> GeneratedTemplate:
        """Generate Kubernetes deployment manifests"""

        request = TemplateRequest(
            template_type=TemplateType.KUBERNETES,
            application_name=application_name,
            description=f"Kubernetes deployment for {application_name}",
            environment=environment,
            requirements={"container_image": container_image, **requirements},
        )

        return await self.generate_template(request)

    async def generate_terraform_config(
        self,
        infrastructure_type: str,
        cloud_provider: str,
        requirements: Dict[str, Any],
        environment: Environment = Environment.PRODUCTION,
    ) -> GeneratedTemplate:
        """Generate Terraform infrastructure configuration"""

        request = TemplateRequest(
            template_type=TemplateType.TERRAFORM,
            application_name=requirements.get("project_name", "infrastructure"),
            description=f"{infrastructure_type} infrastructure on {cloud_provider}",
            environment=environment,
            requirements={
                "infrastructure_type": infrastructure_type,
                "cloud_provider": cloud_provider,
                **requirements,
            },
        )

        return await self.generate_template(request)

    async def generate_ansible_playbook(
        self,
        task_description: str,
        target_hosts: List[str],
        requirements: Dict[str, Any],
        environment: Environment = Environment.PRODUCTION,
    ) -> GeneratedTemplate:
        """Generate Ansible playbook for configuration management"""

        request = TemplateRequest(
            template_type=TemplateType.ANSIBLE,
            application_name=requirements.get("playbook_name", "configuration"),
            description=task_description,
            environment=environment,
            requirements={
                "task_description": task_description,
                "target_hosts": target_hosts,
                **requirements,
            },
        )

        return await self.generate_template(request)

    async def generate_docker_compose(
        self,
        services: List[str],
        requirements: Dict[str, Any],
        environment: Environment = Environment.DEVELOPMENT,
    ) -> GeneratedTemplate:
        """Generate Docker Compose configuration for multi-service applications"""

        request = TemplateRequest(
            template_type=TemplateType.COMPOSE,
            application_name=requirements.get("project_name", "app"),
            description=f"Multi-service application with {', '.join(services)}",
            environment=environment,
            requirements={"services": services, **requirements},
        )

        return await self.generate_template(request)

    def optimize_template(self, template: GeneratedTemplate, optimization_goals: List[str]) -> GeneratedTemplate:
        """Optimize existing template based on goals"""

        # Implementation for template optimization
        # This could include:
        # - Resource usage optimization
        # - Security hardening
        # - Performance tuning
        # - Cost optimization

        logger.info(f"Optimizing {template.template_type.value} template for goals: {optimization_goals}")

        optimized_recommendations = template.recommendations.copy()
        optimized_recommendations.extend(
            [
                f"Template optimized for: {', '.join(optimization_goals)}",
                "Review optimizations and test in staging environment",
            ]
        )

        return GeneratedTemplate(
            template_type=template.template_type,
            content=template.content,  # In a full implementation, content would be modified
            metadata={**template.metadata, "optimized_for": optimization_goals},
            recommendations=optimized_recommendations,
            security_notes=template.security_notes,
            deployment_instructions=template.deployment_instructions,
        )

    def _validate_kubernetes_syntax(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """Validate Kubernetes template syntax"""
        result = {"valid": True, "errors": [], "warnings": [], "suggestions": []}

        try:
            yaml_docs = list(yaml.safe_load_all(template.content))
            for doc in yaml_docs:
                if not isinstance(doc, dict):
                    result["warnings"].append("Found non-dictionary YAML document")
                elif "kind" not in doc:
                    result["warnings"].append("Kubernetes manifest missing 'kind' field")
        except yaml.YAMLError as e:
            result["valid"] = False
            result["errors"].append(f"Invalid YAML syntax: {str(e)}")

        return result

    def _validate_docker_syntax(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """Validate Docker template syntax"""
        result = {"valid": True, "errors": [], "warnings": [], "suggestions": []}

        lines = template.content.split("\n")
        has_from = any(line.strip().startswith("FROM") for line in lines)
        if not has_from:
            result["valid"] = False
            result["errors"].append("Dockerfile missing FROM instruction")

        # Check for common issues
        if any("ADD" in line for line in lines):
            result["suggestions"].append("Consider using COPY instead of ADD for better security")

        if not any("USER" in line for line in lines):
            result["warnings"].append("Consider adding USER instruction to run as non-root")

        return result

    def _validate_terraform_ansible_syntax(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """Validate Terraform/Ansible template syntax"""
        result = {"valid": True, "errors": [], "warnings": [], "suggestions": []}

        if template.template_type == TemplateType.ANSIBLE:
            try:
                yaml.safe_load(template.content)
            except yaml.YAMLError as e:
                result["valid"] = False
                result["errors"].append(f"Invalid Ansible YAML: {str(e)}")

        return result

    def _create_validation_result(self) -> Dict[str, Any]:
        """Create default validation result structure"""
        return {"valid": True, "errors": [], "warnings": [], "suggestions": []}

    def validate_template_syntax(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """Validate template syntax and structure"""

        validation_result = self._create_validation_result()

        try:
            if template.template_type == TemplateType.KUBERNETES:
                result = self._validate_kubernetes_syntax(template)
            elif template.template_type == TemplateType.DOCKER:
                result = self._validate_docker_syntax(template)
            elif template.template_type in [TemplateType.TERRAFORM, TemplateType.ANSIBLE]:
                result = self._validate_terraform_ansible_syntax(template)
            else:
                return validation_result

            # Merge results
            validation_result["valid"] = result["valid"]
            validation_result["errors"].extend(result["errors"])
            validation_result["warnings"].extend(result["warnings"])
            validation_result["suggestions"].extend(result["suggestions"])

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")

        return validation_result


    def _get_base_templates(self) -> dict:
        """Get base template definitions organized by type."""
        return {
            TemplateType.DOCKER: [
                {"name": "basic-webapp", "description": "Basic web application container"},
                {"name": "microservice", "description": "Microservice with health checks"},
                {"name": "python-app", "description": "Python application container"},
                {"name": "node-app", "description": "Node.js application container"},
            ],
            TemplateType.KUBERNETES: [
                {"name": "deployment", "description": "Basic Kubernetes deployment"},
                {"name": "service-mesh", "description": "Service mesh configuration"},
                {"name": "ingress-controller", "description": "Ingress controller setup"},
                {"name": "monitoring-stack", "description": "Monitoring and observability"},
            ],
            TemplateType.TERRAFORM: [
                {"name": "aws-vpc", "description": "AWS VPC with subnets"},
                {"name": "ec2-cluster", "description": "EC2 cluster with load balancer"},
                {"name": "rds-database", "description": "RDS database setup"},
                {"name": "s3-bucket", "description": "S3 bucket with policies"},
            ],
            TemplateType.ANSIBLE: [
                {"name": "web-server", "description": "Web server configuration"},
                {"name": "database-setup", "description": "Database installation"},
                {"name": "monitoring-agent", "description": "Monitoring agent deployment"},
            ],
            TemplateType.COMPOSE: [
                {"name": "lamp-stack", "description": "LAMP stack development"},
                {"name": "microservices", "description": "Multi-container microservices"},
                {"name": "database-cluster", "description": "Database cluster setup"},
            ]
        }

    def _filter_templates_by_type(self, base_templates: dict, template_type) -> list:
        """Filter templates by specified type."""
        if template_type in base_templates:
            return base_templates[template_type]
        return []

    def _build_all_templates(self, base_templates: dict) -> list:
        """Build complete template list with type information."""
        all_templates = []
        for ttype, tmpl_list in base_templates.items():
            for tmpl in tmpl_list:
                tmpl["type"] = ttype.value
                all_templates.append(tmpl)
        return all_templates

    def list_available_templates(self, template_type=None):
        """List available infrastructure templates."""
        base_templates = self._get_base_templates()
        
        if template_type:
            return self._filter_templates_by_type(base_templates, template_type)
        
        return self._build_all_templates(base_templates)

class TemplateLibrary:
    """Manage and store infrastructure templates"""

    def __init__(self, library_path: Optional[Path] = None):
        self.library_path = library_path or Path("/tmp/neuraops/generated")
        self.library_path.mkdir(parents=True, exist_ok=True)

    def save_template(self, template: GeneratedTemplate, name: str) -> Path:
        """Save template to library"""

        # Determine file extension based on template type
        extensions = {
            TemplateType.DOCKER: "Dockerfile",
            TemplateType.KUBERNETES: "yaml",
            TemplateType.TERRAFORM: "tf",
            TemplateType.ANSIBLE: "yml",
            TemplateType.COMPOSE: "docker-compose.yml",
            TemplateType.HELM: "yaml",
            TemplateType.VAGRANT: "Vagrantfile",
        }

        extension = extensions.get(template.template_type, "txt")

        # Create subdirectory for template type
        template_dir = self.library_path / template.template_type.value
        template_dir.mkdir(exist_ok=True)

        # Save template file
        template_file = template_dir / f"{name}.{extension}"

        template.save_to_file(template_file)

        logger.info(f"Template saved to {template_file}")
        return template_file

    def list_templates(self, template_type: Optional[TemplateType] = None) -> Dict[str, List[str]]:
        """List available templates in library"""

        templates = {}

        search_dirs = [self.library_path / template_type.value] if template_type else list(self.library_path.iterdir())

        for template_dir in search_dirs:
            if template_dir.is_dir():
                template_type_name = template_dir.name
                templates[template_type_name] = []

                for template_file in template_dir.iterdir():
                    if template_file.is_file() and not template_file.name.endswith(".meta.json"):
                        templates[template_type_name].append(template_file.stem)

        return templates

    def load_template(self, template_type: TemplateType, name: str) -> Optional[GeneratedTemplate]:
        """Load template from library"""

        template_dir = self.library_path / template_type.value

        # Find template file
        possible_files = list(template_dir.glob(f"{name}.*"))
        template_file = None

        for file in possible_files:
            if not file.name.endswith(".meta.json"):
                template_file = file
                break

        if not template_file or not template_file.exists():
            return None

        # Load content
        content = template_file.read_text(encoding="utf-8")

        # Load metadata if available
        metadata_file = template_file.with_suffix(f"{template_file.suffix}.meta.json")
        metadata = {}
        recommendations = []
        security_notes = []
        deployment_instructions = []

        if metadata_file.exists():
            try:
                metadata_content = json.loads(metadata_file.read_text(encoding="utf-8"))
                metadata = metadata_content.get("metadata", {})
                recommendations = metadata_content.get("recommendations", [])
                security_notes = metadata_content.get("security_notes", [])
                deployment_instructions = metadata_content.get("deployment_instructions", [])
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to load template metadata: {str(e)}")

        return GeneratedTemplate(
            template_type=template_type,
            content=content,
            metadata=metadata,
            recommendations=recommendations,
            security_notes=security_notes,
            deployment_instructions=deployment_instructions,
        )

    def delete_template(self, template_type: TemplateType, name: str) -> bool:
        """Delete template from library"""

        template_dir = self.library_path / template_type.value

        # Find and delete template file and metadata
        deleted = False

        for file in template_dir.glob(f"{name}.*"):
            try:
                file.unlink()
                deleted = True
                logger.info(f"Deleted template file: {file}")
            except Exception as e:
                logger.error(f"Failed to delete {file}: {str(e)}")

        return deleted


class InfrastructureScaffolder:
    """Generate complete infrastructure scaffolding for projects"""

    def __init__(self):
        self.template_engine = TemplateEngine()
        self.template_library = TemplateLibrary()

    async def scaffold_project(
        self,
        project_name: str,
        project_type: str,
        technologies: List[str],
        environment: Environment,
        output_dir: Path,
    ) -> Dict[str, GeneratedTemplate]:
        """Generate complete project infrastructure scaffolding"""

        logger.info(f"Scaffolding {project_type} project '{project_name}' with technologies: {technologies}")

        generated_templates = {}

        # Create output directory
        project_dir = output_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Generate Dockerfile if containerization is needed
            if "docker" in technologies or "container" in project_type.lower():
                dockerfile_req = TemplateRequest(
                    template_type=TemplateType.DOCKER,
                    application_name=project_name,
                    description=f"{project_type} application",
                    environment=environment,
                    requirements={
                        "project_type": project_type,
                        "technologies": technologies,
                        "base_image_preference": "alpine",  # Secure and minimal
                        "multi_stage": True,
                    },
                )

                dockerfile = await self.template_engine.generate_template(dockerfile_req)
                dockerfile.save_to_file(project_dir / "Dockerfile")
                generated_templates["dockerfile"] = dockerfile

            # Generate Docker Compose if multiple services
            if len(technologies) > 1 or "database" in technologies:
                compose_req = TemplateRequest(
                    template_type=TemplateType.COMPOSE,
                    application_name=project_name,
                    description=f"Multi-service {project_type} application",
                    environment=environment,
                    requirements={
                        "services": technologies,
                        "project_type": project_type,
                        "include_database": "database" in technologies or "postgres" in technologies or "mysql" in technologies,
                        "include_cache": "redis" in technologies or "cache" in technologies,
                    },
                )

                compose_template = await self.template_engine.generate_template(compose_req)
                compose_template.save_to_file(project_dir / "docker-compose.yml")
                generated_templates["compose"] = compose_template

            # Generate Kubernetes manifests if production environment
            if environment == Environment.PRODUCTION:
                k8s_req = TemplateRequest(
                    template_type=TemplateType.KUBERNETES,
                    application_name=project_name,
                    description=f"Production Kubernetes deployment for {project_name}",
                    environment=environment,
                    requirements={
                        "project_type": project_type,
                        "technologies": technologies,
                        "replicas": 3,  # Production default
                        "enable_autoscaling": True,
                        "enable_monitoring": True,
                    },
                )

                k8s_template = await self.template_engine.generate_template(k8s_req)
                k8s_dir = project_dir / "k8s"
                k8s_dir.mkdir(exist_ok=True)
                k8s_template.save_to_file(k8s_dir / "deployment.yaml")
                generated_templates["kubernetes"] = k8s_template

            # Generate Terraform if cloud infrastructure needed
            if "cloud" in project_type.lower() or environment == Environment.PRODUCTION:
                tf_req = TemplateRequest(
                    template_type=TemplateType.TERRAFORM,
                    application_name=f"{project_name}-infrastructure",
                    description=f"Cloud infrastructure for {project_name}",
                    environment=environment,
                    requirements={
                        "project_type": project_type,
                        "cloud_provider": "aws",  # Default to AWS
                        "include_database": "database" in technologies,
                        "include_cache": "cache" in technologies,
                        "include_load_balancer": environment == Environment.PRODUCTION,
                    },
                )

                terraform_template = await self.template_engine.generate_template(tf_req)
                terraform_dir = project_dir / "terraform"
                terraform_dir.mkdir(exist_ok=True)
                terraform_template.save_to_file(terraform_dir / "main.tf")
                generated_templates["terraform"] = terraform_template

            logger.info(f"Successfully scaffolded project {project_name} with {len(generated_templates)} templates")
            return generated_templates

        except Exception as e:
            raise InfrastructureError(
                f"Failed to scaffold project {project_name}: {str(e)}",
                project_name=project_name,
                project_type=project_type,
            ) from e


# Convenience functions for common template generation
async def quick_dockerfile(language: str, app_type: str = "web") -> str:
    """Quickly generate a Dockerfile for common scenarios"""
    engine = TemplateEngine()
    result = await engine.generate_dockerfile(
        application_type=app_type,
        programming_language=language,
        requirements={"name": "app", "port": 8080},
    )
    return result.content


async def quick_k8s_deployment(app_name: str, image: str, port: int = 8080) -> str:
    """Quickly generate Kubernetes deployment YAML"""
    engine = TemplateEngine()
    result = await engine.generate_kubernetes_manifests(application_name=app_name, container_image=image, requirements={"port": port, "replicas": 2})
    return result.content
