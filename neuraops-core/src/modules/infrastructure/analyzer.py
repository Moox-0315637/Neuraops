"""
NeuraOps Infrastructure Analysis Module
Advanced analysis tools for cost optimization, security scanning, compliance, and performance recommendations
"""

import asyncio
import logging
import json
import re
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from ...core.command_executor import CommandExecutor, SafetyLevel
from ...core.structured_output import AnalysisResult, SeverityLevel
from ...devops_commander.exceptions import AnalysisError

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of infrastructure analysis"""

    COST_OPTIMIZATION = "cost_optimization"
    SECURITY_SCANNING = "security_scanning"
    COMPLIANCE_CHECK = "compliance_check"
    PERFORMANCE_ANALYSIS = "performance_analysis"


@dataclass
class AnalysisFinding:
    """Finding from infrastructure analysis"""

    finding_id: str
    analysis_type: AnalysisType
    severity: SeverityLevel
    title: str
    description: str
    impact: str
    recommendation: str
    resource_id: str
    metadata: Dict[str, Any]
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CostSavingOpportunity:
    """Cost saving opportunity"""

    resource_id: str
    resource_type: str
    current_cost: float
    potential_savings: float
    savings_percentage: float
    optimization_type: str
    implementation_effort: str
    description: str


class InfrastructureAnalyzer:
    """Analyze infrastructure for optimizations and compliance"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.findings_history: List[AnalysisFinding] = []

    async def analyze_cost_optimization(self, include_cloud: bool = True) -> List[CostSavingOpportunity]:
        """Analyze infrastructure for cost optimization opportunities"""

        opportunities = []

        try:
            # Analyze Kubernetes resources
            k8s_opportunities = await self._analyze_k8s_cost_optimization()
            opportunities.extend(k8s_opportunities)

            # Analyze Docker containers
            docker_opportunities = await self._analyze_docker_cost_optimization()
            opportunities.extend(docker_opportunities)

            # Analyze cloud resources if enabled
            if include_cloud:
                cloud_opportunities = await self._analyze_cloud_cost_optimization()
                opportunities.extend(cloud_opportunities)

            return opportunities

        except Exception as e:
            raise AnalysisError(f"Cost optimization analysis failed: {str(e)}") from e

    async def _get_k8s_pods_info(self) -> Dict[str, Any]:
        """Get Kubernetes pods information"""
        try:
            cmd = "kubectl top pods --all-namespaces --no-headers"
            result = await self.command_executor.execute_async(command=cmd, timeout=30, safety_level=SafetyLevel.LOW)
            return {"success": result.success, "stdout": result.stdout if result.success else ""}
        except Exception as e:
            logger.error(f"Failed to get K8s pods info: {str(e)}")
            return {"success": False, "stdout": ""}

    def _parse_pod_resources(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse pod resource information from kubectl output"""
        underutilized_pods = []

        for line in stdout.strip().split("\n"):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    namespace = parts[0]
                    pod_name = parts[1]
                    cpu_usage = parts[2]
                    memory_usage = parts[3]

                    # Convert CPU usage (remove 'm' suffix and convert to percentage)
                    cpu_value = 0
                    if "m" in cpu_usage:
                        cpu_value = float(cpu_usage.replace("m", "")) / 10

                    # If CPU usage is very low, consider it underutilized
                    if cpu_value < 5:  # Less than 5% CPU
                        underutilized_pods.append({"pod": pod_name, "namespace": namespace, "cpu_usage": cpu_value, "memory_usage": memory_usage})

        return underutilized_pods

    def _create_k8s_cost_opportunities(self, underutilized_pods: List[Dict[str, Any]]) -> List[CostSavingOpportunity]:
        """Create cost saving opportunities from underutilized pods"""
        opportunities = []

        for pod_info in underutilized_pods[:10]:  # Limit to top 10
            opportunities.append(
                CostSavingOpportunity(
                    resource_id=f"{pod_info['namespace']}/{pod_info['pod']}",
                    resource_type="kubernetes_pod",
                    current_cost=50.0,  # Estimated monthly cost
                    potential_savings=15.0,  # Estimated savings
                    savings_percentage=30.0,
                    optimization_type="resource_rightsizing",
                    implementation_effort="low",
                    description=f"Pod '{pod_info['pod']}' shows low CPU utilization ({pod_info['cpu_usage']:.1f}%)",
                )
            )

        return opportunities

    async def _analyze_k8s_cost_optimization(self) -> List[CostSavingOpportunity]:
        """Analyze Kubernetes resources for cost optimization"""

        try:
            # Get Kubernetes pods information
            pods_info = await self._get_k8s_pods_info()

            if not pods_info["success"] or not pods_info["stdout"]:
                return []

            # Parse pod resource information
            underutilized_pods = self._parse_pod_resources(pods_info["stdout"])

            # Create cost saving opportunities
            opportunities = self._create_k8s_cost_opportunities(underutilized_pods)

            return opportunities

        except Exception as e:
            logger.error(f"K8s cost analysis failed: {str(e)}")
            return []

    async def _get_docker_containers_info(self) -> Dict[str, Any]:
        """Get Docker containers information"""
        try:
            cmd = "docker stats --no-stream --format 'table {{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}'"
            result = await self.command_executor.execute_async(command=cmd, timeout=30, safety_level=SafetyLevel.LOW)
            return {"success": result.success, "stdout": result.stdout if result.success else ""}
        except Exception as e:
            logger.error(f"Failed to get Docker containers info: {str(e)}")
            return {"success": False, "stdout": ""}

    def _parse_container_resources(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse container resource information from docker stats output"""
        underutilized_containers = []
        lines = stdout.strip().split("\n")[1:]  # Skip header

        for line in lines:
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 3:
                    container_name = parts[0]
                    cpu_percent = float(parts[1].replace("%", ""))

                    # Check for underutilization
                    if cpu_percent < 5:  # Less than 5% CPU
                        underutilized_containers.append({"container": container_name, "cpu_percent": cpu_percent})

        return underutilized_containers

    def _create_docker_cost_opportunities(self, underutilized_containers: List[Dict[str, Any]]) -> List[CostSavingOpportunity]:
        """Create cost saving opportunities from underutilized containers"""
        opportunities = []

        for container_info in underutilized_containers:
            opportunities.append(
                CostSavingOpportunity(
                    resource_id=container_info["container"],
                    resource_type="docker_container",
                    current_cost=25.0,  # Estimated monthly cost
                    potential_savings=10.0,
                    savings_percentage=40.0,
                    optimization_type="container_rightsizing",
                    implementation_effort="medium",
                    description=f"Container '{container_info['container']}' shows low CPU utilization ({container_info['cpu_percent']:.1f}%)",
                )
            )

        return opportunities

    async def _analyze_docker_cost_optimization(self) -> List[CostSavingOpportunity]:
        """Analyze Docker containers for cost optimization"""

        try:
            # Get Docker containers information
            containers_info = await self._get_docker_containers_info()

            if not containers_info["success"] or not containers_info["stdout"]:
                return []

            # Parse container resource information
            underutilized_containers = self._parse_container_resources(containers_info["stdout"])

            # Create cost saving opportunities
            opportunities = self._create_docker_cost_opportunities(underutilized_containers)

            return opportunities

        except Exception as e:
            logger.error(f"Docker cost analysis failed: {str(e)}")
            return []

    async def _get_cloud_instances_info(self) -> Dict[str, Any]:
        """Get cloud instances information"""
        try:
            aws_cmd = "aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,State:State.Name}' --output json"
            result = await self.command_executor.execute_async(command=aws_cmd, timeout=30, safety_level=SafetyLevel.LOW)
            return {"success": result.success, "stdout": result.stdout if result.success else ""}
        except Exception as e:
            logger.error(f"Failed to get cloud instances info: {str(e)}")
            return {"success": False, "stdout": ""}

    def _parse_cloud_instances(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse cloud instances information from AWS CLI output"""
        running_instances = []

        try:
            instances = json.loads(stdout)
            for reservation in instances:
                for instance in reservation:
                    if instance.get("State") == "running":
                        instance_type = instance.get("Type", "")
                        instance_id = instance.get("ID", "")

                        if instance_type and instance_id:
                            running_instances.append({"instance_id": instance_id, "instance_type": instance_type})
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AWS output: {str(e)}")

        return running_instances

    def _create_cloud_cost_opportunities(self, instances: List[Dict[str, Any]]) -> List[CostSavingOpportunity]:
        """Create cost saving opportunities from cloud instances"""
        opportunities = []

        # For demo purposes, create sample opportunities
        for instance in instances[:5]:  # Limit to first 5 instances
            opportunities.append(
                CostSavingOpportunity(
                    resource_id=instance["instance_id"],
                    resource_type="aws_ec2_instance",
                    current_cost=100.0,  # Estimated monthly cost
                    potential_savings=30.0,
                    savings_percentage=30.0,
                    optimization_type="instance_rightsizing",
                    implementation_effort="high",
                    description=f"EC2 instance {instance['instance_id']} ({instance['instance_type']}) may be oversized",
                )
            )

        return opportunities

    async def _analyze_cloud_cost_optimization(self) -> List[CostSavingOpportunity]:
        """Analyze cloud resources for cost optimization"""

        try:
            # Get cloud instances information
            cloud_info = await self._get_cloud_instances_info()

            if not cloud_info["success"] or not cloud_info["stdout"]:
                return []

            # Parse cloud instances information
            running_instances = self._parse_cloud_instances(cloud_info["stdout"])

            # Create cost saving opportunities
            opportunities = self._create_cloud_cost_opportunities(running_instances)

            return opportunities

        except Exception as e:
            logger.error(f"Cloud cost analysis failed: {str(e)}")
            return []


# End of ResourceAnalyzer class
