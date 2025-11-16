"""Tests for notifier service wrapper."""

from __future__ import annotations

from pathlib import Path

from services.notifier import NotifierHooksConfig, NotifierService


def _make_script(path: Path, content: str = "exit 0") -> Path:
    path.write_text(f"#!/usr/bin/env bash\n{content}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_notify_success_runs_script(tmp_path):
    script = _make_script(tmp_path / "success.sh")
    config = NotifierHooksConfig(
        enable_success=True,
        enable_failure=False,
        success_script=script,
        failure_script=tmp_path / "missing.sh",
    )
    service = NotifierService(tmp_path, config)
    assert service.notify_success("2025-01-01", tmp_path / "log.txt")


def test_notify_failure_handles_missing_script(tmp_path):
    failure_script = tmp_path / "missing.sh"
    config = NotifierHooksConfig(
        enable_success=False,
        enable_failure=True,
        success_script=tmp_path / "success.sh",
        failure_script=failure_script,
    )
    service = NotifierService(tmp_path, config)
    assert not service.notify_failures("2025-01-01", ["prompt-1"], tmp_path / "log.txt")
