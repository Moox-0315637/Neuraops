"""
NeuraOps Kubernetes Generator Module
AI-powered Kubernetes manifest generation with gpt-oss-20b
YAML generation, security contexts, resource management
"""

import json
import logging
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from ...core.engine import DevOpsEngine
from ...core.structured_output import (
    DevOpsCommand,
)
from ...core.command_executor import CommandExecutor, SafetyLevel
from ...devops_commander.config import NeuraOpsConfig
from ...devops_commander.exceptions import InfrastructureError

logger = logging.getLogger(__name__)

# Constants pour éviter duplication de chaînes
DEFAULT_NGINX_IMAGE = "nginx:latest"


class KubernetesResourceType(Enum):
    """Types of Kubernetes resources"""

    DEPLOYMENT = "Deployment"
    SERVICE = "Service"
    INGRESS = "Ingress"
    CONFIGMAP = "ConfigMap"
    SECRET = "Secret"
    PERSISTENT_VOLUME = "PersistentVolume"
    PERSISTENT_VOLUME_CLAIM = "PersistentVolumeClaim"
    NAMESPACE = "Namespace"
    SERVICE_ACCOUNT = "ServiceAccount"
    ROLE = "Role"
    ROLE_BINDING = "RoleBinding"
    NETWORK_POLICY = "NetworkPolicy"
    HORIZONTAL_POD_AUTOSCALER = "HorizontalPodAutoscaler"
    STATEFUL_SET = "StatefulSet"
    DAEMON_SET = "DaemonSet"
    JOB = "Job"
    CRON_JOB = "CronJob"


class DeploymentStrategy(Enum):
    """Kubernetes deployment strategies"""

    ROLLING_UPDATE = "RollingUpdate"
    RECREATE = "Recreate"


@dataclass
class KubernetesGenerationRequest:
    """Request for Kubernetes manifest generation"""

    app_name: str
    namespace: str = "default"
    image: str = DEFAULT_NGINX_IMAGE
    replicas: int = 3
    resources: Dict[str, Any] = field(default_factory=dict)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    service_type: str = "ClusterIP"  # ClusterIP, NodePort, LoadBalancer
    enable_ingress: bool = False
    storage_requirements: Optional[Dict[str, Any]] = None
    security_context: Dict[str, Any] = field(default_factory=dict)
    monitoring: bool = True
    auto_scaling: bool = False
    network_policies: bool = False


