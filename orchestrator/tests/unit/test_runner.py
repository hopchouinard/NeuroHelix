"""Unit tests for RunnerService."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from config.settings_schema import PromptPolicy, WaveType, ConcurrencyClass
from services.runner import RunnerService
from adapters.gemini_cli import GeminiCLIAdapter, GeminiCLIError


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_gemini_adapter():
    """Create mock Gemini adapter."""
    return MagicMock(spec=GeminiCLIAdapter)


@pytest.fixture
def mock_ledger_service():
    """Create mock ledger service."""
    return MagicMock()


@pytest.fixture
def mock_manifest_service():
    """Create mock manifest service."""
    return MagicMock()


@pytest.fixture
def runner(temp_repo_root, mock_gemini_adapter, mock_ledger_service, mock_manifest_service):
    """Create RunnerService instance."""
    return RunnerService(
        repo_root=temp_repo_root,
        gemini_adapter=mock_gemini_adapter,
        ledger_service=mock_ledger_service,
        manifest_service=mock_manifest_service,
    )


@pytest.fixture
def sample_prompts():
    """Create sample prompt policies."""
    return [
        PromptPolicy(
            prompt_id="search_1",
            title="Search 1",
            wave=WaveType.SEARCH,
            category="Research",
            model="gemini-2.5-flash",
            temperature=0.7,
            token_budget=32000,
            timeout_sec=120,
            max_retries=3,
            concurrency_class=ConcurrencyClass.MEDIUM,
            expected_outputs="search_1.md",
            prompt="Search prompt 1",
        ),
        PromptPolicy(
            prompt_id="search_2",
            title="Search 2",
            wave=WaveType.SEARCH,
            category="Research",
            model="gemini-2.5-flash",
            temperature=0.7,
            token_budget=32000,
            timeout_sec=120,
            max_retries=3,
            concurrency_class=ConcurrencyClass.LOW,
            expected_outputs="search_2.md",
            prompt="Search prompt 2",
        ),
        PromptPolicy(
            prompt_id="aggregator_1",
            title="Aggregator 1",
            wave=WaveType.AGGREGATOR,
            category="Synthesis",
            model="gemini-2.5-flash",
            temperature=0.7,
            token_budget=64000,
            timeout_sec=300,
            max_retries=3,
            concurrency_class=ConcurrencyClass.SEQUENTIAL,
            expected_outputs="report_{date}.md",
            prompt="Aggregator prompt",
        ),
    ]


def test_runner_initialization(runner, temp_repo_root):
    """Test runner initialization."""
    assert runner.repo_root == temp_repo_root
    assert runner.gemini_adapter is not None
    assert runner.ledger_service is not None
    assert runner.manifest_service is not None

    # Check pool sizes
    assert runner.pool_sizes[ConcurrencyClass.SEQUENTIAL] == 1
    assert runner.pool_sizes[ConcurrencyClass.LOW] == 2
    assert runner.pool_sizes[ConcurrencyClass.MEDIUM] == 4
    assert runner.pool_sizes[ConcurrencyClass.HIGH] == 8


def test_execute_wave_filters_prompts(runner, sample_prompts, mock_manifest_service, mock_gemini_adapter):
    """Test that execute_wave filters prompts by wave type."""
    # Setup mocks
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}
    mock_gemini_adapter.execute_prompt.return_value = (
        0, "Success", datetime.now(), datetime.now(), 0
    )

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
        )

    # Should execute only SEARCH wave prompts (2 of 3)
    assert len(completed) == 2
    assert len(failed) == 0
    assert "search_1" in completed
    assert "search_2" in completed


def test_execute_wave_empty_wave(runner, sample_prompts):
    """Test execute_wave with no prompts for wave."""
    completed, failed = runner.execute_wave(
        wave=WaveType.RENDER,  # No RENDER prompts in sample
        prompts=sample_prompts,
        date="2025-11-14",
        run_id="test-run",
        registry_hash="abc123",
        config_fingerprint="def456",
    )

    assert completed == []
    assert failed == []


def test_execute_wave_skips_completed_prompts(
    runner, sample_prompts, mock_manifest_service, mock_ledger_service
):
    """Test that completed prompts are skipped."""
    # Mock all prompts as completed
    mock_manifest_service.is_completed.return_value = True

    completed, failed = runner.execute_wave(
        wave=WaveType.SEARCH,
        prompts=sample_prompts,
        date="2025-11-14",
        run_id="test-run",
        registry_hash="abc123",
        config_fingerprint="def456",
    )

    # All should be skipped but counted as completed
    assert len(completed) == 2
    assert len(failed) == 0

    # Verify skip messages were logged
    skip_calls = [
        call for call in mock_ledger_service.write_run_log.call_args_list
        if "Skipping" in str(call)
    ]
    assert len(skip_calls) == 2


def test_execute_wave_handles_failures(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter, mock_ledger_service
):
    """Test that failures are tracked."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}

    # First prompt succeeds, second fails
    mock_gemini_adapter.execute_prompt.side_effect = [
        (0, "Success", datetime.now(), datetime.now(), 0),
        (1, "Error", datetime.now(), datetime.now(), 0),
    ]

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
        )

    assert len(completed) == 1
    assert len(failed) == 1


