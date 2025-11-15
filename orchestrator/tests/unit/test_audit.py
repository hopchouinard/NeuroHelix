"""Unit tests for AuditService."""

import json
import tempfile
from pathlib import Path

import pytest

from services.audit import AuditService


@pytest.fixture
def temp_repo_root():
    """Create a temporary repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def audit_service(temp_repo_root):
    """Create an AuditService instance."""
    return AuditService(temp_repo_root, cli_version="0.1.0-test")


def test_log_operation(audit_service, temp_repo_root):
    """Test logging a generic operation."""
    audit_service.log_operation(
        command="nh test",
        affected_paths=["/path/to/file1", "/path/to/file2"],
        metadata={"key": "value"},
        operator="test_user",
    )

    # Verify audit log file exists
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    assert audit_file.exists()

    # Load and verify entry
    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["operator"] == "test_user"
    assert entry["cli_version"] == "0.1.0-test"
    assert entry["command"] == "nh test"
    assert entry["affected_paths"] == ["/path/to/file1", "/path/to/file2"]
    assert entry["metadata"]["key"] == "value"
    assert "timestamp" in entry


def test_log_cleanup(audit_service, temp_repo_root):
    """Test logging cleanup operation."""
    audit_service.log_cleanup(
        removed_files=["file1.txt", "file2.txt"],
        removed_locks=["lock1.lock"],
        bytes_freed=1024000,
        dry_run=False,
    )

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["command"] == "nh cleanup"
    assert entry["metadata"]["operation"] == "cleanup"
    assert entry["metadata"]["files_removed"] == 2
    assert entry["metadata"]["locks_removed"] == 1
    assert entry["metadata"]["bytes_freed"] == 1024000
    assert entry["metadata"]["dry_run"] is False
    assert len(entry["affected_paths"]) == 3


def test_log_cleanup_dry_run(audit_service, temp_repo_root):
    """Test logging cleanup dry run."""
    audit_service.log_cleanup(
        removed_files=["file1.txt"],
        removed_locks=[],
        bytes_freed=0,
        dry_run=True,
    )

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["metadata"]["dry_run"] is True


def test_log_reprocess(audit_service, temp_repo_root):
    """Test logging reprocess operation."""
    audit_service.log_reprocess(
        date="2025-11-14",
        forced_items=["search", "aggregator"],
        regenerated_files=["file1.md", "file2.md"],
        dry_run=False,
    )

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["command"] == "nh reprocess --date 2025-11-14"
    assert entry["metadata"]["operation"] == "reprocess"
    assert entry["metadata"]["date"] == "2025-11-14"
    assert entry["metadata"]["forced_items"] == ["search", "aggregator"]
    assert entry["metadata"]["files_regenerated"] == 2
    assert entry["affected_paths"] == ["file1.md", "file2.md"]


def test_log_publish(audit_service, temp_repo_root):
    """Test logging publish operation."""
    audit_service.log_publish(
        date="2025-11-14",
        deploy_url="https://example.pages.dev",
        success=True,
        duration_seconds=45.5,
    )

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["command"] == "nh publish --date 2025-11-14"
    assert entry["metadata"]["operation"] == "publish"
    assert entry["metadata"]["date"] == "2025-11-14"
    assert entry["metadata"]["deploy_url"] == "https://example.pages.dev"
    assert entry["metadata"]["success"] is True
    assert entry["metadata"]["duration_seconds"] == 45.5


def test_log_publish_failure(audit_service, temp_repo_root):
    """Test logging failed publish operation."""
    audit_service.log_publish(
        date="2025-11-14",
        deploy_url=None,
        success=False,
        duration_seconds=10.0,
    )

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["metadata"]["deploy_url"] is None
    assert entry["metadata"]["success"] is False


def test_log_automation_install(audit_service, temp_repo_root):
    """Test logging automation install."""
    audit_service.log_automation_install(
        plist_path="/path/to/plist",
        schedule={"hour": 7, "minute": 0},
        success=True,
    )

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["command"] == "nh automation install"
    assert entry["metadata"]["operation"] == "automation_install"
    assert entry["metadata"]["plist_path"] == "/path/to/plist"
    assert entry["metadata"]["schedule"] == {"hour": 7, "minute": 0}
    assert entry["metadata"]["success"] is True
    assert entry["affected_paths"] == ["/path/to/plist"]


def test_log_automation_remove(audit_service, temp_repo_root):
    """Test logging automation remove."""
    audit_service.log_automation_remove(plist_path="/path/to/plist", success=True)

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    assert entry["command"] == "nh automation remove"
    assert entry["metadata"]["operation"] == "automation_remove"
    assert entry["metadata"]["success"] is True


def test_multiple_audit_entries(audit_service, temp_repo_root):
    """Test writing multiple audit entries."""
    # Log several operations
    audit_service.log_cleanup([], [], 0, False)
    audit_service.log_reprocess("2025-11-14", [], [], False)
    audit_service.log_publish("2025-11-14", None, True, 10.0)

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    # Load all entries
    entries = []
    with open(audit_file) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    assert len(entries) == 3
    assert entries[0]["metadata"]["operation"] == "cleanup"
    assert entries[1]["metadata"]["operation"] == "reprocess"
    assert entries[2]["metadata"]["operation"] == "publish"


def test_default_operator(audit_service, temp_repo_root):
    """Test default operator detection."""
    audit_service.log_operation(command="test command")

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = temp_repo_root / "logs" / "audit" / f"{today}.jsonl"

    with open(audit_file) as f:
        entry = json.loads(f.readline())

    # Should have detected operator from environment
    assert "operator" in entry
    assert isinstance(entry["operator"], str)
    assert len(entry["operator"]) > 0