@dataclass
class KubernetesGenerationResult:
    """Result of Kubernetes generation"""

    success: bool
    manifests: Dict[str, str] = field(default_factory=dict)  # resource_type -> YAML content
    validation_results: List[str] = field(default_factory=list)
    security_recommendations: List[str] = field(default_factory=list)
    deployment_order: List[str] = field(default_factory=list)
    kubectl_commands: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class KubernetesGenerator:
    """AI-powered Kubernetes manifest generator with gpt-oss-20b"""

    def __init__(self, config: Optional[NeuraOpsConfig] = None):
        self.config = config or NeuraOpsConfig()
        self.engine = DevOpsEngine(config=self.config.ollama)
        # output_manager removed - not essential for core functionality
        self.command_executor = CommandExecutor(config=self.config.security)

        # Default resource templates
        self.resource_templates = self._load_resource_templates()

    def _load_resource_templates(self) -> Dict[str, str]:
        """Load Kubernetes resource templates"""
        return {
            "deployment": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
    managed-by: neuraops
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
      - name: {app_name}
        image: {image}
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL""",
            "service": """apiVersion: v1
kind: Service
metadata:
  name: {app_name}-service
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  selector:
    app: {app_name}
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
  type: {service_type}""",
            "namespace": """apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    managed-by: neuraops
    security-policy: restricted""",
        }

    async def generate_application_manifests(self, request: KubernetesGenerationRequest) -> KubernetesGenerationResult:
        """Generate complete application manifests"""

        try:
            logger.info(f"Generating Kubernetes manifests for {request.app_name}")

            manifests = {}

            # Generate core resources
            manifests["namespace"] = self._generate_namespace(request)
            manifests["deployment"] = await self._generate_deployment(request)
            manifests["service"] = await self._generate_service(request)

            # Generate optional resources
            if request.enable_ingress:
                manifests["ingress"] = await self._generate_ingress(request)

            if request.storage_requirements:
                manifests["pvc"] = self._generate_persistent_volume_claim(request)

            if request.auto_scaling:
                manifests["hpa"] = self._generate_horizontal_pod_autoscaler(request)

            if request.network_policies:
                manifests["network-policy"] = self._generate_network_policy(request)

            # Generate ConfigMap and Secret if environment variables
            if request.environment_vars:
                manifests["configmap"] = self._generate_configmap(request)

            # Validate all manifests
            validation_results = self._validate_manifests(manifests)

            # Generate security recommendations
            security_recs = await self._generate_security_recommendations(manifests, request)

            # Generate deployment order and kubectl commands
            deployment_order = self._generate_deployment_order(manifests)
            kubectl_commands = self._generate_kubectl_commands(manifests, request.namespace)

            return KubernetesGenerationResult(
                success=True,
                manifests=manifests,
                validation_results=validation_results,
                security_recommendations=security_recs,
                deployment_order=deployment_order,
                kubectl_commands=kubectl_commands,
            )

        except Exception as e:
            logger.error(f"Kubernetes generation failed: {str(e)}")
            return KubernetesGenerationResult(success=False, error_message=str(e))

    async def _generate_deployment(self, request: KubernetesGenerationRequest) -> str:
        """Generate Deployment manifest with AI enhancement"""

        system_prompt = """You are a Kubernetes expert specializing in secure, production-ready deployments.
        Generate a Kubernetes Deployment YAML manifest with best practices:

        - Security contexts (non-root, read-only filesystem)
        - Resource limits and requests
        - Proper labels and selectors
        - Health checks (readiness/liveness probes)
        - Security policies
        - Image pull policies

        Return only valid YAML without markdown formatting."""

        user_prompt = f"""Generate Kubernetes Deployment for:
        - App name: {request.app_name}
        - Namespace: {request.namespace}
        - Image: {request.image}
        - Replicas: {request.replicas}
        - Environment variables: {request.environment_vars}
        - Resource requirements: {request.resources}

        Include proper security context and resource management."""

        try:
            deployment_yaml = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Ensure YAML validity
            try:
                yaml.safe_load(deployment_yaml)
                return deployment_yaml
            except yaml.YAMLError as e:
                logger.warning(f"Generated YAML invalid, using template: {str(e)}")
                # Fallback to template with substitution
                template = self.resource_templates["deployment"]
                return template.format(
                    app_name=request.app_name,
                    namespace=request.namespace,
                    image=request.image,
                    replicas=request.replicas,
                )

        except Exception as e:
            logger.error(f"Deployment generation failed: {str(e)}")
            # Emergency fallback
            template = self.resource_templates["deployment"]
            return template.format(
                app_name=request.app_name,
                namespace=request.namespace,
                image=request.image,
                replicas=request.replicas,
            )

    async def _generate_service(self, request: KubernetesGenerationRequest) -> str:
        """Generate Service manifest"""

        system_prompt = """Generate a Kubernetes Service YAML manifest.
        Include proper port configuration, service type, and selectors.
        Return only valid YAML."""

        user_prompt = f"""Generate Kubernetes Service for:
        - App: {request.app_name}
        - Namespace: {request.namespace}
        - Service type: {request.service_type}

        Configure appropriate ports and selectors."""

        try:
            service_yaml = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Validate YAML
            yaml.safe_load(service_yaml)
            return service_yaml

        except Exception as e:
            logger.warning(f"Service generation failed, using template: {str(e)}")
            template = self.resource_templates["service"]
            return template.format(
                app_name=request.app_name,
                namespace=request.namespace,
                service_type=request.service_type,
            )

    def _generate_namespace(self, request: KubernetesGenerationRequest) -> str:
        """Generate Namespace manifest"""

        if request.namespace == "default":
            return "# Using default namespace"

        template = self.resource_templates["namespace"]
        return template.format(namespace=request.namespace)

    async def _generate_ingress(self, request: KubernetesGenerationRequest) -> str:
        """Generate Ingress manifest"""

        system_prompt = """Generate a Kubernetes Ingress YAML manifest.
        Include TLS configuration, proper annotations, and routing rules.
        Return only valid YAML."""

        user_prompt = f"""Generate Kubernetes Ingress for:
        - App: {request.app_name}
        - Namespace: {request.namespace}
        - Service: {request.app_name}-service

        Include TLS and NGINX ingress controller annotations."""

        ingress_yaml = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

        return ingress_yaml

    def _generate_persistent_volume_claim(self, request: KubernetesGenerationRequest) -> str:
        """Generate PersistentVolumeClaim manifest"""

        storage_size = request.storage_requirements.get("size", "10Gi")
        access_mode = request.storage_requirements.get("access_mode", "ReadWriteOnce")
        storage_class = request.storage_requirements.get("storage_class", "gp2")

        pvc_yaml = f"""apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {request.app_name}-pvc
  namespace: {request.namespace}
  labels:
    app: {request.app_name}
spec:
  accessModes:
    - {access_mode}
  storageClassName: {storage_class}
  resources:
    requests:
      storage: {storage_size}"""

        return pvc_yaml

    def _generate_horizontal_pod_autoscaler(self, request: KubernetesGenerationRequest) -> str:
        """Generate HorizontalPodAutoscaler manifest"""

        hpa_yaml = f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {request.app_name}-hpa
  namespace: {request.namespace}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {request.app_name}
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80"""

        return hpa_yaml

    def _generate_configmap(self, request: KubernetesGenerationRequest) -> str:
        """Generate ConfigMap manifest"""

        config_data = "\n".join([f'  {k}: "{v}"' for k, v in request.environment_vars.items()])

        configmap_yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {request.app_name}-config
  namespace: {request.namespace}
  labels:
    app: {request.app_name}
data:
{config_data}"""

        return configmap_yaml

    def _generate_network_policy(self, request: KubernetesGenerationRequest) -> str:
        """Generate NetworkPolicy manifest"""

        network_policy_yaml = f"""apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {request.app_name}-network-policy
  namespace: {request.namespace}
spec:
  podSelector:
    matchLabels:
      app: {request.app_name}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: {request.namespace}
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS"""

        return network_policy_yaml

    def _validate_manifests(self, manifests: Dict[str, str]) -> List[str]:
        """Validate Kubernetes manifests"""
        validation_results = []

        for resource_type, yaml_content in manifests.items():
            try:
                # Parse YAML
                yaml_obj = yaml.safe_load(yaml_content)

                if yaml_obj:
                    # Basic structure validation
                    structure_result = self._validate_yaml_structure(yaml_obj, resource_type)
                    validation_results.extend(structure_result)

                    # Metadata validation
                    metadata_result = self._validate_metadata(yaml_obj, resource_type)
                    validation_results.extend(metadata_result)
                else:
                    validation_results.append(f"❌ {resource_type}: Empty or invalid YAML")

                # Try kubectl dry-run validation if available
                kubectl_result = self._validate_with_kubectl(yaml_content, resource_type)
                validation_results.extend(kubectl_result)

            except yaml.YAMLError as e:
                validation_results.append(f"❌ {resource_type}: YAML parsing error: {str(e)}")
            except Exception as e:
                validation_results.append(f"❌ {resource_type}: Validation error: {str(e)}")

        return validation_results

    def _validate_yaml_structure(self, yaml_obj: dict, resource_type: str) -> List[str]:
        """Validate basic YAML structure"""
        results = []

        if "apiVersion" in yaml_obj and "kind" in yaml_obj and "metadata" in yaml_obj:
            results.append(f"✅ {resource_type}: Valid YAML structure")
        else:
            results.append(f"❌ {resource_type}: Invalid Kubernetes manifest structure")

        return results

    def _validate_metadata(self, yaml_obj: dict, resource_type: str) -> List[str]:
        """Validate metadata fields"""
        results = []
        metadata = yaml_obj.get("metadata", {})

        # Check for required name
        if "name" in metadata:
            results.append(f"✅ {resource_type}: Has required name")
        else:
            results.append(f"❌ {resource_type}: Missing name in metadata")

        # Check for labels
        if "labels" in metadata:
            results.append(f"✅ {resource_type}: Has labels")
        else:
            results.append(f"⚠️  {resource_type}: Consider adding labels")

        return results

    def _validate_with_kubectl(self, yaml_content: str, resource_type: str) -> List[str]:
        """Validate with kubectl if available"""
        results = []

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
                temp_file.write(yaml_content)
                temp_file_path = temp_file.name

            # kubectl dry-run validation
            validate_cmd = f"kubectl apply --dry-run=client -f {temp_file_path}"
            validate_result = self.command_executor.execute_sync(command=validate_cmd, timeout=30, safety_level=SafetyLevel.LOW)

            if validate_result.success:
                results.append(f"✅ {resource_type}: kubectl validation passed")
            else:
                results.append(f"⚠️  {resource_type}: kubectl validation: {validate_result.stderr[:100]}")

            # Cleanup
            self._cleanup_temp_file(temp_file_path)

        except Exception:
            results.append(f"⚠️  {resource_type}: kubectl validation unavailable")

        return results

    def _cleanup_temp_file(self, file_path: str) -> None:
        """Clean up temporary file"""
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass  # Ignore cleanup errors

    async def _generate_security_recommendations(self, manifests: Dict[str, str], request: KubernetesGenerationRequest) -> List[str]:
        """Generate security recommendations for manifests"""

        system_prompt = """You are a Kubernetes security expert.
        Analyze the provided Kubernetes manifests and provide specific security recommendations.

        Focus on:
        - Pod security standards and contexts
        - Network segmentation and policies
        - RBAC and service accounts
        - Resource limits and quotas
        - Image security and scanning
        - Secrets management
        - Compliance considerations

        Return specific, actionable recommendations as a numbered list."""

        # Combine manifests for analysis (limit size)
        manifests_text = "\n---\n".join(list(manifests.values())[:3])  # Limit to avoid token limits

        user_prompt = f"""Analyze these Kubernetes manifests for security improvements:

        ```yaml
        {manifests_text[:2000]}  # Limit for prompt size
        ```

        Application: {request.app_name}
        Namespace: {request.namespace}
        Environment: production

        Provide specific security recommendations."""

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

            return recommendations[:8]  # Limit to top 8

        except Exception as e:
            logger.error(f"Security recommendations failed: {str(e)}")
            return ["Security analysis unavailable"]

    def _generate_deployment_order(self, manifests: Dict[str, str]) -> List[str]:
        """Generate proper deployment order for resources"""

        # Standard deployment order for dependencies
        order_priority = [
            "namespace",
            "configmap",
            "secret",
            "service-account",
            "role",
            "role-binding",
            "pvc",
            "deployment",
            "statefulset",
            "service",
            "ingress",
            "hpa",
            "network-policy",
        ]

        deployment_order = []
        for resource_type in order_priority:
            if resource_type in manifests:
                deployment_order.append(resource_type)

        # Add any remaining resources
        for resource_type in manifests:
            if resource_type not in deployment_order:
                deployment_order.append(resource_type)

        return deployment_order

    def _generate_kubectl_commands(self, manifests: Dict[str, str], namespace: str) -> List[str]:
        """Generate kubectl commands for deployment"""

        commands = []

        # Create namespace first if not default
        if namespace != "default" and "namespace" in manifests:
            commands.append("kubectl apply -f namespace.yaml")

        # Apply resources in order
        for resource_type in self._generate_deployment_order(manifests):
            if resource_type != "namespace":  # Already handled
                commands.append(f"kubectl apply -f {resource_type}.yaml -n {namespace}")

        # Add verification commands
        commands.extend(
            [
                f"kubectl get all -n {namespace}",
                f"kubectl get pods -n {namespace} -w",
                f"kubectl describe deployment -n {namespace}",
                f"kubectl logs -l app={manifests.get('deployment', {}).get('metadata', {}).get('labels', {}).get('app', 'app')} -n {namespace}",
            ]
        )

        return commands

    async def generate_from_description(self, description: str, namespace: str = "default") -> KubernetesGenerationResult:
        """Generate Kubernetes manifests from natural language description"""

        # Use AI to parse description into structured request
        system_prompt = """Parse the user's infrastructure description into specific requirements.
        Extract: app name, image, replicas, service type, resource needs, storage, security requirements.

        Return a JSON object with these fields:
        {
          "app_name": "string",
          "image": "string",
          "replicas": number,
          "service_type": "ClusterIP|NodePort|LoadBalancer",
          "enable_ingress": boolean,
          "auto_scaling": boolean,
          "storage_requirements": {"size": "string"},
          "resources": {"requests": {"cpu": "string", "memory": "string"}},
          "environment_vars": {}
        }"""

        user_prompt = f"""Parse this infrastructure description:
        "{description}"

        Extract specific requirements for Kubernetes deployment."""

        try:
            # Get structured requirements from AI
            requirements_json = await self.engine.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)

            # Parse JSON response
            requirements = json.loads(requirements_json)

            # Build request object
            request = KubernetesGenerationRequest(
                app_name=requirements.get("app_name", "myapp"),
                namespace=namespace,
                image=requirements.get("image", DEFAULT_NGINX_IMAGE),
                replicas=requirements.get("replicas", 3),
                service_type=requirements.get("service_type", "ClusterIP"),
                enable_ingress=requirements.get("enable_ingress", False),
                auto_scaling=requirements.get("auto_scaling", False),
                storage_requirements=requirements.get("storage_requirements"),
                resources=requirements.get("resources", {}),
                environment_vars=requirements.get("environment_vars", {}),
            )

            return await self.generate_application_manifests(request)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed, using defaults: {str(e)}")
            # Fallback with basic configuration
            request = KubernetesGenerationRequest(app_name="myapp", namespace=namespace, image=DEFAULT_NGINX_IMAGE)
            return await self.generate_application_manifests(request)

        except Exception as e:
            logger.error(f"Description parsing failed: {str(e)}")
            return KubernetesGenerationResult(success=False, error_message=str(e))

    async def generate_security_hardened_app(self, app_name: str, image: str, namespace: str = "secure") -> KubernetesGenerationResult:
        """Generate security-hardened application deployment"""

        request = KubernetesGenerationRequest(
            app_name=app_name,
            namespace=namespace,
            image=image,
            replicas=3,
            security_context={
                "runAsNonRoot": True,
                "runAsUser": 1000,
                "readOnlyRootFilesystem": True,
                "allowPrivilegeEscalation": False,
            },
            network_policies=True,
            monitoring=True,
            resources={
                "requests": {"cpu": "100m", "memory": "128Mi"},
                "limits": {"cpu": "500m", "memory": "512Mi"},
            },
        )

        return await self.generate_application_manifests(request)

    def save_manifests_to_files(self, result: KubernetesGenerationResult, output_dir: str = "./k8s-manifests") -> List[str]:
        """Save generated manifests to files"""

        if not result.success:
            raise InfrastructureError(f"Cannot save failed generation: {result.error_message}")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        saved_files = []

        for resource_type, yaml_content in result.manifests.items():
            file_path = output_path / f"{resource_type}.yaml"
            file_path.write_text(yaml_content)
            saved_files.append(str(file_path))
            logger.info(f"Saved {resource_type} manifest to {file_path}")

        # Save kubectl commands script
        if result.kubectl_commands:
            commands_script = "\n".join([f"echo 'Executing: {cmd}'", cmd, "echo ''"] for cmd in result.kubectl_commands)
            script_path = output_path / "deploy.sh"
            script_path.write_text(f"#!/bin/bash\nset -e\n\n{commands_script}")
            script_path.chmod(0o755)
            saved_files.append(str(script_path))

        return saved_files


# Convenience functions for CLI usage
async def quick_generate_webapp(app_name: str = "webapp", image: str = DEFAULT_NGINX_IMAGE, namespace: str = "default") -> KubernetesGenerationResult:
    """Quick web application manifests generation"""
    generator = KubernetesGenerator()

    request = KubernetesGenerationRequest(
        app_name=app_name,
        namespace=namespace,
        image=image,
        service_type="LoadBalancer",
        enable_ingress=True,
        auto_scaling=True,
    )

    return await generator.generate_application_manifests(request)


async def quick_generate_microservice(service_name: str, image: str) -> KubernetesGenerationResult:
    """Quick microservice manifests generation"""
    generator = KubernetesGenerator()

    request = KubernetesGenerationRequest(
        app_name=service_name,
        namespace="microservices",
        image=image,
        replicas=2,
        service_type="ClusterIP",
        auto_scaling=True,
        monitoring=True,
        resources={
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "1000m", "memory": "1Gi"},
        },
    )

    return await generator.generate_application_manifests(request)


async def generate_from_natural_language(description: str, namespace: str = "default") -> KubernetesGenerationResult:
    """Generate Kubernetes manifests from natural language"""
    generator = KubernetesGenerator()
    return await generator.generate_from_description(description, namespace)
