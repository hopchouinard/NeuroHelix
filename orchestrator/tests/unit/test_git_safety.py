"""Tests for git safety helper service."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from services.git_safety import GitDirtyError, ensure_clean_repo, get_git_status


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run([
        "git",
        "config",
        "user.email",
        "ci@example.com",
    ], cwd=repo, check=True)
    subprocess.run([
        "git",
        "config",
        "user.name",
        "CI",
    ], cwd=repo, check=True)
    (repo / "file.txt").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)


def test_get_git_status_clean(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    status = get_git_status(tmp_path)
    assert status.clean
    assert status.dirty_files == []


def test_get_git_status_dirty(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "file.txt").write_text("modified", encoding="utf-8")
    status = get_git_status(tmp_path)
    assert not status.clean
    assert status.dirty_files[0].endswith("file.txt")


def test_ensure_clean_repo_blocks_dirty(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "file.txt").write_text("modified", encoding="utf-8")

    with pytest.raises(GitDirtyError):
        ensure_clean_repo(tmp_path, allow_dirty=False)


def test_ensure_clean_repo_allows_dirty_with_flag(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "file.txt").write_text("modified", encoding="utf-8")

    status = ensure_clean_repo(tmp_path, allow_dirty=True)
    assert not status.clean
