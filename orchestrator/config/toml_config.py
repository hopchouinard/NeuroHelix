"""TOML configuration file loader with precedence handling."""

import os
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python

from pydantic import BaseModel, Field


class OrchestratorConfig(BaseModel):
    """Orchestrator settings."""

    default_model: str = Field(default="gemini-2.5-pro", description="Default Gemini model")
    max_parallel_jobs: int = Field(default=4, ge=1, le=16, description="Max parallel jobs")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    approval_mode: str = Field(default="yolo", description="Gemini approval mode")


class PathsConfig(BaseModel):
    """Path settings."""

    repo_root: Optional[str] = Field(default=None, description="Repository root directory")
    data_dir: Optional[str] = Field(default=None, description="Data directory")
    logs_dir: Optional[str] = Field(default=None, description="Logs directory")


class RegistryConfig(BaseModel):
    """Registry settings."""

    backend: str = Field(default="tsv", description="Registry backend (tsv or sqlite)")
    sqlite_path: str = Field(default="config/prompts.db", description="SQLite database path")
    tsv_path: str = Field(default="config/prompts.tsv", description="TSV registry path")


class CloudflareConfig(BaseModel):
    """Cloudflare publishing settings."""

    api_token: Optional[str] = Field(default=None, description="Cloudflare API token")
    account_id: Optional[str] = Field(default=None, description="Cloudflare account ID")
    project_name: str = Field(
        default="neurohelix-site", description="Cloudflare Pages project name"
    )


class NHConfig(BaseModel):
    """Complete NH configuration."""

    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    cloudflare: CloudflareConfig = Field(default_factory=CloudflareConfig)


