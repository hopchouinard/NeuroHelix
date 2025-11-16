"""Git safety helpers mirroring Bash cleanup safeguards."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class GitDirtyError(RuntimeError):
    """Raised when the repository has pending changes and allow_dirty is False."""


@dataclass
class GitStatus:
    """Represents git clean/dirty state along with changed files."""

    clean: bool
    dirty_files: list[str]


def _run_git_command(args: Iterable[str], repo_root: Path) -> subprocess.CompletedProcess:
    """Run git command inside repo_root and return completed process."""

    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )


def get_git_status(repo_root: Path) -> GitStatus:
    """Return whether repo is clean and the list of dirty files."""

    result = _run_git_command(["status", "--short"], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to inspect git status")

    dirty_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return GitStatus(clean=len(dirty_files) == 0, dirty_files=dirty_files)


def ensure_clean_repo(repo_root: Path, allow_dirty: bool) -> GitStatus:
    """Ensure repo is clean unless allow_dirty is True."""

    status = get_git_status(repo_root)
    if status.clean or allow_dirty:
        return status

    raise GitDirtyError(
        "Git working tree is dirty. Commit or stash changes or pass --allow-dirty."
    )
