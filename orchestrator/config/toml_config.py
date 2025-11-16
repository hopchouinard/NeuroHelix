"""Environment-first configuration loader with legacy .nh.toml support."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # Fallback for older Python

from dotenv import load_dotenv
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


class MaintenanceConfig(BaseModel):
    """Maintenance operation options."""

    require_clean_git: bool = Field(
        default=True,
        description="Require clean git working tree before destructive commands",
    )


class NotifierConfig(BaseModel):
    """Notifier hook configuration."""

    enable_success: bool = Field(default=False, description="Call success notifier script")
    enable_failure: bool = Field(default=False, description="Call failure notifier script")
    success_script: str = Field(
        default="scripts/notifiers/notify.sh",
        description="Path to success notifier script",
    )
    failure_script: str = Field(
        default="scripts/notifiers/notify_failures.sh",
        description="Path to failure notifier script",
    )


class ConfigLoader:
    """Configuration loader with precedence: CLI flags > .env* > legacy files > defaults."""

    DEFAULT_CONFIG_NAME = ".env.local"
    ENV_FILENAMES = (".env", ".env.local", ".env.dev")

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize config loader.

        Args:
            repo_root: Repository root directory (defaults to current working directory)
        """
        self.repo_root = repo_root or Path.cwd()
        self.config_path = self.repo_root / self.DEFAULT_CONFIG_NAME
        self.legacy_config_path = self.repo_root / ".nh.toml"
        self._config: Optional[NHConfig] = None
        self._env_loaded = False
        self._override_env = False

    def load(self, reload: bool = False) -> NHConfig:
        """Load configuration with precedence.

        Args:
            reload: Force reload from file

        Returns:
            NHConfig object with merged settings
        """
        if self._config is not None and not reload:
            return self._config

        if reload:
            self._config = None
            self._env_loaded = False
            self._override_env = True

        # Load .env files once
        self._load_env_files()

        config_dict: dict[str, Any] = {}

        # Legacy fallback: .nh.toml
        if self.legacy_config_path.exists():
            warnings.warn(
                ".nh.toml is deprecated. Move settings into .env/.env.local",
                DeprecationWarning,
                stacklevel=2,
            )
            with open(self.legacy_config_path, "rb") as f:
                config_dict = tomllib.load(f)

        config_dict = self._apply_env_overrides(config_dict)

        # Parse into Pydantic model
        self._config = NHConfig(**config_dict)
        return self._config

    def _load_env_files(self) -> None:
        """Load .env stack into process environment."""

        if self._env_loaded:
            return

        for filename in self.ENV_FILENAMES:
            env_path = self.repo_root / filename
            if env_path.exists():
                load_dotenv(env_path, override=self._override_env)

        self._env_loaded = True
        self._override_env = False

    def _apply_env_overrides(self, config_dict: dict) -> dict:
        """Apply environment variable overrides."""
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

        # Maintenance settings
        if "NH_REQUIRE_CLEAN_GIT" in os.environ:
            config_dict.setdefault("maintenance", {})["require_clean_git"] = (
                os.environ["NH_REQUIRE_CLEAN_GIT"].lower() in ("true", "1", "yes")
            )

        # Notifier settings (map from legacy env vars)
        if "ENABLE_NOTIFICATIONS" in os.environ:
            config_dict.setdefault("notifier", {})["enable_success"] = (
                os.environ["ENABLE_NOTIFICATIONS"].lower() in ("true", "1", "yes")
            )

        if "ENABLE_FAILURE_NOTIFICATIONS" in os.environ:
            config_dict.setdefault("notifier", {})["enable_failure"] = (
                os.environ["ENABLE_FAILURE_NOTIFICATIONS"].lower() in ("true", "1", "yes")
            )

        if "NH_SUCCESS_NOTIFIER_SCRIPT" in os.environ:
            config_dict.setdefault("notifier", {})["success_script"] = os.environ[
                "NH_SUCCESS_NOTIFIER_SCRIPT"
            ]

        if "NH_FAILURE_NOTIFIER_SCRIPT" in os.environ:
            config_dict.setdefault("notifier", {})["failure_script"] = os.environ[
                "NH_FAILURE_NOTIFIER_SCRIPT"
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
        """Create a sample .env configuration file."""

        if output_path is None:
            output_path = self.config_path

        sample_config = """# NeuroHelix environment configuration (.env.local)
# Copy this file to .env.local and update values as needed.

# Orchestrator defaults
NH_DEFAULT_MODEL=gemini-2.5-pro
NH_MAX_PARALLEL_JOBS=4
NH_ENABLE_RATE_LIMITING=true
GEMINI_APPROVAL_MODE=yolo

# Paths
NH_REPO_ROOT=
NH_DATA_DIR=
NH_LOGS_DIR=

# Registry
NH_REGISTRY_BACKEND=tsv
NH_REGISTRY_TSV_PATH=config/prompts.tsv
NH_REGISTRY_SQLITE_PATH=config/prompts.db

# Cloudflare
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_PROJECT_NAME=neurohelix-site

# Maintenance
NH_REQUIRE_CLEAN_GIT=true

# Notifiers
ENABLE_NOTIFICATIONS=false
ENABLE_FAILURE_NOTIFICATIONS=false
NH_SUCCESS_NOTIFIER_SCRIPT=scripts/notifiers/notify.sh
NH_FAILURE_NOTIFIER_SCRIPT=scripts/notifiers/notify_failures.sh
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(sample_config.strip() + "\n", encoding="utf-8")
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
class NHConfig(BaseModel):
    """Complete NH configuration."""

    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    cloudflare: CloudflareConfig = Field(default_factory=CloudflareConfig)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)
    notifier: NotifierConfig = Field(default_factory=NotifierConfig)