def test_execute_wave_handles_exceptions(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter
):
    """Test that exceptions during execution are handled."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}

    # First prompt raises exception
    mock_gemini_adapter.execute_prompt.side_effect = [
        GeminiCLIError("CLI failed"),
        (0, "Success", datetime.now(), datetime.now(), 0),
    ]

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
        )

    assert len(completed) == 1
    assert len(failed) == 1


def test_execute_wave_dry_run(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter
):
    """Test dry run mode."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}
    mock_gemini_adapter.execute_prompt.return_value = (
        0, "[DRY RUN]", datetime.now(), datetime.now(), 0
    )

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
            dry_run=True,
        )

    # Verify gemini_adapter was called with dry_run=True
    assert mock_gemini_adapter.execute_prompt.call_count == 2
    for call_obj in mock_gemini_adapter.execute_prompt.call_args_list:
        assert call_obj[1]["dry_run"] is True


def test_get_max_workers_sequential(runner, sample_prompts):
    """Test max workers with sequential prompts."""
    # Aggregator has SEQUENTIAL concurrency
    aggregator_prompts = [p for p in sample_prompts if p.wave == WaveType.AGGREGATOR]

    max_workers = runner._get_max_workers(aggregator_prompts)
    assert max_workers == 1


def test_get_max_workers_mixed(runner, sample_prompts):
    """Test max workers with mixed concurrency classes."""
    # Search prompts have LOW (2) and MEDIUM (4)
    search_prompts = [p for p in sample_prompts if p.wave == WaveType.SEARCH]

    max_workers = runner._get_max_workers(search_prompts)
    # Should use minimum: min(4, 2) = 2
    assert max_workers == 2


def test_get_max_workers_empty(runner):
    """Test max workers with empty list."""
    max_workers = runner._get_max_workers([])
    assert max_workers == 1


def test_get_output_path_search_wave(runner, temp_repo_root):
    """Test output path for search wave."""
    prompt = PromptPolicy(
        prompt_id="test",
        title="Test",
        wave=WaveType.SEARCH,
        category="Research",
        model="gemini-2.5-flash",
        temperature=0.7,
        token_budget=32000,
        timeout_sec=120,
        max_retries=3,
        concurrency_class=ConcurrencyClass.MEDIUM,
        expected_outputs="test_output.md",
        prompt="Test",
    )

    path = runner._get_output_path(prompt, "2025-11-14")
    expected = temp_repo_root / "data" / "outputs" / "daily" / "2025-11-14" / "test_output.md"
    assert path == expected


def test_get_output_path_aggregator_wave(runner, temp_repo_root):
    """Test output path for aggregator wave."""
    prompt = PromptPolicy(
        prompt_id="test",
        title="Test",
        wave=WaveType.AGGREGATOR,
        category="Synthesis",
        model="gemini-2.5-flash",
        temperature=0.7,
        token_budget=64000,
        timeout_sec=300,
        max_retries=3,
        concurrency_class=ConcurrencyClass.SEQUENTIAL,
        expected_outputs="report_{date}.md",
        prompt="Test",
    )

    path = runner._get_output_path(prompt, "2025-11-14")
    expected = temp_repo_root / "data" / "reports" / "report_2025-11-14.md"
    assert path == expected


def test_get_output_path_tagger_wave(runner, temp_repo_root):
    """Test output path for tagger wave."""
    prompt = PromptPolicy(
        prompt_id="test",
        title="Test",
        wave=WaveType.TAGGER,
        category="Tagging",
        model="gemini-2.5-flash",
        temperature=0.7,
        token_budget=32000,
        timeout_sec=120,
        max_retries=3,
        concurrency_class=ConcurrencyClass.SEQUENTIAL,
        expected_outputs="tags_{date}.json",
        prompt="Test",
    )

    path = runner._get_output_path(prompt, "2025-11-14")
    expected = temp_repo_root / "data" / "publishing" / "tags_2025-11-14.json"
    assert path == expected


def test_get_output_path_render_wave(runner, temp_repo_root):
    """Test output path for render wave."""
    prompt = PromptPolicy(
        prompt_id="test",
        title="Test",
        wave=WaveType.RENDER,
        category="Rendering",
        model="gemini-2.5-flash",
        temperature=0.7,
        token_budget=32000,
        timeout_sec=120,
        max_retries=3,
        concurrency_class=ConcurrencyClass.SEQUENTIAL,
        expected_outputs="dashboard_{date}.html",
        prompt="Test",
    )

    path = runner._get_output_path(prompt, "2025-11-14")
    expected = temp_repo_root / "dashboards" / "dashboard_2025-11-14.html"
    assert path == expected


