"""
NeuraOps Terraform Generator Module
AI-powered Infrastructure as Code generation with gpt-oss-20b
Multi-provider support: AWS, Azure, GCP, OCI
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from ...core.engine import DevOpsEngine
from ...core.command_executor import CommandExecutor, SafetyLevel
from ...devops_commander.config import NeuraOpsConfig

logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    """Supported cloud providers"""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OCI = "oci"
    DIGITAL_OCEAN = "digitalocean"


class InfrastructureType(Enum):
    """Types of infrastructure to generate"""

    WEB_APP_3_TIER = "web_app_3_tier"
    MICROSERVICES = "microservices"
    DATABASE_CLUSTER = "database_cluster"
    KUBERNETES_CLUSTER = "kubernetes_cluster"
    MONITORING_STACK = "monitoring_stack"
    CI_CD_PIPELINE = "ci_cd_pipeline"
    LOAD_BALANCER = "load_balancer"
    STORAGE_SOLUTION = "storage_solution"


@dataclass
class TerraformGenerationRequest:
    """Request for Terraform code generation"""

    description: str
    provider: CloudProvider
    infra_type: InfrastructureType
    requirements: Dict[str, Any] = field(default_factory=dict)
    security_level: str = "standard"  # standard, enhanced, strict
    budget_range: Optional[str] = None  # low, medium, high
    environment: str = "production"  # dev, staging, production
    region: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class TerraformGenerationResult:
    """Result of Terraform generation"""

    success: bool
    terraform_code: Optional[str] = None
    variables_file: Optional[str] = None
    outputs_file: Optional[str] = None
    validation_results: List[str] = field(default_factory=list)
    security_recommendations: List[str] = field(default_factory=list)
    cost_estimate: Optional[Dict[str, Any]] = None
    deployment_instructions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class TerraformGenerator:
    """AI-powered Terraform code generator with gpt-oss-20b"""

    def __init__(self, config: Optional[NeuraOpsConfig] = None):
        self.config = config or NeuraOpsConfig()
        self.engine = DevOpsEngine(config=self.config.ollama)
        self.command_executor = CommandExecutor(config=self.config.security)

        # Templates and best practices
        self.provider_templates = self._load_provider_templates()

    def _load_provider_templates(self) -> Dict[str, Dict[str, str]]:
        """Load provider-specific templates and patterns"""
        return {
            CloudProvider.AWS.value: {
                "provider_block": """terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.common_tags
  }
}""",
                "variables": """variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Project     = "neuraops-managed"
    ManagedBy   = "terraform"
  }
}""",
                "outputs": """output "deployment_info" {
  description = "Deployment information"
  value = {
    provider    = "aws"
    region      = var.aws_region
    environment = var.environment
  }
}""",
            }
        }

    async def generate_infrastructure(self, request: TerraformGenerationRequest) -> TerraformGenerationResult:
        """Generate complete Terraform infrastructure"""

        try:
            logger.info(f"Generating {request.infra_type.value} for {request.provider.value}")

            # Build AI prompt for generation
            system_prompt = self._build_system_prompt(request)
            user_prompt = self._build_user_prompt(request)

            # Generate with gpt-oss-20b
            terraform_code = await self.engine.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Low temperature for precise code generation
            )

            # Generate variables and outputs
            variables_file = await self._generate_variables_file(request)
            outputs_file = await self._generate_outputs_file(request)

            # Validate generated code
            validation_results = await self._validate_terraform_code(terraform_code)

            # Generate security recommendations
            security_recs = await self._generate_security_recommendations(terraform_code, request)

            # Generate deployment instructions
            deploy_instructions = self._generate_deployment_instructions(request)

            return TerraformGenerationResult(
                success=True,
                terraform_code=terraform_code,
                variables_file=variables_file,
                outputs_file=outputs_file,
                validation_results=validation_results,
                security_recommendations=security_recs,
                deployment_instructions=deploy_instructions,
            )

        except Exception as e:
            logger.error(f"Terraform generation failed: {str(e)}")
            return TerraformGenerationResult(success=False, error_message=str(e))

    def _build_system_prompt(self, request: TerraformGenerationRequest) -> str:
        """Build system prompt for AI generation"""

        return f"""You are an expert DevOps engineer and Terraform specialist.

