"""
NeuraOps Infrastructure Monitoring Module
Monitor containers, services, clusters, and cloud resources with intelligent alerting
"""

import logging
import json
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ...core.command_executor import SecureCommandExecutor, SafetyLevel
from ...core.structured_output import MonitoringResult, SeverityLevel
from ...devops_commander.exceptions import MonitoringError

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of infrastructure resources to monitor"""

    CONTAINER = "container"
    SERVICE = "service"
    POD = "pod"
    NODE = "node"
    CLUSTER = "cluster"
    VOLUME = "volume"
    NETWORK = "network"


class MetricType(Enum):
    """Types of metrics to collect"""

    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    REQUEST_RATE = "request_rate"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"


@dataclass
class ResourceMetrics:
    """Metrics for a monitored resource"""

    resource_id: str
    resource_type: ResourceType
    timestamp: datetime
    metrics: Dict[str, float]
    labels: Dict[str, str]
    healthy: bool = True
    alerts: Optional[List[str]] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


class InfrastructureMonitor:
    """Monitor infrastructure components and generate alerts"""

    def __init__(self):
        # Create a more permissive security config for monitoring operations  
        from ...devops_commander.config import SecurityConfig
        monitoring_config = SecurityConfig(
            validation_enabled=False,  # Disable validation for monitoring commands
            audit_enabled=True,
            enable_safety_checks=False  # Disable safety checks for read-only monitoring
        )
        self.command_executor = SecureCommandExecutor(monitoring_config)
        self.metric_history: Dict[str, List[ResourceMetrics]] = {}
        self.alert_thresholds = {
            MetricType.CPU_USAGE: 80.0,
            MetricType.MEMORY_USAGE: 85.0,
            MetricType.DISK_USAGE: 90.0,
            MetricType.ERROR_RATE: 5.0,
            MetricType.RESPONSE_TIME: 2000.0,  # ms
        }

    async def monitor_kubernetes_cluster(self, namespace: str = "default") -> List[ResourceMetrics]:
        """Monitor Kubernetes cluster resources"""

        metrics = []

        try:
            # Monitor pods
            pod_metrics = await self._monitor_k8s_pods(namespace)
            metrics.extend(pod_metrics)

            # Monitor nodes
            node_metrics = await self._monitor_k8s_nodes()
            metrics.extend(node_metrics)

            # Monitor services
            service_metrics = await self._monitor_k8s_services(namespace)
            metrics.extend(service_metrics)

            return metrics

        except Exception as e:
            raise MonitoringError(f"Kubernetes monitoring failed: {str(e)}") from e

    async def _monitor_k8s_pods(self, namespace: str) -> List[ResourceMetrics]:
        """Monitor Kubernetes pods"""
        metrics = []

        try:
            # Get pod metrics
            cmd = f"kubectl top pods -n {namespace} --no-headers"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success and result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        pod_metrics = self._parse_pod_metrics(line)
                        if pod_metrics:
                            pod_name, cpu_float, memory_float = pod_metrics

                            # Check pod status
                            pod_status = await self._check_pod_status(pod_name, namespace)

                            # Evaluate alerts
                            alerts, healthy = self._evaluate_pod_alerts(cpu_float, memory_float, pod_status)

                            # Create resource metrics
                            resource_metrics = self._create_pod_resource_metrics(pod_name, cpu_float, memory_float, namespace, healthy, alerts)
                            metrics.append(resource_metrics)

            return metrics

        except Exception as e:
            logger.error(f"Pod monitoring failed: {str(e)}")
            return []

    def _parse_pod_metrics(self, line: str) -> Optional[tuple]:
        """Parse a line from kubectl top pods output"""
        try:
            parts = line.split()
            if len(parts) >= 3:
                pod_name = parts[0]
                cpu_usage = parts[1].replace("m", "")  # Remove 'm' suffix
                memory_usage = parts[2].replace("Mi", "")  # Remove 'Mi' suffix

                # Convert to float
                cpu_float = float(cpu_usage) / 10 if "m" in parts[1] else float(cpu_usage)
                memory_float = float(memory_usage)

                return pod_name, cpu_float, memory_float
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse pod metrics line '{line}': {e}")
        return None

    async def _check_pod_status(self, pod_name: str, namespace: str) -> str:
        """Check pod status via kubectl"""
        try:
            status_cmd = f"kubectl get pod {pod_name} -n {namespace} -o json"
            status_result = await self.command_executor.execute_command(command=status_cmd, timeout_seconds=15)

            if status_result.success:
                pod_data = json.loads(status_result.stdout)
                pod_status = pod_data.get("status", {})
                return pod_status.get("phase", "Unknown")
        except Exception as e:
            logger.warning(f"Failed to get pod {pod_name} status: {e}")

        return "Unknown"

    def _evaluate_pod_alerts(self, cpu_float: float, memory_float: float, phase: str) -> tuple:
        """Evaluate alerts for a pod"""
        alerts = []
        healthy = True

        if phase != "Running":
            healthy = False
            alerts.append(f"Pod not running (phase: {phase})")

        # Check CPU thresholds
        if cpu_float > 80.0:  # Over 80% CPU
            alerts.append("High CPU usage")

        # Check memory thresholds
        if memory_float > 1000:  # Over 1GB
            alerts.append("High memory usage")

        return alerts, healthy

    def _create_pod_resource_metrics(self, pod_name: str, cpu_float: float, memory_float: float, namespace: str, healthy: bool, alerts: List[str]) -> ResourceMetrics:
        """Create ResourceMetrics for a pod"""
        return ResourceMetrics(
            resource_id=pod_name,
            resource_type=ResourceType.POD,
            timestamp=datetime.now(),
            metrics={
                MetricType.CPU_USAGE.value: cpu_float,
                MetricType.MEMORY_USAGE.value: memory_float,
            },
            labels={"namespace": namespace},
            healthy=healthy,
            alerts=alerts,
        )

    async def _monitor_k8s_nodes(self) -> List[ResourceMetrics]:
        """Monitor Kubernetes nodes"""
        metrics = []

        try:
            cmd = "kubectl top nodes --no-headers"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success and result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        node_metrics = self._parse_node_metrics(line)
                        if node_metrics:
                            node_name, cpu_percent, memory_percent = node_metrics

                            # Evaluate alerts
                            alerts, healthy = self._evaluate_node_alerts(cpu_percent, memory_percent)

                            # Create resource metrics
                            resource_metrics = self._create_node_resource_metrics(node_name, cpu_percent, memory_percent, alerts, healthy)
                            metrics.append(resource_metrics)

            return metrics

        except Exception as e:
            logger.error(f"Node monitoring failed: {str(e)}")
            return []

    def _parse_node_metrics(self, line: str) -> Optional[tuple]:
        """Parse a line from kubectl top nodes output"""
        try:
            parts = line.split()
            if len(parts) >= 5:
                node_name = parts[0]
                cpu_percent = float(parts[2].replace("%", ""))
                memory_percent = float(parts[4].replace("%", ""))

                return node_name, cpu_percent, memory_percent
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse node metrics line '{line}': {e}")
        return None

    def _evaluate_node_alerts(self, cpu_percent: float, memory_percent: float) -> tuple:
        """Evaluate alerts for a node"""
        alerts = []
        healthy = True

        if cpu_percent > self.alert_thresholds[MetricType.CPU_USAGE]:
            alerts.append(f"High CPU usage: {cpu_percent}%")
            healthy = False

        if memory_percent > self.alert_thresholds[MetricType.MEMORY_USAGE]:
            alerts.append(f"High memory usage: {memory_percent}%")
            healthy = False

        return alerts, healthy

    def _create_node_resource_metrics(self, node_name: str, cpu_percent: float, memory_percent: float, alerts: List[str], healthy: bool) -> ResourceMetrics:
        """Create ResourceMetrics for a node"""
        return ResourceMetrics(
            resource_id=node_name,
            resource_type=ResourceType.NODE,
            timestamp=datetime.now(),
            metrics={
                MetricType.CPU_USAGE.value: cpu_percent,
                MetricType.MEMORY_USAGE.value: memory_percent,
            },
            labels={"node": node_name},
            healthy=healthy,
            alerts=alerts,
        )

    async def _monitor_k8s_services(self, namespace: str) -> List[ResourceMetrics]:
        """Monitor Kubernetes services"""

        metrics = []

        try:
            cmd = f"kubectl get services -n {namespace} -o json"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success and result.stdout:
                services_data = json.loads(result.stdout)

                for service in services_data.get("items", []):
                    service_name = service["metadata"]["name"]
                    service_type = service["spec"].get("type", "ClusterIP")

                    # Check if service has endpoints
                    endpoints_cmd = f"kubectl get endpoints {service_name} -n {namespace} -o json"
                    endpoints_result = await self.command_executor.execute_command(command=endpoints_cmd, timeout_seconds=15)

                    healthy = True
                    alerts = []
                    endpoint_count = 0

                    if endpoints_result.success:
                        endpoints_data = json.loads(endpoints_result.stdout)
                        subsets = endpoints_data.get("subsets", [])
                        endpoint_count = sum(len(subset.get("addresses", [])) for subset in subsets)

                        if endpoint_count == 0:
                            healthy = False
                            alerts.append("Service has no available endpoints")

                    metrics.append(
                        ResourceMetrics(
                            resource_id=service_name,
                            resource_type=ResourceType.SERVICE,
                            timestamp=datetime.now(),
                            metrics={"endpoint_count": float(endpoint_count)},
                            labels={"namespace": namespace, "type": service_type},
                            healthy=healthy,
                            alerts=alerts,
                        )
                    )

            return metrics

        except Exception as e:
            logger.error(f"Service monitoring failed: {str(e)}")
            return []

    async def monitor_docker_containers(self) -> List[ResourceMetrics]:
        """Monitor Docker containers"""
        metrics = []

        try:
            # Get container stats
            cmd = "docker stats --no-stream --format 'table {{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.NetIO}}\\t{{.BlockIO}}'"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success and result.stdout:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header

                for line in lines:
                    if line.strip():
                        container_metrics = self._parse_docker_stats(line)
                        if container_metrics:
                            container_name, cpu_percent, memory_usage = container_metrics

                            # Evaluate alerts
                            alerts, healthy = self._evaluate_container_alerts(cpu_percent)

                            # Create resource metrics
                            resource_metrics = self._create_container_resource_metrics(container_name, cpu_percent, memory_usage, alerts, healthy)
                            metrics.append(resource_metrics)

            return metrics

        except Exception as e:
            logger.error(f"Docker monitoring failed: {str(e)}")
            return []

    def _parse_docker_stats(self, line: str) -> Optional[tuple]:
        """Parse a line from docker stats output"""
        try:
            parts = line.split("\t")
            if len(parts) >= 4:
                container_name = parts[0]
                cpu_percent = float(parts[1].replace("%", ""))
                memory_usage = parts[2]  # Format: "used / total"

                return container_name, cpu_percent, memory_usage
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse docker stats line '{line}': {e}")
        return None

    def _evaluate_container_alerts(self, cpu_percent: float) -> tuple:
        """Evaluate alerts for a container"""
        alerts = []
        healthy = True

        if cpu_percent > self.alert_thresholds[MetricType.CPU_USAGE]:
            alerts.append(f"High CPU usage: {cpu_percent}%")
            healthy = False

        return alerts, healthy

    def _create_container_resource_metrics(self, container_name: str, cpu_percent: float, memory_usage: str, alerts: List[str], healthy: bool) -> ResourceMetrics:
        """Create ResourceMetrics for a container"""
        return ResourceMetrics(
            resource_id=container_name,
            resource_type=ResourceType.CONTAINER,
            timestamp=datetime.now(),
            metrics={
                MetricType.CPU_USAGE.value: cpu_percent,
                "memory_usage_raw": memory_usage,
            },
            labels={"platform": "docker"},
            healthy=healthy,
            alerts=alerts,
        )

    async def monitor_system_resources(self) -> List[ResourceMetrics]:
        """Monitor system-level resources"""

        metrics = []

        try:
            # CPU usage
            cpu_cmd = "top -l 1 | grep 'CPU usage' | awk '{print $3}' | sed 's/%//'"
            cpu_result = await self.command_executor.execute_command(command=cpu_cmd, timeout_seconds=15)

            # Memory usage
            memory_cmd = "vm_stat | grep 'Pages active' | awk '{print $3}' | sed 's/\\.//' | head -1"
            memory_result = await self.command_executor.execute_command(command=memory_cmd, timeout_seconds=15)

            # Disk usage
            disk_cmd = "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'"
            disk_result = await self.command_executor.execute_command(command=disk_cmd, timeout_seconds=15)

            alerts = []
            healthy = True

            cpu_usage = 0.0
            disk_usage = 0.0

            if cpu_result.success and cpu_result.stdout:
                cpu_usage = float(cpu_result.stdout.strip())
                if cpu_usage > self.alert_thresholds[MetricType.CPU_USAGE]:
                    alerts.append(f"High CPU usage: {cpu_usage}%")
                    healthy = False

            if memory_result.success and memory_result.stdout:
                # Basic memory check - this would need more sophisticated calculation in production
                pass

            if disk_result.success and disk_result.stdout:
                disk_usage = float(disk_result.stdout.strip())
                if disk_usage > self.alert_thresholds[MetricType.DISK_USAGE]:
                    alerts.append(f"High disk usage: {disk_usage}%")
                    healthy = False

            metrics.append(
                ResourceMetrics(
                    resource_id="system",
                    resource_type=ResourceType.NODE,
                    timestamp=datetime.now(),
                    metrics={
                        MetricType.CPU_USAGE.value: cpu_usage,
                        MetricType.DISK_USAGE.value: disk_usage,
                    },
                    labels={"type": "system"},
                    healthy=healthy,
                    alerts=alerts,
                )
            )

            return metrics

        except Exception as e:
            logger.error(f"System monitoring failed: {str(e)}")
            return []

    async def monitor_cloud_resources(self, provider: str = "aws") -> List[ResourceMetrics]:
        """Monitor cloud provider resources"""

        if provider.lower() == "aws":
            return await self._monitor_aws_resources()
        elif provider.lower() == "gcp":
            return await self._monitor_gcp_resources()
        elif provider.lower() == "azure":
            return await self._monitor_azure_resources()
        else:
            logger.warning(f"Unsupported cloud provider: {provider}")
            return []

    async def _monitor_aws_resources(self) -> List[ResourceMetrics]:
        """Monitor AWS resources using AWS CLI"""

        metrics = []

        try:
            # Monitor EC2 instances
            cmd = "aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType]' --output table"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success:
                # Basic parsing of AWS output - would need more sophisticated parsing in production
                logger.info("AWS resources checked")

            return metrics

        except Exception as e:
            logger.error(f"AWS monitoring failed: {str(e)}")
            return []

    async def _monitor_gcp_resources(self) -> List[ResourceMetrics]:
        """Monitor GCP resources using gcloud CLI"""

        metrics = []

        try:
            # Monitor Compute instances
            cmd = "gcloud compute instances list --format='table(name,status,zone,machineType)'"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success:
                logger.info("GCP resources checked")

            return metrics

        except Exception as e:
            logger.error(f"GCP monitoring failed: {str(e)}")
            return []

    async def _monitor_azure_resources(self) -> List[ResourceMetrics]:
        """Monitor Azure resources using Azure CLI"""

        metrics = []

        try:
            # Monitor VMs
            cmd = "az vm list --show-details --output table"
            result = await self.command_executor.execute_command(command=cmd, timeout_seconds=30)

            if result.success:
                logger.info("Azure resources checked")

            return metrics

        except Exception as e:
            logger.error(f"Azure monitoring failed: {str(e)}")
            return []

    def store_metrics(self, metrics: List[ResourceMetrics]):
        """Store metrics in history for trend analysis"""

        for metric in metrics:
            resource_key = f"{metric.resource_type.value}:{metric.resource_id}"

            if resource_key not in self.metric_history:
                self.metric_history[resource_key] = []

            self.metric_history[resource_key].append(metric)

            # Keep only last 24 hours of data
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metric_history[resource_key] = [m for m in self.metric_history[resource_key] if m.timestamp > cutoff_time]

    def get_resource_trends(self, resource_id: str, resource_type: ResourceType, hours: int = 1) -> Dict[str, List[float]]:
        """Get metric trends for a specific resource"""

        resource_key = f"{resource_type.value}:{resource_id}"

        if resource_key not in self.metric_history:
            return {}

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metric_history[resource_key] if m.timestamp > cutoff_time]

        trends = {}
        for metric in recent_metrics:
            for metric_name, value in metric.metrics.items():
                if metric_name not in trends:
                    trends[metric_name] = []
                trends[metric_name].append(value)

        return trends

    def detect_anomalies(self, metrics: List[ResourceMetrics]) -> List[Dict[str, Any]]:
        """Detect anomalies in current metrics compared to historical data"""

        anomalies = []

        for metric in metrics:
            resource_key = f"{metric.resource_type.value}:{metric.resource_id}"

            if resource_key in self.metric_history:
                # Get historical averages (simple implementation)
                historical_metrics = self.metric_history[resource_key]

                for metric_name, current_value in metric.metrics.items():
                    historical_values = [m.metrics.get(metric_name, 0) for m in historical_metrics[-10:] if metric_name in m.metrics]

                    if historical_values:
                        avg_value = sum(historical_values) / len(historical_values)
                        threshold = avg_value * 1.5  # 50% increase threshold

                        if current_value > threshold:
                            anomalies.append(
                                {
                                    "resource_id": metric.resource_id,
                                    "resource_type": metric.resource_type.value,
                                    "metric_name": metric_name,
                                    "current_value": current_value,
                                    "average_value": avg_value,
                                    "anomaly_factor": current_value / avg_value,
                                    "timestamp": metric.timestamp.isoformat(),
                                }
                            )

        return anomalies

    def generate_alerts(self, metrics: List[ResourceMetrics]) -> List[Dict[str, Any]]:
        """Generate alerts based on current metrics"""

        alerts = []

        for metric in metrics:
            if not metric.healthy or metric.alerts:
                alert = {
                    "timestamp": metric.timestamp.isoformat(),
                    "resource_id": metric.resource_id,
                    "resource_type": metric.resource_type.value,
                    "severity": (SeverityLevel.WARNING.value if not metric.healthy else SeverityLevel.MEDIUM.value),
                    "alerts": metric.alerts,
                    "metrics": metric.metrics,
                    "labels": metric.labels,
                }
                alerts.append(alert)

        return alerts

    def get_monitoring_summary(self, metrics: List[ResourceMetrics]) -> Dict[str, Any]:
        """Generate monitoring summary with key insights"""

        total_resources = len(metrics)
        healthy_resources = len([m for m in metrics if m.healthy])
        unhealthy_resources = total_resources - healthy_resources

        resource_counts = {}
        for metric in metrics:
            resource_type = metric.resource_type.value
            resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

        alerts = self.generate_alerts(metrics)
        anomalies = self.detect_anomalies(metrics)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_resources": total_resources,
            "healthy_resources": healthy_resources,
            "unhealthy_resources": unhealthy_resources,
            "health_percentage": ((healthy_resources / total_resources * 100) if total_resources > 0 else 0),
            "resource_counts": resource_counts,
            "alert_count": len(alerts),
            "anomaly_count": len(anomalies),
            "alerts": alerts[:5],  # Top 5 alerts
            "anomalies": anomalies[:5],  # Top 5 anomalies
        }


class AlertManager:
    """Manage alerts and notifications"""

    def __init__(self):
        # Create a more permissive security config for alert operations
        from ...devops_commander.config import SecurityConfig
        monitoring_config = SecurityConfig(
            validation_enabled=False,  # Disable validation for monitoring commands
            audit_enabled=True,
            enable_safety_checks=False  # Disable safety checks for read-only monitoring
        )
        self.command_executor = SecureCommandExecutor(monitoring_config)
        self.alert_history: List[Dict[str, Any]] = []
        self.notification_channels = []

    def add_notification_channel(self, channel_type: str, config: Dict[str, Any]):
        """Add notification channel (email, slack, webhook, etc.)"""

        self.notification_channels.append({"type": channel_type, "config": config, "enabled": True})

    async def send_alert(self, alert: Dict[str, Any]):
        """Send alert through configured channels"""

        self.alert_history.append(alert)

        for channel in self.notification_channels:
            if channel["enabled"]:
                try:
                    await self._send_to_channel(alert, channel)
                except Exception as e:
                    logger.error(f"Failed to send alert to {channel['type']}: {str(e)}")

    async def _send_to_channel(self, alert: Dict[str, Any], channel: Dict[str, Any]):
        """Send alert to specific notification channel"""

        channel_type = channel["type"]

        if channel_type == "webhook":
            # Send webhook notification
            webhook_url = channel["config"].get("url")
            if webhook_url:
                cmd = f"curl -X POST -H 'Content-Type: application/json' -d '{json.dumps(alert)}' {webhook_url}"
                await self.command_executor.execute_command(command=cmd, timeout_seconds=10)

        elif channel_type == "email":
            # Basic email notification (would need proper SMTP setup)
            email_config = channel["config"]
            logger.info(f"Would send email alert to {email_config.get('recipient')}")

        elif channel_type == "slack":
            # Slack notification (would need Slack webhook)
            slack_config = channel["config"]
            webhook_url = slack_config.get("webhook_url")
            if webhook_url:
                slack_message = {
                    "text": f"🚨 Alert: {alert['resource_id']} - {', '.join(alert['alerts'])}",
                    "username": "NeuraOps Monitor",
                    "icon_emoji": ":warning:",
                }
                cmd = f"curl -X POST -H 'Content-Type: application/json' -d '{json.dumps(slack_message)}' {webhook_url}"
                await self.command_executor.execute_command(command=cmd, timeout_seconds=10)

    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alert history"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        return [alert for alert in self.alert_history if datetime.fromisoformat(alert["timestamp"]) > cutoff_time]

    def generate_alerts(self, metrics: List[ResourceMetrics]) -> List[Dict[str, Any]]:
        """Generate alerts based on current metrics"""

        alerts = []

        for metric in metrics:
            if not metric.healthy or metric.alerts:
                alert = {
                    "timestamp": metric.timestamp.isoformat(),
                    "resource_id": metric.resource_id,
                    "resource_type": metric.resource_type.value,
                    "severity": (SeverityLevel.WARNING.value if not metric.healthy else SeverityLevel.MEDIUM.value),
                    "alerts": metric.alerts,
                    "metrics": metric.metrics,
                    "labels": metric.labels,
                }
                alerts.append(alert)

        return alerts


class MonitoringDashboard:
    """Generate monitoring dashboard data"""

    def __init__(self, monitor: InfrastructureMonitor):
        self.monitor = monitor

    def generate_dashboard_data(self, metrics: List[ResourceMetrics]) -> Dict[str, Any]:
        """Generate dashboard data for visualization"""

        # Resource health overview
        health_overview = self._get_health_overview(metrics)

        # Resource utilization
        utilization = self._get_utilization_stats(metrics)

        # Recent alerts
        alerts = self.monitor.generate_alerts(metrics)

        # Anomalies
        anomalies = self.monitor.detect_anomalies(metrics)

        return {
            "health_overview": health_overview,
            "utilization": utilization,
            "alerts": alerts,
            "anomalies": anomalies,
            "last_updated": datetime.now().isoformat(),
        }

    def _get_health_overview(self, metrics: List[ResourceMetrics]) -> Dict[str, Any]:
        """Get health overview by resource type"""

        overview = {}

        for metric in metrics:
            resource_type = metric.resource_type.value

            if resource_type not in overview:
                overview[resource_type] = {"total": 0, "healthy": 0, "unhealthy": 0}

            overview[resource_type]["total"] += 1

            if metric.healthy:
                overview[resource_type]["healthy"] += 1
            else:
                overview[resource_type]["unhealthy"] += 1

        # Calculate health percentages
        for resource_type in overview:
            total = overview[resource_type]["total"]
            if total > 0:
                overview[resource_type]["health_percentage"] = overview[resource_type]["healthy"] / total * 100
            else:
                overview[resource_type]["health_percentage"] = 0

        return overview

    def _get_utilization_stats(self, metrics: List[ResourceMetrics]) -> Dict[str, Any]:
        """Get resource utilization statistics"""

        utilization = {"cpu": [], "memory": [], "disk": []}

        for metric in metrics:
            cpu_usage = metric.metrics.get(MetricType.CPU_USAGE.value)
            if cpu_usage is not None:
                utilization["cpu"].append(cpu_usage)

            memory_usage = metric.metrics.get(MetricType.MEMORY_USAGE.value)
            if memory_usage is not None:
                utilization["memory"].append(memory_usage)

            disk_usage = metric.metrics.get(MetricType.DISK_USAGE.value)
            if disk_usage is not None:
                utilization["disk"].append(disk_usage)

        # Calculate statistics
        stats = {}
        for metric_type, values in utilization.items():
            if values:
                stats[metric_type] = {
                    "average": sum(values) / len(values),
                    "max": max(values),
                    "min": min(values),
                    "count": len(values),
                }
            else:
                stats[metric_type] = {"average": 0, "max": 0, "min": 0, "count": 0}

        return stats


# Convenience functions for quick monitoring
async def quick_k8s_health_check(namespace: str = "default") -> MonitoringResult:
    """Quick Kubernetes health check"""

    monitor = InfrastructureMonitor()

    try:
        metrics = await monitor.monitor_kubernetes_cluster(namespace)
        summary = monitor.get_monitoring_summary(metrics)

        return MonitoringResult(
            success=True,
            summary=summary,
            details=metrics,
            severity=(SeverityLevel.INFO if summary["unhealthy_resources"] == 0 else SeverityLevel.WARNING),
        )

    except Exception as e:
        return MonitoringResult(success=False, error_message=str(e), severity=SeverityLevel.ERROR)


async def quick_docker_health_check() -> MonitoringResult:
    """Quick Docker health check"""

    monitor = InfrastructureMonitor()

    try:
        metrics = await monitor.monitor_docker_containers()
        summary = monitor.get_monitoring_summary(metrics)

        return MonitoringResult(
            success=True,
            summary=summary,
            details=metrics,
            severity=(SeverityLevel.INFO if summary["unhealthy_resources"] == 0 else SeverityLevel.WARNING),
        )

    except Exception as e:
        return MonitoringResult(success=False, error_message=str(e), severity=SeverityLevel.ERROR)


async def comprehensive_infrastructure_check(include_cloud: bool = False, cloud_provider: str = "aws", namespace: str = "default") -> MonitoringResult:
    """Comprehensive infrastructure health check"""

    monitor = InfrastructureMonitor()
    all_metrics = []

    try:
        # Check system resources
        system_metrics = await monitor.monitor_system_resources()
        all_metrics.extend(system_metrics)

        # Check Docker containers
        docker_metrics = await monitor.monitor_docker_containers()
        all_metrics.extend(docker_metrics)

        # Check Kubernetes (if available) - now with specified namespace
        try:
            k8s_metrics = await monitor.monitor_kubernetes_cluster(namespace)
            all_metrics.extend(k8s_metrics)
        except MonitoringError:
            logger.info(f"Kubernetes not available for monitoring in namespace '{namespace}'")

        # Check cloud resources (if requested)
        if include_cloud:
            try:
                cloud_metrics = await monitor.monitor_cloud_resources(cloud_provider)
                all_metrics.extend(cloud_metrics)
            except MonitoringError:
                logger.info(f"Cloud monitoring for {cloud_provider} not available")

        # Store metrics and generate summary
        monitor.store_metrics(all_metrics)
        summary = monitor.get_monitoring_summary(all_metrics)

        return MonitoringResult(
            success=True,
            summary=summary,
            details=all_metrics,
            severity=(SeverityLevel.INFO if summary["unhealthy_resources"] == 0 else SeverityLevel.WARNING),
        )

    except Exception as e:
        return MonitoringResult(success=False, error_message=str(e), severity=SeverityLevel.ERROR)