class ConfigLoader:
    """Configuration loader with precedence: CLI flags > .nh.toml > env vars > defaults."""

    DEFAULT_CONFIG_NAME = ".nh.toml"

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize config loader.

        Args:
            repo_root: Repository root directory (defaults to current working directory)
        """
        self.repo_root = repo_root or Path.cwd()
        self.config_path = self.repo_root / self.DEFAULT_CONFIG_NAME
        self._config: Optional[NHConfig] = None

    def load(self, reload: bool = False) -> NHConfig:
        """Load configuration with precedence.

        Args:
            reload: Force reload from file

        Returns:
            NHConfig object with merged settings
        """
        if self._config is not None and not reload:
            return self._config

        # Start with defaults
        config_dict = {}

        # Layer 1: Load from .nh.toml if it exists
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                config_dict = tomllib.load(f)

        # Layer 2: Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)

        # Parse into Pydantic model
        self._config = NHConfig(**config_dict)
        return self._config

    def _apply_env_overrides(self, config_dict: dict) -> dict:
        """Apply environment variable overrides.

        Args:
            config_dict: Configuration dictionary from TOML

        Returns:
            Updated configuration dictionary
        """
        # Orchestrator settings
        if "NH_DEFAULT_MODEL" in os.environ:
            config_dict.setdefault("orchestrator", {})["default_model"] = os.environ[
                "NH_DEFAULT_MODEL"
            ]

        if "NH_MAX_PARALLEL_JOBS" in os.environ:
            config_dict.setdefault("orchestrator", {})["max_parallel_jobs"] = int(
                os.environ["NH_MAX_PARALLEL_JOBS"]
            )

        if "NH_ENABLE_RATE_LIMITING" in os.environ:
            config_dict.setdefault("orchestrator", {})["enable_rate_limiting"] = (
                os.environ["NH_ENABLE_RATE_LIMITING"].lower() in ("true", "1", "yes")
            )

        if "GEMINI_APPROVAL_MODE" in os.environ:
            config_dict.setdefault("orchestrator", {})["approval_mode"] = os.environ[
                "GEMINI_APPROVAL_MODE"
            ]

        # Path settings
        if "NH_REPO_ROOT" in os.environ:
            config_dict.setdefault("paths", {})["repo_root"] = os.environ["NH_REPO_ROOT"]

        if "NH_DATA_DIR" in os.environ:
            config_dict.setdefault("paths", {})["data_dir"] = os.environ["NH_DATA_DIR"]

        if "NH_LOGS_DIR" in os.environ:
            config_dict.setdefault("paths", {})["logs_dir"] = os.environ["NH_LOGS_DIR"]

        # Registry settings
        if "NH_REGISTRY_BACKEND" in os.environ:
            config_dict.setdefault("registry", {})["backend"] = os.environ[
                "NH_REGISTRY_BACKEND"
            ]

        if "NH_REGISTRY_SQLITE_PATH" in os.environ:
            config_dict.setdefault("registry", {})["sqlite_path"] = os.environ[
                "NH_REGISTRY_SQLITE_PATH"
            ]

        if "NH_REGISTRY_TSV_PATH" in os.environ:
            config_dict.setdefault("registry", {})["tsv_path"] = os.environ[
                "NH_REGISTRY_TSV_PATH"
            ]

        # Cloudflare settings
        if "CLOUDFLARE_API_TOKEN" in os.environ:
            config_dict.setdefault("cloudflare", {})["api_token"] = os.environ[
                "CLOUDFLARE_API_TOKEN"
            ]

        if "CLOUDFLARE_ACCOUNT_ID" in os.environ:
            config_dict.setdefault("cloudflare", {})["account_id"] = os.environ[
                "CLOUDFLARE_ACCOUNT_ID"
            ]

        if "CLOUDFLARE_PROJECT_NAME" in os.environ:
            config_dict.setdefault("cloudflare", {})["project_name"] = os.environ[
                "CLOUDFLARE_PROJECT_NAME"
            ]

        return config_dict

    def get_registry_path(self) -> Path:
        """Get registry path based on configured backend.

        Returns:
            Path to registry file (TSV or SQLite)
        """
        config = self.load()

        if config.registry.backend == "sqlite":
            path = self.repo_root / config.registry.sqlite_path
        else:
            path = self.repo_root / config.registry.tsv_path

        return path

    def get_registry_backend(self) -> str:
        """Get configured registry backend type.

        Returns:
            Backend type ('tsv' or 'sqlite')
        """
        config = self.load()
        return config.registry.backend

    def create_sample_config(self, output_path: Optional[Path] = None) -> Path:
        """Create a sample .nh.toml configuration file.

        Args:
            output_path: Path to write config (defaults to repo_root/.nh.toml)

        Returns:
            Path to created config file
        """
        if output_path is None:
            output_path = self.config_path

        sample_config = """# NeuroHelix Orchestrator Configuration
# This file configures the Python orchestrator behavior.
# Settings can be overridden by environment variables (see README).

[orchestrator]
# Default Gemini model for prompts
default_model = "gemini-2.5-pro"

# Maximum parallel jobs for concurrent execution
max_parallel_jobs = 4

# Enable rate limiting to avoid API quota exhaustion
enable_rate_limiting = true

# Gemini CLI approval mode (yolo, interactive, or conservative)
approval_mode = "yolo"

[paths]
# Repository root (defaults to current directory if not set)
# repo_root = "/path/to/neurohelix"

# Custom data directory (defaults to repo_root/data)
# data_dir = "/path/to/data"

# Custom logs directory (defaults to repo_root/logs)
# logs_dir = "/path/to/logs"

[registry]
# Registry backend: "tsv" or "sqlite"
backend = "tsv"

# Path to SQLite database (relative to repo_root)
sqlite_path = "config/prompts.db"

# Path to TSV registry (relative to repo_root)
tsv_path = "config/prompts.tsv"

[cloudflare]
# Cloudflare API token (can also use CLOUDFLARE_API_TOKEN env var)
# api_token = "${CLOUDFLARE_API_TOKEN}"

# Cloudflare account ID (optional)
# account_id = "your-account-id"

# Cloudflare Pages project name
project_name = "neurohelix-site"
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(sample_config)
        return output_path


def get_config(repo_root: Optional[Path] = None) -> NHConfig:
    """Get global configuration instance.

    Args:
        repo_root: Repository root directory

    Returns:
        NHConfig object
    """
    loader = ConfigLoader(repo_root)
    return loader.load()
