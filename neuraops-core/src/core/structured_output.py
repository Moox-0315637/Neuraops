# src/core/structured_output.py
"""
Schemas Pydantic pour outputs structurés - NeuraOps
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Niveaux de sévérité"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    MEDIUM = "medium"
    ERROR = "error"
    CRITICAL = "critical"


class ActionType(str, Enum):
    """Types d'actions DevOps"""

    ANALYZE = "analyze"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    BACKUP = "backup"
    RESTORE = "restore"
    SCALE = "scale"


class SafetyLevel(str, Enum):
    """Niveaux de sécurité pour les commandes"""

    SAFE = "safe"
    CAUTIOUS = "cautious"
    MODERATE = "moderate"
    RISKY = "risky"
    DANGEROUS = "dangerous"


class LogAnalysisResult(BaseModel):
    """Résultat d'analyse de logs"""

    severity: SeverityLevel = Field(description="Niveau de sévérité global")
    error_count: int = Field(ge=0, description="Nombre d'erreurs trouvées")
    warning_count: int = Field(ge=0, default=0, description="Nombre d'avertissements trouvés")
    critical_issues: List[str] = Field(default_factory=list, description="Issues critiques identifiées")
    error_patterns: Dict[str, int] = Field(default_factory=dict, description="Patterns d'erreurs et fréquences")
    affected_services: List[str] = Field(default_factory=list, description="Services affectés")
    recommendations: List[str] = Field(default_factory=list, description="Recommandations pour résoudre")
    root_causes: List[str] = Field(default_factory=list, description="Causes racines identifiées")
    security_issues: List[str] = Field(default_factory=list, description="Problèmes de sécurité identifiés")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Métriques de performance")
    incident_timeline: List[Any] = Field(default_factory=list, description="Timeline des incidents")


class DevOpsCommand(BaseModel):
    """Commande DevOps avec validation sécurité"""

    action: ActionType = Field(description="Type d'action")
    command: str = Field(description="Commande à exécuter")
    description: str = Field(description="Description de l'action")
    safety_level: SafetyLevel = Field(description="Niveau de sécurité")
    estimated_impact: str = Field(description="Impact estimé")
    prerequisites: List[str] = Field(description="Prérequis")
    verification_commands: List[str] = Field(description="Commandes de vérification")
    rollback_procedure: Optional[str] = Field(default=None, description="Procédure de rollback")
    requires_confirmation: bool = Field(default=False, description="Nécessite confirmation utilisateur")
    timeout_seconds: int = Field(default=300, description="Timeout d'exécution en secondes")


class InfrastructureAssessment(BaseModel):
    """Évaluation infrastructure"""

    security_score: int = Field(ge=0, le=100, description="Score sécurité")
    performance_score: int = Field(ge=0, le=100, description="Score performance")
    cost_score: int = Field(ge=0, le=100, description="Score coût")
    security_issues: List[str] = Field(description="Problèmes de sécurité")
    recommended_actions: List[DevOpsCommand] = Field(description="Actions recommandées")
    compliance_status: Dict[str, bool] = Field(description="Statut compliance")


class IncidentResponse(BaseModel):
    """Plan de réponse incident"""

    incident_type: str = Field(description="Type d'incident")
    severity: SeverityLevel = Field(description="Sévérité")
    immediate_actions: List[DevOpsCommand] = Field(description="Actions immédiates")
    investigation_steps: List[str] = Field(description="Étapes d'investigation")
    communication_plan: List[str] = Field(description="Plan de communication")
    estimated_resolution_time: str = Field(description="Temps de résolution estimé")


class IntegrationTestResult(BaseModel):
    """Result of an integration test workflow"""

    test_name: str = Field(description="Name of the integration test")
    status: str = Field(description="Test status (pass/fail)")
    execution_time: float = Field(ge=0, description="Test execution time in seconds")
    ai_accuracy: float = Field(ge=0, le=1, description="AI accuracy score (0-1)")
    error_details: Optional[str] = Field(default=None, description="Error details if test failed")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


class MonitoringResult(BaseModel):
    """Result of infrastructure monitoring operations"""

    success: bool = Field(description="Whether the monitoring operation succeeded")
    severity: SeverityLevel = Field(description="Overall severity level")
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of monitoring results")
    details: List[Any] = Field(default_factory=list, description="Detailed monitoring data")


class AnalysisResult(BaseModel):
    """Result of infrastructure analysis operations"""

    success: bool = Field(description="Whether the analysis operation succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of analysis results")
    details: List[Any] = Field(default_factory=list, description="Detailed analysis data")


class PredictionResult(BaseModel):
    """Result of predictive analytics operations"""

    success: bool = Field(description="Whether the prediction operation succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if prediction failed")
    predictions: List[Any] = Field(default_factory=list, description="Prediction results and forecasts")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of prediction results")
    severity: SeverityLevel = Field(default=SeverityLevel.INFO, description="Severity level of predictions")


class DeploymentResult(BaseModel):
    """Result of infrastructure deployment operations"""

    success: bool = Field(description="Whether the deployment operation succeeded")
    deployment_id: Optional[str] = Field(default=None, description="Unique deployment identifier")
    error_message: Optional[str] = Field(default=None, description="Error message if deployment failed")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of deployment results")
    details: List[Any] = Field(default_factory=list, description="Detailed deployment data")


class CommandSuggestion(BaseModel):
    """AI-generated command suggestion with safety validation"""

    command: str = Field(description="Suggested command to execute")
    description: str = Field(description="Human-readable description of the command")
    safety_level: SafetyLevel = Field(description="Safety level assessment")
    confidence: float = Field(ge=0, le=1, description="AI confidence in the suggestion")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites before execution")


class AssistantResponse(BaseModel):
    """AI assistant response with structured content"""

    message: str = Field(description="Human-readable response message")
    suggestions: List[CommandSuggestion] = Field(default_factory=list, description="Command suggestions")
    analysis: Optional[str] = Field(default=None, description="Detailed analysis if applicable")
    confidence: float = Field(ge=0, le=1, description="Overall confidence in response")
