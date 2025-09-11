# src/devops_commander/exceptions.py
"""
NeuraOps Exceptions
"""


class NeuraOpsError(Exception):
    """Base exception pour NeuraOps"""

    pass


class ModelInferenceError(NeuraOpsError):
    """Erreur d'inférence du modèle"""

    pass


class StructuredOutputError(NeuraOpsError):
    """Erreur de génération structurée"""

    pass


class ConfigurationError(NeuraOpsError):
    """Erreur de configuration"""

    pass


class OllamaConnectionError(NeuraOpsError):
    """Erreur de connexion Ollama"""

    pass


class LogAnalysisError(NeuraOpsError):
    """Erreur d'analyse de logs"""

    pass


class InfrastructureError(NeuraOpsError):
    """Erreur d'infrastructure"""

    pass


class SecurityViolationError(NeuraOpsError):
    """Erreur de violation de sécurité"""
    
    def __init__(self, message: str, command: str = None, violation_type: str = None):
        super().__init__(message)
        self.command = command
        self.violation_type = violation_type


class CommandExecutionError(NeuraOpsError):
    """Erreur d'exécution de commande avec contexte"""

    def __init__(self, message: str, command: str = None, exit_code: int = None):
        super().__init__(message)
        self.command = command
        self.exit_code = exit_code


class ValidationError(NeuraOpsError):
    """Erreur de validation"""

    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.field = field


class MonitoringError(NeuraOpsError):
    """Erreur de monitoring d'infrastructure"""

    pass


class AnalysisError(NeuraOpsError):
    """Erreur d'analyse d'infrastructure"""

    pass


class DeploymentError(NeuraOpsError):
    """Erreur de déploiement d'infrastructure"""

    pass


class LogParsingError(NeuraOpsError):
    """Erreur de parsing de logs"""

    pass


class PredictionError(NeuraOpsError):
    """Erreur de prédiction et analyses prédictives"""

    pass


class IncidentDetectionError(NeuraOpsError):
    """Erreur de détection d'incidents"""

    pass
