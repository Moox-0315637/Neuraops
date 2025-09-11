"""Agent configuration management with Pydantic settings."""

from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# Application constants
NEURAOPS_DIR_NAME = ".neuraops"


class AgentConfig(BaseSettings):
    """Main agent configuration."""
    
    # Core connection
    core_url: str = Field(default="", validation_alias="NEURAOPS_CORE_URL")
    auth_token: Optional[str] = Field(default=None, validation_alias="NEURAOPS_AUTH_TOKEN")
    agent_name: str = Field(default_factory=lambda: os.uname().nodename, 
                           env="NEURAOPS_AGENT_NAME")
    
    # Connection settings
    reconnect_interval: int = Field(default=30, env="NEURAOPS_RECONNECT_INTERVAL")
    heartbeat_interval: int = Field(default=60, env="NEURAOPS_HEARTBEAT_INTERVAL") 
    command_timeout: int = Field(default=300, env="NEURAOPS_COMMAND_TIMEOUT")
    
    # Metrics collection
    metrics_interval: int = Field(default=30, env="NEURAOPS_METRICS_INTERVAL")
    collect_system_info: bool = Field(default=True, env="NEURAOPS_COLLECT_SYSTEM")
    collect_filesystem: bool = Field(default=True, env="NEURAOPS_COLLECT_FS")
    
    # Security
    enable_command_execution: bool = Field(default=True, 
                                         env="NEURAOPS_ENABLE_COMMANDS")
    allowed_commands: list[str] = Field(default_factory=lambda: [
        "systemctl status", "ps", "df", "free", "uptime", "whoami"
    ])
    
    # Logging
    log_level: str = Field(default="INFO", env="NEURAOPS_LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="NEURAOPS_LOG_FILE")
    
    model_config = ConfigDict(
        env_file=str(Path.home() / NEURAOPS_DIR_NAME / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env file
    )


def get_config_path() -> Path:
    """Get agent configuration file path."""
    return Path.home() / NEURAOPS_DIR_NAME / "agent.yaml"


def load_config() -> AgentConfig:
    """Load agent configuration."""
    return AgentConfig()


def save_config_value(key: str, value: str) -> None:
    """Save a configuration value."""
    config_dir = Path.home() / NEURAOPS_DIR_NAME
    config_dir.mkdir(exist_ok=True)
    
    env_file = config_dir / ".env"
    
    # Map internal config keys to environment variable names
    env_key_map = {
        "neuraops_core_url": "NEURAOPS_CORE_URL",
        "neuraops_auth_token": "NEURAOPS_AUTH_TOKEN", 
        "neuraops_agent_name": "NEURAOPS_AGENT_NAME",
        "neuraops_log_level": "NEURAOPS_LOG_LEVEL",
        "neuraops_log_file": "NEURAOPS_LOG_FILE"
    }
    
    env_key = env_key_map.get(key, key.upper())
    
    # Simple key=value storage for now
    lines = []
    if env_file.exists():
        lines = env_file.read_text().splitlines()
    
    # Update or add the key
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}="):
            lines[i] = f"{env_key}={value}"
            found = True
            break
    
    if not found:
        lines.append(f"{env_key}={value}")
    
    env_file.write_text("\n".join(lines) + "\n")