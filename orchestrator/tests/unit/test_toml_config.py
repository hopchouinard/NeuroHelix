"""Unit tests for environment-based configuration loader."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from config.toml_config import ConfigLoader, NHConfig, get_config


@pytest.fixture
def temp_repo():
    """Create a temporary repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_env_content():
    return """NH_DEFAULT_MODEL=gemini-2.5-flash
NH_MAX_PARALLEL_JOBS=8
NH_ENABLE_RATE_LIMITING=false
GEMINI_APPROVAL_MODE=conservative
NH_REPO_ROOT=/custom/path
NH_DATA_DIR=/custom/data
NH_REGISTRY_BACKEND=sqlite
NH_REGISTRY_SQLITE_PATH=custom.db
CLOUDFLARE_PROJECT_NAME=custom-project
"""


@pytest.fixture
def cleanup_env(monkeypatch):
    keys: list[str] = []

    def register_from_text(content: str) -> None:
        for line in content.splitlines():
            if not line or line.strip().startswith("#"):
                continue
            key = line.split("=", 1)[0].strip()
            keys.append(key)

    yield register_from_text

    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_config_loader_initialization(temp_repo):
    loader = ConfigLoader(temp_repo)
    assert loader.repo_root == temp_repo
    assert loader.config_path == temp_repo / ".env.local"


def test_load_default_config(temp_repo):
    loader = ConfigLoader(temp_repo)
    config = loader.load()

    assert config.orchestrator.default_model == "gemini-2.5-pro"
    assert config.orchestrator.max_parallel_jobs == 4
    assert config.registry.backend == "tsv"


def test_load_config_from_env_file(temp_repo, sample_env_content, cleanup_env):
    env_path = temp_repo / ".env.local"
    env_path.write_text(sample_env_content)
    cleanup_env(sample_env_content)

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    assert config.orchestrator.default_model == "gemini-2.5-flash"
    assert config.orchestrator.max_parallel_jobs == 8
    assert config.orchestrator.enable_rate_limiting is False
    assert config.orchestrator.approval_mode == "conservative"
    assert config.paths.repo_root == "/custom/path"
    assert config.registry.backend == "sqlite"
    assert config.registry.sqlite_path == "custom.db"
    assert config.cloudflare.project_name == "custom-project"


def test_env_var_overrides(temp_repo, sample_env_content, monkeypatch, cleanup_env):
    env_path = temp_repo / ".env.local"
    env_path.write_text(sample_env_content)
    cleanup_env(sample_env_content)

    monkeypatch.setenv("NH_DEFAULT_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("NH_MAX_PARALLEL_JOBS", "16")
    monkeypatch.setenv("NH_ENABLE_RATE_LIMITING", "true")

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    assert config.orchestrator.default_model == "gemini-2.5-pro"
    assert config.orchestrator.max_parallel_jobs == 16
    assert config.orchestrator.enable_rate_limiting is True


def test_config_caching(temp_repo):
    loader = ConfigLoader(temp_repo)
    config1 = loader.load()
    config2 = loader.load()
    assert config1 is config2


def test_config_reload_reads_updated_env(temp_repo, cleanup_env):
    env_path = temp_repo / ".env.local"
    env_path.write_text("NH_DEFAULT_MODEL=foo")
    cleanup_env("NH_DEFAULT_MODEL=foo")

    loader = ConfigLoader(temp_repo)
    config = loader.load()
    assert config.orchestrator.default_model == "foo"

    cleanup_env("NH_DEFAULT_MODEL=bar")
    env_path.write_text("NH_DEFAULT_MODEL=bar")
    config = loader.load(reload=True)
    assert config.orchestrator.default_model == "bar"


def test_get_registry_path_from_env(temp_repo, cleanup_env):
    cleanup_env("NH_REGISTRY_TSV_PATH=custom.tsv")
    env_path = temp_repo / ".env.local"
    env_path.write_text("NH_REGISTRY_TSV_PATH=custom.tsv")

    loader = ConfigLoader(temp_repo)
    registry_path = loader.get_registry_path()
    assert registry_path == temp_repo / "custom.tsv"


def test_create_sample_config(temp_repo):
    loader = ConfigLoader(temp_repo)
    config_path = loader.create_sample_config()
    assert config_path.exists()
    content = config_path.read_text()
    assert "NH_DEFAULT_MODEL" in content
    assert "CLOUDFLARE_PROJECT_NAME" in content


def test_legacy_toml_triggers_warning(temp_repo):
    legacy_path = temp_repo / ".nh.toml"
    legacy_path.write_text("[orchestrator]\nmax_parallel_jobs = 6")
    loader = ConfigLoader(temp_repo)
    with pytest.warns(DeprecationWarning):
        config = loader.load()
    assert config.orchestrator.max_parallel_jobs == 6


def test_boolean_env_var_parsing(temp_repo, monkeypatch):
    loader = ConfigLoader(temp_repo)
    for true_value in ["true", "1", "yes", "TRUE"]:
        monkeypatch.setenv("NH_ENABLE_RATE_LIMITING", true_value)
        loader._config = None
        loader._env_loaded = False
        config = loader.load()
        assert config.orchestrator.enable_rate_limiting is True
    for false_value in ["false", "0", "no", "FALSE"]:
        monkeypatch.setenv("NH_ENABLE_RATE_LIMITING", false_value)
        loader._config = None
        loader._env_loaded = False
        config = loader.load()
        assert config.orchestrator.enable_rate_limiting is False


def test_cloudflare_env_vars(temp_repo, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_PROJECT_NAME", "test-project")
    loader = ConfigLoader(temp_repo)
    config = loader.load()
    assert config.cloudflare.api_token == "test-token"
    assert config.cloudflare.account_id == "test-account"
    assert config.cloudflare.project_name == "test-project"


def test_pydantic_validation(temp_repo, monkeypatch):
    monkeypatch.setenv("NH_MAX_PARALLEL_JOBS", "100")
    loader = ConfigLoader(temp_repo)
    with pytest.raises(Exception):
        loader.load()


def test_get_config_function(temp_repo):
    config = get_config(temp_repo)
    assert isinstance(config, NHConfig)


def test_partial_env_defaults(temp_repo, cleanup_env):
    env_path = temp_repo / ".env"
    env_path.write_text("NH_DEFAULT_MODEL=custom")
    cleanup_env("NH_DEFAULT_MODEL=custom")

    loader = ConfigLoader(temp_repo)
    config = loader.load()
    assert config.orchestrator.default_model == "custom"
    assert config.registry.backend == "tsv"