def test_get_output_path_export_wave(runner, temp_repo_root):
    """Test output path for export wave."""
    prompt = PromptPolicy(
        prompt_id="test",
        title="Test",
        wave=WaveType.EXPORT,
        category="Export",
        model="gemini-2.5-flash",
        temperature=0.7,
        token_budget=32000,
        timeout_sec=120,
        max_retries=3,
        concurrency_class=ConcurrencyClass.SEQUENTIAL,
        expected_outputs="{date}.json",
        prompt="Test",
    )

    path = runner._get_output_path(prompt, "2025-11-14")
    expected = temp_repo_root / "data" / "publishing" / "2025-11-14.json"
    assert path == expected


def test_load_prompt_and_context(runner, sample_prompts):
    """Test loading prompt text and context."""
    prompt = sample_prompts[0]

    prompt_text, context_data = runner._load_prompt_and_context(
        prompt, sample_prompts, "2025-11-14"
    )

    assert prompt_text == prompt.prompt
    # Currently no context is added
    assert context_data is None


def test_execute_wave_writes_completion_markers(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter
):
    """Test that completion markers are written."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}
    mock_gemini_adapter.execute_prompt.return_value = (
        0, "Success", datetime.now(), datetime.now(), 0
    )

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
        )

    # Verify completion markers were written
    assert mock_manifest_service.write_completion_marker.call_count == 2


def test_execute_wave_writes_ledger_entries(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter, mock_ledger_service
):
    """Test that ledger entries are written."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}
    mock_gemini_adapter.execute_prompt.return_value = (
        0, "Success", datetime.now(), datetime.now(), 0
    )

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
        )

    # Verify ledger entries were written
    assert mock_ledger_service.write_ledger_entry.call_count == 2


def test_execute_wave_forced_prompts(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter
):
    """Test forced prompts override completion check."""
    # Mock first prompt as completed
    mock_manifest_service.is_completed.side_effect = [
        False,  # First call (forced) returns False
        True,   # Second call (not forced) returns True
    ]
    mock_manifest_service.build_dependency_graph.return_value = {}
    mock_gemini_adapter.execute_prompt.return_value = (
        0, "Success", datetime.now(), datetime.now(), 0
    )

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
            forced_prompts=["search_1"],  # Force search_1
        )

    # One executed, one skipped
    assert len(completed) == 2
    assert len(failed) == 0

    # Verify is_completed was called with forced_prompts
    for call_obj in mock_manifest_service.is_completed.call_args_list:
        assert "forced_prompts" in call_obj[1]


def test_execute_wave_forced_waves(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter
):
    """Test forced waves override completion check."""
    mock_manifest_service.is_completed.side_effect = [False, False]
    mock_manifest_service.build_dependency_graph.return_value = {}
    mock_gemini_adapter.execute_prompt.return_value = (
        0, "Success", datetime.now(), datetime.now(), 0
    )

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
            forced_waves=[WaveType.SEARCH],  # Force entire wave
        )

    assert len(completed) == 2
    assert len(failed) == 0

    # Verify is_completed was called with forced_waves
    for call_obj in mock_manifest_service.is_completed.call_args_list:
        assert "forced_waves" in call_obj[1]


def test_execute_single_prompt_error_handling(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter, mock_ledger_service
):
    """Test error handling in single prompt execution."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}

    # Simulate CLI error
    mock_gemini_adapter.execute_prompt.side_effect = GeminiCLIError("Test error")

    result = runner._execute_single_prompt(
        prompt=sample_prompts[0],
        all_prompts=sample_prompts,
        date="2025-11-14",
        run_id="test-run",
        registry_hash="abc123",
        config_fingerprint="def456",
        forced_prompts=None,
        forced_waves=None,
        dry_run=False,
    )

    # Should return False on error
    assert result is False

    # Verify error marker was written
    mock_manifest_service.write_completion_marker.assert_called_once()
    call_kwargs = mock_manifest_service.write_completion_marker.call_args[1]
    assert call_kwargs["exit_code"] == 1
    assert "error_message" in call_kwargs

    # Verify error ledger entry was written
    mock_ledger_service.write_ledger_entry.assert_called_once()
    call_kwargs = mock_ledger_service.write_ledger_entry.call_args[1]
    assert call_kwargs["success"] is False
    assert "error_message" in call_kwargs


def test_execute_wave_concurrency(
    runner, sample_prompts, mock_manifest_service, mock_gemini_adapter
):
    """Test that prompts execute concurrently."""
    mock_manifest_service.is_completed.return_value = False
    mock_manifest_service.build_dependency_graph.return_value = {}

    # Track execution order
    execution_times = []

    def mock_execute(*args, **kwargs):
        execution_times.append(datetime.now())
        import time
        time.sleep(0.1)  # Simulate work
        return (0, "Success", datetime.now(), datetime.now(), 0)

    mock_gemini_adapter.execute_prompt.side_effect = mock_execute

    with patch("adapters.filesystem.compute_file_hash", return_value="hash123"):
        completed, failed = runner.execute_wave(
            wave=WaveType.SEARCH,
            prompts=sample_prompts,
            date="2025-11-14",
            run_id="test-run",
            registry_hash="abc123",
            config_fingerprint="def456",
        )

    # Both prompts should execute
    assert len(completed) == 2
    assert len(execution_times) == 2
