"""Unit tests for TOML configuration loader."""

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
def sample_config_content():
    """Sample .nh.toml content."""
    return """[orchestrator]
default_model = "gemini-2.5-flash"
max_parallel_jobs = 8
enable_rate_limiting = false
approval_mode = "conservative"

[paths]
repo_root = "/custom/path"
data_dir = "/custom/data"

[registry]
backend = "sqlite"
sqlite_path = "custom.db"

[cloudflare]
project_name = "custom-project"
"""


def test_config_loader_initialization(temp_repo):
    """Test config loader initialization."""
    loader = ConfigLoader(temp_repo)

    assert loader.repo_root == temp_repo
    assert loader.config_path == temp_repo / ".nh.toml"


def test_load_default_config(temp_repo):
    """Test loading default config when no file exists."""
    loader = ConfigLoader(temp_repo)
    config = loader.load()

    # Should use defaults
    assert config.orchestrator.default_model == "gemini-2.5-pro"
    assert config.orchestrator.max_parallel_jobs == 4
    assert config.orchestrator.enable_rate_limiting is True
    assert config.registry.backend == "tsv"


def test_load_config_from_file(temp_repo, sample_config_content):
    """Test loading config from .nh.toml file."""
    # Create config file
    config_path = temp_repo / ".nh.toml"
    config_path.write_text(sample_config_content)

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    # Should use values from file
    assert config.orchestrator.default_model == "gemini-2.5-flash"
    assert config.orchestrator.max_parallel_jobs == 8
    assert config.orchestrator.enable_rate_limiting is False
    assert config.orchestrator.approval_mode == "conservative"
    assert config.paths.repo_root == "/custom/path"
    assert config.registry.backend == "sqlite"
    assert config.registry.sqlite_path == "custom.db"
    assert config.cloudflare.project_name == "custom-project"


