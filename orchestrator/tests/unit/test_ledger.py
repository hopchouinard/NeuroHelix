"""Unit tests for LedgerService."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from services.ledger import LedgerService


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def ledger_service(temp_repo_root):
    """Create a LedgerService instance."""
    return LedgerService(temp_repo_root)


def test_write_run_log(ledger_service, temp_repo_root):
    """Test writing to run log."""
    date = "2025-11-14"

    ledger_service.write_run_log(date, "Test log message")

    # Verify log file exists
    log_file = temp_repo_root / "logs" / "runs" / f"{date}.log"
    assert log_file.exists()

    # Verify content
    content = log_file.read_text()
    assert "Test log message" in content
    assert "[INFO]" in content


def test_write_run_log_with_level(ledger_service, temp_repo_root):
    """Test writing to run log with custom level."""
    date = "2025-11-14"

    ledger_service.write_run_log(date, "Error occurred", level="ERROR")

    log_file = temp_repo_root / "logs" / "runs" / f"{date}.log"
    content = log_file.read_text()

    assert "Error occurred" in content
    assert "[ERROR]" in content


def test_write_ledger_entry(ledger_service, temp_repo_root):
    """Test writing ledger entry."""
    date = "2025-11-14"
    run_id = "test-run-123"
    prompt_id = "test_prompt"

    started_at = datetime.now()
    ended_at = datetime.now()

    ledger_service.write_ledger_entry(
        date=date,
        run_id=run_id,
        prompt_id=prompt_id,
        registry_hash="abc123",
        config_fingerprint="def456",
        started_at=started_at,
        ended_at=ended_at,
        success=True,
        retries=2,
        output_sha256="sha256hash",
        dependent_inputs=["input1", "input2"],
        output_paths=["output1.md", "output2.md"],
    )

    # Verify ledger file exists
    ledger_file = temp_repo_root / "logs" / "ledger" / f"{date}.jsonl"
    assert ledger_file.exists()

    # Load and verify entry
    entries = []
    with open(ledger_file) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    assert len(entries) == 1
    entry = entries[0]

    assert entry["run_id"] == run_id
    assert entry["prompt_id"] == prompt_id
    assert entry["registry_hash"] == "abc123"
    assert entry["config_fingerprint"] == "def456"
    assert entry["success"] is True
    assert entry["retries"] == 2
    assert entry["output_sha256"] == "sha256hash"
    assert entry["dependent_inputs"] == ["input1", "input2"]
    assert entry["output_paths"] == ["output1.md", "output2.md"]
    assert "duration_seconds" in entry


def test_write_ledger_entry_with_error(ledger_service, temp_repo_root):
    """Test writing ledger entry with error."""
    date = "2025-11-14"

    ledger_service.write_ledger_entry(
        date=date,
        run_id="test-run",
        prompt_id="failed_prompt",
        registry_hash="abc",
        config_fingerprint="def",
        started_at=datetime.now(),
        ended_at=datetime.now(),
        success=False,
        error_message="Test error occurred",
    )

    ledger_file = temp_repo_root / "logs" / "ledger" / f"{date}.jsonl"

    with open(ledger_file) as f:
        entry = json.loads(f.readline())

    assert entry["success"] is False
    assert entry["error_message"] == "Test error occurred"


def test_compute_registry_hash(ledger_service, temp_repo_root):
    """Test computing registry hash."""
    # Create a test registry file
    registry_path = temp_repo_root / "test_registry.tsv"
    registry_path.write_text("prompt_id\ttitle\ntest1\tTest 1\ntest2\tTest 2\n")

    hash1 = ledger_service.compute_registry_hash(registry_path)

    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256 hex digest length

    # Same file should produce same hash
    hash2 = ledger_service.compute_registry_hash(registry_path)
    assert hash1 == hash2

    # Modified file should produce different hash
    registry_path.write_text("prompt_id\ttitle\ntest1\tTest 1\ntest3\tTest 3\n")
    hash3 = ledger_service.compute_registry_hash(registry_path)
    assert hash1 != hash3


def test_compute_config_fingerprint(ledger_service):
    """Test computing config fingerprint."""
    config1 = {"key1": "value1", "key2": "value2"}
    config2 = {"key2": "value2", "key1": "value1"}  # Same keys, different order
    config3 = {"key1": "value1", "key2": "different"}

    hash1 = ledger_service.compute_config_fingerprint(config1)
    hash2 = ledger_service.compute_config_fingerprint(config2)
    hash3 = ledger_service.compute_config_fingerprint(config3)

    assert isinstance(hash1, str)
    assert len(hash1) == 64

    # Same config should produce same hash (order-independent)
    assert hash1 == hash2

    # Different config should produce different hash
    assert hash1 != hash3


def test_get_summary_stats_empty(ledger_service, temp_repo_root):
    """Test getting summary stats with no entries."""
    date = "2025-11-14"

    stats = ledger_service.get_summary_stats(date)

    assert stats["total_prompts"] == 0
    assert stats["successful_prompts"] == 0
    assert stats["failed_prompts"] == 0
    assert stats["total_retries"] == 0
    assert stats["total_duration_seconds"] == 0


def test_get_summary_stats(ledger_service, temp_repo_root):
    """Test getting summary stats with entries."""
    date = "2025-11-14"

    # Write several ledger entries
    for i in range(5):
        ledger_service.write_ledger_entry(
            date=date,
            run_id="test-run",
            prompt_id=f"prompt_{i}",
            registry_hash="abc",
            config_fingerprint="def",
            started_at=datetime.now(),
            ended_at=datetime.now(),
            success=(i < 3),  # First 3 succeed, last 2 fail
            retries=i,
        )

    stats = ledger_service.get_summary_stats(date)

    assert stats["total_prompts"] == 5
    assert stats["successful_prompts"] == 3
    assert stats["failed_prompts"] == 2
    assert stats["total_retries"] == sum(range(5))  # 0+1+2+3+4 = 10
    assert stats["total_duration_seconds"] >= 0


def test_multiple_ledger_entries(ledger_service, temp_repo_root):
    """Test writing multiple entries to same ledger file."""
    date = "2025-11-14"

    for i in range(3):
        ledger_service.write_ledger_entry(
            date=date,
            run_id=f"run-{i}",
            prompt_id=f"prompt-{i}",
            registry_hash="abc",
            config_fingerprint="def",
            started_at=datetime.now(),
            ended_at=datetime.now(),
            success=True,
        )

    ledger_file = temp_repo_root / "logs" / "ledger" / f"{date}.jsonl"

    with open(ledger_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    assert len(entries) == 3
    assert entries[0]["prompt_id"] == "prompt-0"
    assert entries[1]["prompt_id"] == "prompt-1"
    assert entries[2]["prompt_id"] == "prompt-2"


def test_log_levels(ledger_service, temp_repo_root):
    """Test different log levels."""
    date = "2025-11-14"

    ledger_service.write_run_log(date, "Info message", "INFO")
    ledger_service.write_run_log(date, "Warning message", "WARNING")
    ledger_service.write_run_log(date, "Error message", "ERROR")

    log_file = temp_repo_root / "logs" / "runs" / f"{date}.log"
    content = log_file.read_text()

    assert "[INFO]" in content
    assert "Info message" in content
    assert "[WARNING]" in content
    assert "Warning message" in content
    assert "[ERROR]" in content
    assert "Error message" in content
