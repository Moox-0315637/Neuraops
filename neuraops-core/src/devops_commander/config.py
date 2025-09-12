# src/devops_commander/config.py
"""
Configuration NeuraOps - Pydantic V2 Correct
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

# Constante pour éviter duplication
NEURAOPS_DIR_NAME = ".neuraops"

def _get_neuraops_path(*subdirs: str) -> Path:
    """Get NeuraOps application path with optional subdirectories."""
    base_path = Path.home() / NEURAOPS_DIR_NAME
    for subdir in subdirs:
        base_path = base_path / subdir
    return base_path


class OllamaConfig(BaseSettings):
    """Configuration Ollama"""

    base_url: str = Field(default="https://ollama.prd.ihmn.fr")
    model: str = Field(default="gpt-oss:20b")
    timeout: int = Field(default=300)
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.1)
    num_parallel: int = Field(default=1)
    num_ctx: int = Field(default=4096)

    model_config = ConfigDict(env_prefix="OLLAMA_", case_sensitive=False)


class CacheConfig(BaseSettings):
    """Configuration cache"""

    enabled: bool = Field(default=True)
    ttl: int = Field(default=3600)
    max_entries: int = Field(default=1000)
    storage_path: Path = Field(default_factory=lambda: _get_neuraops_path("cache"))

    model_config = ConfigDict(env_prefix="CACHE_", case_sensitive=False)


class SecurityConfig(BaseSettings):
    """Configuration sécurité"""

    enable_safety_checks: bool = Field(default=True)
    auto_approve_safe: bool = Field(default=False)
    require_confirmation_dangerous: bool = Field(default=True)
    audit_enabled: bool = Field(default=True)

    # Configuration pour SecureCommandExecutor
    validation_enabled: bool = Field(default=True)
    whitelist_enabled: bool = Field(default=False)
    allowed_commands: list[str] = Field(default_factory=lambda: ["ls", "cat", "grep", "echo", "pwd", "whoami", "date"])
    blocked_commands: list[str] = Field(default_factory=lambda: ["rm", "sudo", "chmod", "chown"])
    dangerous_patterns: list[str] = Field(default_factory=lambda: [r"rm\s+-rf", r"sudo\s+", r"chmod\s+777"])
    audit_log_path: Path = Field(default_factory=lambda: _get_neuraops_path("audit.log"))

    # Agent API Keys - Loaded from environment variables
    agent_master_key: Optional[str] = Field(default=None, env="NEURAOPS_AGENT_MASTER_KEY")
    # Changed to str to handle comma-separated values from env
    allowed_api_keys: Optional[str] = Field(default=None, env="NEURAOPS_ALLOWED_API_KEYS")
    
    model_config = ConfigDict(env_prefix="SECURITY_", case_sensitive=False)
    
    def get_valid_api_keys(self) -> set[str]:
        """Get all valid API keys from configuration"""
        valid_keys = set()
        
        # Add master key if configured
        if self.agent_master_key:
            valid_keys.add(self.agent_master_key)
        
        # Add allowed keys from environment (comma-separated)
        if self.allowed_api_keys:
            # Handle comma-separated string
            keys = [key.strip() for key in self.allowed_api_keys.split(',') if key.strip()]
            valid_keys.update(keys)
        
        return valid_keys


class NeuraOpsConfig(BaseSettings):
    """Configuration principale avec sous-configs"""

    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)
    version: str = Field(default="0.1.0")
    data_dir: Path = Field(default_factory=lambda: _get_neuraops_path("data"))
    
    # API Configuration
    jwt_secret: str = Field(default=None, description="JWT secret key - MUST be set via environment variable")
    cors_origins: str = Field(default="*")
    redis_url: str = Field(default="redis://localhost:6379")
    database_url: str = Field(default="postgresql://neuraops:password@localhost:5432/neuraops")
    
    # Core API URL for agent communication
    core_api_url: str = Field(default="http://localhost:8000", env="NEURAOPS_CORE_API_URL")

    # Sous-configurations définies comme fields
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    model_config = ConfigDict(env_prefix="NEURAOPS_", case_sensitive=False)


def get_config() -> NeuraOpsConfig:
    """Récupère la configuration complète"""
    return NeuraOpsConfig()


def get_ollama_config() -> OllamaConfig:
    """Récupère seulement la config Ollama"""
    return OllamaConfig()


def get_cache_config() -> CacheConfig:
    """Récupère seulement la config Cache"""
    return CacheConfig()


def get_security_config() -> SecurityConfig:
    """Récupère seulement la config Security"""
    return SecurityConfig()