Your task is to generate production-ready Terraform code for {request.provider.value.upper()}.

REQUIREMENTS:
- Generate secure, scalable, and cost-optimized infrastructure
- Follow Terraform best practices and {request.provider.value.upper()} recommendations
- Include proper resource naming and tagging
- Add security groups, IAM roles, and encryption where appropriate
- Include monitoring and logging setup
- Use variables for all configurable values
- Add comments explaining complex configurations
- Environment: {request.environment}
- Security level: {request.security_level}

CONSTRAINTS:
- Use only official {request.provider.value.upper()} provider resources
- Follow infrastructure as code best practices
- Include data sources where beneficial
- Add locals for computed values
- Ensure resources have proper dependencies

OUTPUT FORMAT:
Return ONLY valid Terraform (.tf) code without markdown formatting.
Do not include explanations before or after the code."""

    def _build_user_prompt(self, request: TerraformGenerationRequest) -> str:
        """Build user prompt with specific requirements"""

        prompt_parts = [
            f"Generate Terraform code for: {request.description}",
            f"Provider: {request.provider.value.upper()}",
            f"Infrastructure type: {request.infra_type.value}",
            f"Environment: {request.environment}",
        ]

        if request.region:
            prompt_parts.append(f"Region: {request.region}")

        if request.budget_range:
            prompt_parts.append(f"Budget range: {request.budget_range}")

        if request.requirements:
            req_text = ", ".join([f"{k}: {v}" for k, v in request.requirements.items()])
            prompt_parts.append(f"Additional requirements: {req_text}")

        # Add infrastructure-specific requirements
        if request.infra_type == InfrastructureType.WEB_APP_3_TIER:
            prompt_parts.append("Include: Web servers, application servers, database, load balancer, auto-scaling")
        elif request.infra_type == InfrastructureType.MICROSERVICES:
            prompt_parts.append("Include: Container orchestration, service mesh, API gateway, monitoring")
        elif request.infra_type == InfrastructureType.KUBERNETES_CLUSTER:
            prompt_parts.append("Include: Control plane, worker nodes, networking, storage, monitoring")

        return "\n".join(prompt_parts)

    async def _generate_variables_file(self, request: TerraformGenerationRequest) -> str:
        """Generate variables.tf file"""

        provider_template = self.provider_templates.get(request.provider.value, {})
        base_variables = provider_template.get("variables", "")

        # AI enhancement for specific variables
        system_prompt = """Generate additional Terraform variables for the infrastructure.
        Focus on configurability, security, and best practices.
        Return only valid Terraform variable blocks."""

        user_prompt = f"""Add specific variables for {request.infra_type.value} infrastructure.
        Include variables for: sizing, networking, security, backup, monitoring.
        Provider: {request.provider.value}"""

        additional_vars = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

        return f"{base_variables}\n\n{additional_vars}"

    async def _generate_outputs_file(self, request: TerraformGenerationRequest) -> str:
        """Generate outputs.tf file"""

        system_prompt = """Generate useful Terraform outputs for infrastructure monitoring and integration.
        Include endpoints, IDs, ARNs, and connection information.
        Return only valid Terraform output blocks."""

        user_prompt = f"""Generate outputs for {request.infra_type.value} on {request.provider.value}.
        Include: resource IDs, endpoints, connection strings, monitoring URLs."""

        outputs = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

        provider_template = self.provider_templates.get(request.provider.value, {})
        base_outputs = provider_template.get("outputs", "")

        return f"{base_outputs}\n\n{outputs}"

    async def _write_temp_terraform_file(self, code: str) -> str:
        """Write Terraform code to temporary file using async API"""
        import aiofiles.tempfile

        async with aiofiles.tempfile.NamedTemporaryFile(mode="w", suffix=".tf", delete=False) as tf_file:
            await tf_file.write(code)
            return tf_file.name

    def _check_basic_syntax(self, code: str) -> List[str]:
        """Check basic Terraform syntax"""
        results = []

        if 'resource "' in code and "{" in code:
            results.append("✅ Basic Terraform syntax appears valid")
        else:
            results.append("❌ Invalid Terraform syntax detected")

        return results

    def _check_best_practices(self, code: str) -> List[str]:
        """Check Terraform best practices"""
        results = []

        if "terraform {" in code:
            results.append("✅ Terraform block present")
        else:
            results.append("⚠️  Missing terraform block with required_providers")

        if "variable " in code:
            results.append("✅ Variables defined")
        else:
            results.append("⚠️  No variables defined")

        if "output " in code:
            results.append("✅ Outputs defined")
        else:
            results.append("⚠️  No outputs defined")

        return results

    def _check_security_patterns(self, code: str) -> List[str]:
        """Check security patterns in Terraform code"""
        results = []

        if any(keyword in code.lower() for keyword in ["encryption", "kms", "ssl", "tls"]):
            results.append("✅ Security features detected")
        else:
            results.append("⚠️  Consider adding encryption/security features")

        return results

    async def _run_terraform_validation(self, code: str) -> List[str]:
        """Run terraform validate command"""
        results = []

        try:
            # Create temporary directory with terraform files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Write main file
                (temp_path / "main.tf").write_text(code)

                # Try terraform init and validate
                init_result = await self.command_executor.execute_async(
                    command=f"cd {temp_dir} && terraform init -backend=false",
                    timeout=60,
                    safety_level=SafetyLevel.LOW,
                )

                if init_result.success:
                    validate_result = await self.command_executor.execute_async(
                        command=f"cd {temp_dir} && terraform validate",
                        timeout=30,
                        safety_level=SafetyLevel.LOW,
                    )

                    if validate_result.success:
                        results.append("✅ Terraform validate passed")
                    else:
                        results.append(f"❌ Terraform validate failed: {validate_result.stderr}")
                else:
                    results.append("⚠️  Terraform not available for validation")

        except Exception as e:
            results.append(f"⚠️  Terraform validation error: {str(e)}")

        return results

    def _cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

    async def _validate_terraform_code(self, terraform_code: str) -> List[str]:
        """Validate Terraform code syntax and best practices"""

        validation_results = []
        temp_files = []

        try:
            # Write code to temporary file using async API
            tf_file_path = await self._write_temp_terraform_file(terraform_code)
            temp_files.append(tf_file_path)

            # Perform validations using helper functions
            validation_results.extend(self._check_basic_syntax(terraform_code))
            validation_results.extend(self._check_best_practices(terraform_code))
            validation_results.extend(self._check_security_patterns(terraform_code))

            # Run terraform validation
            terraform_results = await self._run_terraform_validation(terraform_code)
            validation_results.extend(terraform_results)

        except Exception as e:
            validation_results.append(f"❌ Validation error: {str(e)}")
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_files)

        return validation_results

    async def _generate_security_recommendations(self, terraform_code: str, request: TerraformGenerationRequest) -> List[str]:
        """Generate security recommendations for the generated code"""

        system_prompt = """You are a cloud security expert specializing in Infrastructure as Code.
        Analyze the provided Terraform code and provide specific security recommendations.

        Focus on:
        - Encryption at rest and in transit
        - Network security and segmentation
        - Access controls and IAM
        - Monitoring and logging
        - Compliance considerations
        - Resource-specific security configurations

        Return a list of specific, actionable security recommendations."""

        user_prompt = f"""Analyze this Terraform code for security improvements:

        ```terraform
        {terraform_code[:3000]}  # Limit for prompt size
        ```

        Provider: {request.provider.value}
        Environment: {request.environment}
        Security level required: {request.security_level}

        Provide specific security recommendations as a numbered list."""

        try:
            recommendations_text = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.2)

            # Parse recommendations into list
            recommendations = []
            for line in recommendations_text.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                    # Clean up formatting
                    clean_line = line.lstrip("0123456789.-* ").strip()
                    if clean_line:
                        recommendations.append(clean_line)

            return recommendations[:10]  # Limit to top 10 recommendations

        except Exception as e:
            logger.error(f"Security recommendations generation failed: {str(e)}")
            return ["Security analysis unavailable due to error"]

    def _generate_deployment_instructions(self, request: TerraformGenerationRequest) -> List[str]:
        """Generate step-by-step deployment instructions"""

        base_instructions = [
            "1. Review and customize variables in variables.tf",
            "2. Initialize Terraform: terraform init",
            "3. Plan deployment: terraform plan -out=tfplan",
            "4. Review planned changes carefully",
            "5. Apply changes: terraform apply tfplan",
            "6. Verify deployment and test connectivity",
            "7. Document important outputs and endpoints",
        ]

        # Add provider-specific instructions
        if request.provider == CloudProvider.AWS:
            aws_instructions = [
                "0. Configure AWS credentials: aws configure",
                "0. Verify AWS CLI access: aws sts get-caller-identity",
            ]
            base_instructions = aws_instructions + base_instructions

        elif request.provider == CloudProvider.AZURE:
            azure_instructions = [
                "0. Login to Azure: az login",
                "0. Set subscription: az account set --subscription <subscription-id>",
            ]
            base_instructions = azure_instructions + base_instructions

        elif request.provider == CloudProvider.GCP:
            gcp_instructions = [
                "0. Authenticate with GCP: gcloud auth login",
                "0. Set project: gcloud config set project <project-id>",
            ]
            base_instructions = gcp_instructions + base_instructions

        return base_instructions

    async def generate_aws_3_tier_app(
        self,
        app_name: str = "webapp",
        database_engine: str = "mysql",
        instance_type: str = "t3.medium",
    ) -> TerraformGenerationResult:
        """Generate AWS 3-tier web application infrastructure"""

        request = TerraformGenerationRequest(
            description=f"3-tier web application with {database_engine} database",
            provider=CloudProvider.AWS,
            infra_type=InfrastructureType.WEB_APP_3_TIER,
            requirements={
                "app_name": app_name,
                "database_engine": database_engine,
                "instance_type": instance_type,
                "auto_scaling": True,
                "load_balancer": True,
                "monitoring": True,
            },
        )

        return await self.generate_infrastructure(request)

    async def generate_kubernetes_cluster(self, cluster_name: str = "k8s-cluster", node_count: int = 3, node_type: str = "t3.medium") -> TerraformGenerationResult:
        """Generate Kubernetes cluster infrastructure"""

        request = TerraformGenerationRequest(
            description=f"Kubernetes cluster with {node_count} nodes",
            provider=CloudProvider.AWS,  # Default to AWS, can be parameterized
            infra_type=InfrastructureType.KUBERNETES_CLUSTER,
            requirements={
                "cluster_name": cluster_name,
                "node_count": node_count,
                "node_type": node_type,
                "networking": "vpc-native",
                "addons": ["monitoring", "logging", "auto-scaler"],
            },
        )

        return await self.generate_infrastructure(request)

    async def generate_from_description(self, description: str, provider: str = "aws", **kwargs) -> TerraformGenerationResult:
        """Generate infrastructure from natural language description"""

        # Determine infrastructure type from description
        infra_type = self._infer_infrastructure_type(description)

        # Parse provider
        try:
            cloud_provider = CloudProvider(provider.lower())
        except ValueError:
            cloud_provider = CloudProvider.AWS

        request = TerraformGenerationRequest(
            description=description,
            provider=cloud_provider,
            infra_type=infra_type,
            requirements=kwargs,
        )

        return await self.generate_infrastructure(request)

    def _infer_infrastructure_type(self, description: str) -> InfrastructureType:
        """Infer infrastructure type from description"""

        description_lower = description.lower()

        if any(keyword in description_lower for keyword in ["3-tier", "web app", "webapp", "website"]):
            return InfrastructureType.WEB_APP_3_TIER
        elif any(keyword in description_lower for keyword in ["microservice", "api", "service mesh"]):
            return InfrastructureType.MICROSERVICES
        elif any(keyword in description_lower for keyword in ["database", "db", "postgres", "mysql", "mongodb"]):
            return InfrastructureType.DATABASE_CLUSTER
        elif any(keyword in description_lower for keyword in ["kubernetes", "k8s", "container", "orchestration"]):
            return InfrastructureType.KUBERNETES_CLUSTER
        elif any(keyword in description_lower for keyword in ["monitoring", "observability", "metrics", "prometheus"]):
            return InfrastructureType.MONITORING_STACK
        elif any(keyword in description_lower for keyword in ["ci/cd", "pipeline", "build", "deploy"]):
            return InfrastructureType.CI_CD_PIPELINE
        elif any(keyword in description_lower for keyword in ["load balancer", "lb", "traffic"]):
            return InfrastructureType.LOAD_BALANCER
        elif any(keyword in description_lower for keyword in ["storage", "file system", "backup"]):
            return InfrastructureType.STORAGE_SOLUTION
        else:
            return InfrastructureType.WEB_APP_3_TIER  # Default fallback

    async def validate_existing_terraform(self, file_path: str) -> List[str]:
        """Validate existing Terraform files"""

        try:
            # Read the terraform file
            terraform_code = Path(file_path).read_text()

            # Use existing validation logic
            return await self._validate_terraform_code(terraform_code)

        except Exception as e:
            return [f"❌ Error reading file {file_path}: {str(e)}"]

    async def enhance_existing_terraform(self, file_path: str, enhancement_request: str) -> TerraformGenerationResult:
        """Enhance existing Terraform code with AI"""

        try:
            # Read existing code
            existing_code = Path(file_path).read_text()

            system_prompt = """You are an expert Terraform engineer.
            Enhance the provided Terraform code based on the user's requirements.
            Maintain existing resource configurations while adding improvements.
            Return the complete enhanced Terraform code."""

            user_prompt = f"""Enhance this Terraform code:

            ```terraform
            {existing_code}
            ```

            Enhancement request: {enhancement_request}

            Maintain all existing resources and add the requested enhancements."""

            enhanced_code = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Validate enhanced code
            validation_results = await self._validate_terraform_code(enhanced_code)

            return TerraformGenerationResult(
                success=True,
                terraform_code=enhanced_code,
                validation_results=validation_results,
                deployment_instructions=[
                    "1. Backup existing terraform.tfstate",
                    "2. Review changes with terraform plan",
                    "3. Apply enhancements gradually",
                    "4. Test functionality after each change",
                ],
            )

        except Exception as e:
            logger.error(f"Terraform enhancement failed: {str(e)}")
            return TerraformGenerationResult(success=False, error_message=str(e))


# Convenience functions for CLI usage
async def quick_generate_aws_webapp() -> TerraformGenerationResult:
    """Quick AWS web app generation"""
    generator = TerraformGenerator()
    return await generator.generate_aws_3_tier_app()


async def quick_generate_k8s_cluster(nodes: int = 3) -> TerraformGenerationResult:
    """Quick Kubernetes cluster generation"""
    generator = TerraformGenerator()
    return await generator.generate_kubernetes_cluster(node_count=nodes)


async def generate_from_natural_language(description: str, provider: str = "aws") -> TerraformGenerationResult:
    """Generate infrastructure from natural language"""
    generator = TerraformGenerator()
    return await generator.generate_from_description(description, provider)