def test_env_var_overrides(temp_repo, sample_config_content, monkeypatch):
    """Test that environment variables override .nh.toml."""
    # Create config file
    config_path = temp_repo / ".nh.toml"
    config_path.write_text(sample_config_content)

    # Set environment variables
    monkeypatch.setenv("NH_DEFAULT_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("NH_MAX_PARALLEL_JOBS", "16")
    monkeypatch.setenv("NH_ENABLE_RATE_LIMITING", "true")
    monkeypatch.setenv("NH_REGISTRY_BACKEND", "tsv")

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    # Env vars should override file
    assert config.orchestrator.default_model == "gemini-2.5-pro"
    assert config.orchestrator.max_parallel_jobs == 16
    assert config.orchestrator.enable_rate_limiting is True
    assert config.registry.backend == "tsv"


def test_config_caching(temp_repo):
    """Test that config is cached and reused."""
    loader = ConfigLoader(temp_repo)

    config1 = loader.load()
    config2 = loader.load()

    # Should return same instance
    assert config1 is config2


def test_config_reload(temp_repo, sample_config_content):
    """Test forcing config reload."""
    loader = ConfigLoader(temp_repo)

    # Load default config
    config1 = loader.load()
    assert config1.orchestrator.max_parallel_jobs == 4

    # Create config file
    config_path = temp_repo / ".nh.toml"
    config_path.write_text(sample_config_content)

    # Reload should pick up new file
    config2 = loader.load(reload=True)
    assert config2.orchestrator.max_parallel_jobs == 8


def test_get_registry_path_tsv(temp_repo):
    """Test getting registry path for TSV backend."""
    config_path = temp_repo / ".nh.toml"
    config_path.write_text('[registry]\nbackend = "tsv"\ntsv_path = "custom.tsv"')

    loader = ConfigLoader(temp_repo)
    registry_path = loader.get_registry_path()

    assert registry_path == temp_repo / "custom.tsv"


def test_get_registry_path_sqlite(temp_repo):
    """Test getting registry path for SQLite backend."""
    config_path = temp_repo / ".nh.toml"
    config_path.write_text('[registry]\nbackend = "sqlite"\nsqlite_path = "custom.db"')

    loader = ConfigLoader(temp_repo)
    registry_path = loader.get_registry_path()

    assert registry_path == temp_repo / "custom.db"


def test_get_registry_backend(temp_repo):
    """Test getting registry backend type."""
    config_path = temp_repo / ".nh.toml"
    config_path.write_text('[registry]\nbackend = "sqlite"')

    loader = ConfigLoader(temp_repo)
    backend = loader.get_registry_backend()

    assert backend == "sqlite"


def test_create_sample_config(temp_repo):
    """Test creating sample config file."""
    loader = ConfigLoader(temp_repo)
    config_path = loader.create_sample_config()

    assert config_path.exists()
    content = config_path.read_text()

    # Should contain all sections
    assert "[orchestrator]" in content
    assert "[paths]" in content
    assert "[registry]" in content
    assert "[cloudflare]" in content

    # Should contain comments
    assert "#" in content


def test_create_sample_config_custom_path(temp_repo):
    """Test creating sample config at custom path."""
    loader = ConfigLoader(temp_repo)
    custom_path = temp_repo / "custom.toml"

    created_path = loader.create_sample_config(custom_path)

    assert created_path == custom_path
    assert custom_path.exists()


def test_boolean_env_var_parsing(temp_repo, monkeypatch):
    """Test parsing boolean environment variables."""
    # Test various true values
    for true_value in ["true", "1", "yes", "True", "TRUE", "YES"]:
        monkeypatch.setenv("NH_ENABLE_RATE_LIMITING", true_value)
        loader = ConfigLoader(temp_repo)
        loader._config = None  # Reset cache
        config = loader.load()
        assert config.orchestrator.enable_rate_limiting is True

    # Test false values
    for false_value in ["false", "0", "no", "False", "FALSE", "NO"]:
        monkeypatch.setenv("NH_ENABLE_RATE_LIMITING", false_value)
        loader = ConfigLoader(temp_repo)
        loader._config = None  # Reset cache
        config = loader.load()
        assert config.orchestrator.enable_rate_limiting is False


def test_cloudflare_env_vars(temp_repo, monkeypatch):
    """Test Cloudflare-specific environment variables."""
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_PROJECT_NAME", "test-project")

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    assert config.cloudflare.api_token == "test-token"
    assert config.cloudflare.account_id == "test-account"
    assert config.cloudflare.project_name == "test-project"


def test_gemini_approval_mode_env_var(temp_repo, monkeypatch):
    """Test GEMINI_APPROVAL_MODE environment variable."""
    monkeypatch.setenv("GEMINI_APPROVAL_MODE", "interactive")

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    assert config.orchestrator.approval_mode == "interactive"


def test_pydantic_validation(temp_repo):
    """Test that Pydantic validates values."""
    # Invalid max_parallel_jobs (too high)
    config_path = temp_repo / ".nh.toml"
    config_path.write_text("[orchestrator]\nmax_parallel_jobs = 100")

    loader = ConfigLoader(temp_repo)

    with pytest.raises(Exception):  # Pydantic will raise validation error
        loader.load()


def test_get_config_function(temp_repo):
    """Test global get_config function."""
    config = get_config(temp_repo)

    assert isinstance(config, NHConfig)
    assert config.orchestrator.default_model is not None


def test_partial_config_file(temp_repo):
    """Test loading config with only some sections defined."""
    config_path = temp_repo / ".nh.toml"
    config_path.write_text('[orchestrator]\ndefault_model = "custom-model"')

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    # Should have custom value
    assert config.orchestrator.default_model == "custom-model"

    # Should have defaults for other sections
    assert config.registry.backend == "tsv"
    assert config.cloudflare.project_name == "neurohelix-site"


def test_empty_config_file(temp_repo):
    """Test loading empty config file."""
    config_path = temp_repo / ".nh.toml"
    config_path.write_text("")

    loader = ConfigLoader(temp_repo)
    config = loader.load()

    # Should use all defaults
    assert config.orchestrator.default_model == "gemini-2.5-pro"
    assert config.registry.backend == "tsv"
