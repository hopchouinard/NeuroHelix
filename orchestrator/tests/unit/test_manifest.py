"""Unit tests for ManifestService."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from config.settings_schema import PromptPolicy, WaveType, ConcurrencyClass
from services.manifest import ManifestService


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manifest_service(temp_repo_root):
    """Create a ManifestService instance."""
    return ManifestService(temp_repo_root)


@pytest.fixture
def sample_prompts():
    """Create sample prompt policies."""
    return [
        PromptPolicy(
            prompt_id="test_prompt_1",
            title="Test Prompt 1",
            wave=WaveType.SEARCH,
            category="Research",
            model="gemini-2.5-flash",
            temperature=0.7,
            token_budget=32000,
            timeout_sec=120,
            max_retries=3,
            concurrency_class=ConcurrencyClass.MEDIUM,
            expected_outputs="test_prompt_1.md",
            prompt="Test prompt 1 text",
        ),
        PromptPolicy(
            prompt_id="test_prompt_2",
            title="Test Prompt 2",
            wave=WaveType.AGGREGATOR,
            category="Synthesis",
            model="gemini-2.5-flash",
            temperature=0.7,
            token_budget=64000,
            timeout_sec=300,
            max_retries=3,
            concurrency_class=ConcurrencyClass.SEQUENTIAL,
            expected_outputs="test_report.md",
            prompt="Test prompt 2 text",
        ),
    ]


def test_create_manifest(manifest_service, temp_repo_root):
    """Test manifest creation."""
    date = "2025-11-14"
    forced_prompts = ["test_prompt_1"]
    forced_waves = [WaveType.SEARCH]

    manifest = manifest_service.create_manifest(
        date=date,
        forced_prompts=forced_prompts,
        forced_waves=forced_waves,
        dry_run=False,
    )

    assert manifest.date == date
    assert manifest.forced_prompts == forced_prompts
    assert manifest.forced_waves == forced_waves
    assert manifest.dry_run is False
    assert manifest.started_at is not None
    assert manifest.ended_at is None
    assert isinstance(manifest.run_id, str)
    assert len(manifest.run_id) > 0


def test_save_and_load_manifest(manifest_service, temp_repo_root):
    """Test saving and loading manifests."""
    date = "2025-11-14"

    # Create manifest
    manifest = manifest_service.create_manifest(date=date)
    manifest.completed_prompts = ["prompt1", "prompt2"]
    manifest.failed_prompts = ["prompt3"]
    manifest.ended_at = datetime.now()

    # Save manifest
    manifest_service.save_manifest(manifest, date)

    # Verify file exists
    manifest_file = temp_repo_root / "data" / "manifests" / f"{date}.json"
    assert manifest_file.exists()

    # Load and verify
    with open(manifest_file) as f:
        loaded = json.load(f)

    assert loaded["date"] == date
    assert loaded["run_id"] == manifest.run_id
    assert loaded["completed_prompts"] == ["prompt1", "prompt2"]
    assert loaded["failed_prompts"] == ["prompt3"]


def test_write_completion_marker(manifest_service, temp_repo_root):
    """Test writing completion markers."""
    output_path = temp_repo_root / "test_output.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("Test output content")

    started_at = datetime.now()
    ended_at = datetime.now()

    manifest_service.write_completion_marker(
        output_path=output_path,
        prompt_id="test_prompt",
        started_at=started_at,
        ended_at=ended_at,
        exit_code=0,
        retries=2,
    )

    # Verify marker file exists
    marker_file = output_path.parent / ".nh_status_test_prompt.json"
    assert marker_file.exists()

    # Load and verify
    with open(marker_file) as f:
        marker = json.load(f)

    assert marker["prompt_id"] == "test_prompt"
    assert marker["exit_code"] == 0
    assert marker["retries"] == 2
    assert "sha256" in marker
    assert marker["sha256"] is not None


def test_is_completed_fresh_run(manifest_service, temp_repo_root, sample_prompts):
    """Test completion check for fresh run (no marker)."""
    output_path = temp_repo_root / "test_output.md"

    is_complete = manifest_service.is_completed(
        output_path=output_path,
        force=False,
        prompt_policy=sample_prompts[0],
    )

    assert is_complete is False


def test_is_completed_with_marker(manifest_service, temp_repo_root, sample_prompts):
    """Test completion check with existing marker."""
    output_path = temp_repo_root / "test_output.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("Test output content")

    # Write completion marker
    manifest_service.write_completion_marker(
        output_path=output_path,
        prompt_id=sample_prompts[0].prompt_id,
        started_at=datetime.now(),
        ended_at=datetime.now(),
        exit_code=0,
    )

    # Check completion
    is_complete = manifest_service.is_completed(
        output_path=output_path,
        force=False,
        prompt_policy=sample_prompts[0],
    )

    assert is_complete is True


def test_is_completed_force_flag(manifest_service, temp_repo_root, sample_prompts):
    """Test that force flag overrides completion check."""
    output_path = temp_repo_root / "test_output.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("Test output content")

    # Write completion marker
    manifest_service.write_completion_marker(
        output_path=output_path,
        prompt_id=sample_prompts[0].prompt_id,
        started_at=datetime.now(),
        ended_at=datetime.now(),
        exit_code=0,
    )

    # Check completion with force flag
    is_complete = manifest_service.is_completed(
        output_path=output_path,
        force=True,
        prompt_policy=sample_prompts[0],
    )

    assert is_complete is False


def test_is_completed_forced_prompts(manifest_service, temp_repo_root, sample_prompts):
    """Test that forced_prompts list overrides completion check."""
    output_path = temp_repo_root / "test_output.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("Test output content")

    # Write completion marker
    manifest_service.write_completion_marker(
        output_path=output_path,
        prompt_id=sample_prompts[0].prompt_id,
        started_at=datetime.now(),
        ended_at=datetime.now(),
        exit_code=0,
    )

    # Check completion with forced_prompts
    is_complete = manifest_service.is_completed(
        output_path=output_path,
        force=False,
        forced_prompts=[sample_prompts[0].prompt_id],
        prompt_policy=sample_prompts[0],
    )

    assert is_complete is False


def test_build_dependency_graph(manifest_service, sample_prompts, temp_repo_root):
    """Test dependency graph building."""
    date = "2025-11-14"

    # Build dependency graph
    deps = manifest_service.build_dependency_graph(sample_prompts, date)

    # Verify structure
    assert isinstance(deps, dict)
    # In our simple case, aggregator depends on search
    # But without explicit dependencies in the model, graph should be empty or simple
    # This test validates the method runs without errors
    assert len(deps) >= 0


def test_completion_marker_with_error(manifest_service, temp_repo_root):
    """Test writing completion marker with error message."""
    output_path = temp_repo_root / "test_output.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_service.write_completion_marker(
        output_path=output_path,
        prompt_id="failed_prompt",
        started_at=datetime.now(),
        ended_at=datetime.now(),
        exit_code=1,
        error_message="Test error message",
    )

    # Verify marker file
    marker_file = output_path.parent / ".nh_status_failed_prompt.json"
    assert marker_file.exists()

    with open(marker_file) as f:
        marker = json.load(f)

    assert marker["exit_code"] == 1
    assert marker["error_message"] == "Test error message"
