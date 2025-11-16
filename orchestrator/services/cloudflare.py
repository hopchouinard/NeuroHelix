"""Cloudflare helper service for parity with Bash orchestrator."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CloudflareService:
    """Minimal wrapper for Cloudflare deployment lookups."""

    repo_root: Path
    project_name: Optional[str] = None
    api_token: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.project_name and (self.api_token or os.getenv("CLOUDFLARE_API_TOKEN")))

    def get_latest_deployment_id(self) -> Optional[str]:
        """Return the latest deployment ID via wrangler, if available."""

        if not self.is_configured:
            return None

        env = os.environ.copy()
        if self.api_token:
            env.setdefault("CLOUDFLARE_API_TOKEN", self.api_token)

        try:
            result = subprocess.run(
                [
                    "npx",
                    "wrangler",
                    "pages",
                    "deployment",
                    "list",
                    f"--project-name={self.project_name}",
                ],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            parts = [segment.strip() for segment in line.split("|")]
            if len(parts) >= 4 and parts[0] and (
                "active" in parts[3].lower() or "success" in parts[3].lower()
            ):
                return parts[0]

            match = re.search(r"([a-f0-9]{32})", line)
            if match:
                return match.group(1)

        return None
