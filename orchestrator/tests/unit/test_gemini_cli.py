"""Unit tests for GeminiCLIAdapter."""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from adapters.gemini_cli import (
    GeminiCLIAdapter,
    GeminiCLIError,
    RateLimitDetectedError,
)
from config.settings_schema import PromptPolicy, WaveType, ConcurrencyClass
from services.rate_limiter import RateLimitError


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_policy():
    """Create a sample prompt policy."""
    return PromptPolicy(
        prompt_id="test_prompt",
        title="Test Prompt",
        wave=WaveType.SEARCH,
        category="Research",
        model="gemini-2.5-flash",
        temperature=0.7,
        token_budget=32000,
        timeout_sec=120,
        max_retries=3,
        concurrency_class=ConcurrencyClass.MEDIUM,
        expected_outputs="test_prompt.md",
        prompt="Test prompt text",
    )


@pytest.fixture
def adapter_no_rate_limit(temp_repo_root):
    """Create adapter with rate limiting disabled."""
    return GeminiCLIAdapter(temp_repo_root, enable_rate_limiting=False)


@pytest.fixture
def adapter_with_rate_limit(temp_repo_root):
    """Create adapter with rate limiting enabled."""
    return GeminiCLIAdapter(temp_repo_root, enable_rate_limiting=True)


def test_adapter_initialization_no_rate_limit(temp_repo_root):
    """Test adapter initialization without rate limiting."""
    adapter = GeminiCLIAdapter(temp_repo_root, enable_rate_limiting=False)

    assert adapter.repo_root == temp_repo_root
    assert adapter.rate_limiter is None
    assert adapter.enable_rate_limiting is False


def test_adapter_initialization_with_rate_limit(temp_repo_root):
    """Test adapter initialization with rate limiting."""
    adapter = GeminiCLIAdapter(temp_repo_root, enable_rate_limiting=True)

    assert adapter.repo_root == temp_repo_root
    assert adapter.rate_limiter is not None
    assert adapter.enable_rate_limiting is True


@patch("adapters.gemini_cli.subprocess.run")
def test_execute_prompt_success(mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test successful prompt execution."""
    output_path = temp_repo_root / "output.md"

    # Mock successful execution
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Test output content"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    exit_code, output, started_at, ended_at, retries = adapter_no_rate_limit.execute_prompt(
        policy=sample_policy,
        prompt_text="Test prompt",
        output_path=output_path,
    )

    assert exit_code == 0
    assert output == "Test output content"
    assert retries == 0
    assert isinstance(started_at, datetime)
    assert isinstance(ended_at, datetime)
    assert ended_at >= started_at

    # Verify output file was written
    assert output_path.exists()
    assert output_path.read_text() == "Test output content"

    # Verify subprocess.run was called correctly
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args[0][0] == ["gemini", "--model", "gemini-2.5-flash", "Test prompt"]


@patch("adapters.gemini_cli.subprocess.run")
def test_execute_prompt_with_context(mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test prompt execution with context data."""
    output_path = temp_repo_root / "output.md"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Output with context"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    adapter_no_rate_limit.execute_prompt(
        policy=sample_policy,
        prompt_text="Base prompt",
        output_path=output_path,
        context_data="Additional context",
    )

    # Verify context was appended to prompt
    call_args = mock_run.call_args
    called_prompt = call_args[0][0][3]  # Fourth argument is the prompt
    assert "Base prompt" in called_prompt
    assert "Additional context" in called_prompt


