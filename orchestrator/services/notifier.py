"""Wrapper around legacy notifier shell scripts."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class NotifierHooksConfig:
    enable_success: bool
    enable_failure: bool
    success_script: Path
    failure_script: Path


class NotifierService:
    """Invoke Bash notifier hooks from the Python CLI."""

    def __init__(self, repo_root: Path, config: NotifierHooksConfig):
        self.repo_root = repo_root
        self.config = config

    def _script_exists(self, script: Path) -> bool:
        return script.exists() and script.is_file()

    def _run_script(self, script: Path, env_updates: Optional[dict] = None) -> bool:
        if not self._script_exists(script):
            return False

        env = os.environ.copy()
        if env_updates:
            env.update(env_updates)

        try:
            result = subprocess.run(
                ["bash", str(script)],
                cwd=str(self.repo_root),
                env=env,
                capture_output=False,
                check=False,
            )
        except FileNotFoundError:
            return False

        return result.returncode == 0

    def notify_success(self, date: str, log_path: Path) -> bool:
        if not self.config.enable_success:
            return False
        return self._run_script(
            self.config.success_script,
            {
                "NH_RUN_DATE": date,
                "NH_RUN_LOG": str(log_path),
            },
        )

    def notify_failures(self, date: str, failed_prompts: Iterable[str], log_path: Path) -> bool:
        if not self.config.enable_failure or not failed_prompts:
            return False
        return self._run_script(
            self.config.failure_script,
            {
                "NH_RUN_DATE": date,
                "NH_FAILED_PROMPTS": ",".join(sorted(failed_prompts)),
                "NH_RUN_LOG": str(log_path),
            },
        )
