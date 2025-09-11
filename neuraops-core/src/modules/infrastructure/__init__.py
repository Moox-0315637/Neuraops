"""NeuraOps Infrastructure Module"""

from .templates import TemplateEngine, TemplateType, quick_dockerfile, quick_k8s_deployment

from .monitoring import (
    InfrastructureMonitor,
    ResourceType,
    MetricType,
    AlertManager,
    MonitoringDashboard,
    quick_k8s_health_check,
    quick_docker_health_check,
    comprehensive_infrastructure_check,
)
from .analyzer import (
    InfrastructureAnalyzer,
    AnalysisType,
    AnalysisFinding,
    CostSavingOpportunity,
)

__all__ = [
    # Templates
    "TemplateEngine",
    "TemplateType",
    "quick_dockerfile",
    "quick_k8s_deployment",
    # Deployment (temporarily disabled due to syntax errors)
    # "DeploymentManager",
    # "DeploymentStrategy",
    # "quick_docker_deploy",
    # "quick_k8s_deploy",
    # Monitoring
    "InfrastructureMonitor",
    "ResourceType",
    "MetricType",
    "AlertManager",
    "MonitoringDashboard",
    "quick_k8s_health_check",
    "quick_docker_health_check",
    "comprehensive_infrastructure_check",
    # Analysis
    "InfrastructureAnalyzer",
    "AnalysisType",
    "AnalysisFinding",
    "CostSavingOpportunity",
]