def test_execute_prompt_dry_run(adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test dry run mode doesn't execute CLI."""
    output_path = temp_repo_root / "output.md"

    exit_code, output, started_at, ended_at, retries = adapter_no_rate_limit.execute_prompt(
        policy=sample_policy,
        prompt_text="Test prompt",
        output_path=output_path,
        dry_run=True,
    )

    assert exit_code == 0
    assert "[DRY RUN]" in output
    assert retries == 0


@patch("adapters.gemini_cli.subprocess.run")
@patch("adapters.gemini_cli.time.sleep")
def test_execute_prompt_retry_on_failure(mock_sleep, mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test retry logic on failures."""
    output_path = temp_repo_root / "output.md"

    # First 2 attempts fail, third succeeds
    failed_result = Mock()
    failed_result.returncode = 1
    failed_result.stdout = ""
    failed_result.stderr = "API error"

    success_result = Mock()
    success_result.returncode = 0
    success_result.stdout = "Success after retry"
    success_result.stderr = ""

    mock_run.side_effect = [failed_result, failed_result, success_result]

    exit_code, output, started_at, ended_at, retries = adapter_no_rate_limit.execute_prompt(
        policy=sample_policy,
        prompt_text="Test prompt",
        output_path=output_path,
    )

    assert exit_code == 0
    assert output == "Success after retry"
    assert retries == 2  # Failed twice before succeeding

    # Verify exponential backoff was used
    assert mock_sleep.call_count == 2
    # First backoff: 2^0 = 1, second backoff: 2^1 = 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@patch("adapters.gemini_cli.subprocess.run")
@patch("adapters.gemini_cli.time.sleep")
def test_execute_prompt_max_retries_exceeded(mock_sleep, mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test failure after max retries."""
    output_path = temp_repo_root / "output.md"

    # All attempts fail
    failed_result = Mock()
    failed_result.returncode = 1
    failed_result.stdout = ""
    failed_result.stderr = "Persistent error"

    mock_run.return_value = failed_result

    with pytest.raises(GeminiCLIError) as exc_info:
        adapter_no_rate_limit.execute_prompt(
            policy=sample_policy,
            prompt_text="Test prompt",
            output_path=output_path,
        )

    assert "after 4 attempts" in str(exc_info.value)  # max_retries=3 means 4 total attempts
    assert "test_prompt" in str(exc_info.value)


@patch("adapters.gemini_cli.subprocess.run")
@patch("adapters.gemini_cli.time.sleep")
def test_execute_prompt_rate_limit_detection(mock_sleep, mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test rate limit error detection and longer backoff."""
    output_path = temp_repo_root / "output.md"

    # First attempt hits rate limit, second succeeds
    rate_limit_result = Mock()
    rate_limit_result.returncode = 1
    rate_limit_result.stdout = ""
    rate_limit_result.stderr = "Error: 429 Too Many Requests - rate limit exceeded"

    success_result = Mock()
    success_result.returncode = 0
    success_result.stdout = "Success after rate limit"
    success_result.stderr = ""

    mock_run.side_effect = [rate_limit_result, success_result]

    exit_code, output, started_at, ended_at, retries = adapter_no_rate_limit.execute_prompt(
        policy=sample_policy,
        prompt_text="Test prompt",
        output_path=output_path,
    )

    assert exit_code == 0
    assert retries == 1

    # Verify longer backoff for rate limits (30 seconds)
    mock_sleep.assert_called_once_with(30)


@patch("adapters.gemini_cli.subprocess.run")
def test_execute_prompt_timeout(mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test timeout handling."""
    output_path = temp_repo_root / "output.md"

    # Simulate timeout
    import subprocess
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["gemini"], timeout=120)

    with pytest.raises(GeminiCLIError) as exc_info:
        adapter_no_rate_limit.execute_prompt(
            policy=sample_policy,
            prompt_text="Test prompt",
            output_path=output_path,
        )

    assert "Timeout" in str(exc_info.value)


@patch("adapters.gemini_cli.subprocess.run")
def test_invoke_gemini_cli_environment_variables(mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test environment variable handling."""
    output_path = temp_repo_root / "output.md"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    adapter_no_rate_limit.execute_prompt(
        policy=sample_policy,
        prompt_text="Test",
        output_path=output_path,
    )

    # Check that GEMINI_APPROVAL_MODE was set in env
    call_kwargs = mock_run.call_args[1]
    env = call_kwargs["env"]
    assert "GEMINI_APPROVAL_MODE" in env
    assert env["GEMINI_APPROVAL_MODE"] == "yolo"


@patch("adapters.gemini_cli.subprocess.run")
def test_check_gemini_cli_available(mock_run, adapter_no_rate_limit):
    """Test checking if Gemini CLI is available."""
    # CLI available
    mock_result = Mock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    assert adapter_no_rate_limit.check_gemini_cli_available() is True

    # CLI not available
    mock_run.side_effect = FileNotFoundError()
    assert adapter_no_rate_limit.check_gemini_cli_available() is False


@patch("adapters.gemini_cli.subprocess.run")
def test_get_gemini_version(mock_run, adapter_no_rate_limit):
    """Test getting Gemini CLI version."""
    # Version available
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "gemini version 1.2.3\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    version = adapter_no_rate_limit.get_gemini_version()
    assert version == "gemini version 1.2.3"

    # Version not available
    mock_run.side_effect = FileNotFoundError()
    assert adapter_no_rate_limit.get_gemini_version() is None


def test_is_rate_limit_error(adapter_no_rate_limit):
    """Test rate limit error detection."""
    # Test various rate limit indicators
    assert adapter_no_rate_limit._is_rate_limit_error("Error 429: Too Many Requests") is True
    assert adapter_no_rate_limit._is_rate_limit_error("Rate limit exceeded") is True
    assert adapter_no_rate_limit._is_rate_limit_error("Quota exceeded for requests") is True
    assert adapter_no_rate_limit._is_rate_limit_error("Too many requests per minute") is True
    assert adapter_no_rate_limit._is_rate_limit_error("Resource exhausted") is True

    # Non-rate-limit errors
    assert adapter_no_rate_limit._is_rate_limit_error("Internal server error") is False
    assert adapter_no_rate_limit._is_rate_limit_error("Invalid API key") is False
    assert adapter_no_rate_limit._is_rate_limit_error("") is False
    assert adapter_no_rate_limit._is_rate_limit_error(None) is False


@patch("adapters.gemini_cli.subprocess.run")
def test_execute_with_rate_limiter_wait(mock_run, temp_repo_root, sample_policy):
    """Test rate limiter integration."""
    output_path = temp_repo_root / "output.md"

    # Create adapter with rate limiting
    adapter = GeminiCLIAdapter(temp_repo_root, enable_rate_limiting=True)

    # Mock rate limiter
    mock_rate_limiter = MagicMock()
    adapter.rate_limiter = mock_rate_limiter

    # Mock successful execution
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    adapter.execute_prompt(
        policy=sample_policy,
        prompt_text="Test",
        output_path=output_path,
    )

    # Verify rate limiter was called
    mock_rate_limiter.wait_if_needed.assert_called_once()


@patch("adapters.gemini_cli.subprocess.run")
def test_execute_with_rate_limit_exceeded(mock_run, temp_repo_root, sample_policy):
    """Test handling when rate limiter daily limit is exceeded."""
    output_path = temp_repo_root / "output.md"

    # Create adapter with rate limiting
    adapter = GeminiCLIAdapter(temp_repo_root, enable_rate_limiting=True)

    # Mock rate limiter that raises RateLimitError
    mock_rate_limiter = MagicMock()
    mock_rate_limiter.wait_if_needed.side_effect = RateLimitError("Daily limit exceeded")
    adapter.rate_limiter = mock_rate_limiter

    with pytest.raises(GeminiCLIError) as exc_info:
        adapter.execute_prompt(
            policy=sample_policy,
            prompt_text="Test",
            output_path=output_path,
        )

    assert "Rate limit exceeded" in str(exc_info.value)


def test_output_directory_creation(adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test that output directories are created automatically."""
    # Create nested output path
    output_path = temp_repo_root / "data" / "outputs" / "nested" / "output.md"

    with patch("adapters.gemini_cli.subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        adapter_no_rate_limit.execute_prompt(
            policy=sample_policy,
            prompt_text="Test",
            output_path=output_path,
        )

    # Verify parent directories were created
    assert output_path.parent.exists()
    assert output_path.exists()


@patch("adapters.gemini_cli.subprocess.run")
def test_execute_prompt_captures_stderr_on_failure(mock_run, adapter_no_rate_limit, sample_policy, temp_repo_root):
    """Test that stderr is captured when execution fails."""
    output_path = temp_repo_root / "output.md"

    # Mock failed execution with stderr
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Detailed error message from CLI"
    mock_run.return_value = mock_result

    with pytest.raises(GeminiCLIError) as exc_info:
        adapter_no_rate_limit.execute_prompt(
            policy=sample_policy,
            prompt_text="Test",
            output_path=output_path,
        )

    # Verify error message includes stderr
    assert "Detailed error message from CLI" in str(exc_info.value)
