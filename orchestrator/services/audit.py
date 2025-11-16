"""Audit log service for maintenance operations."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from adapters.filesystem import append_jsonl, ensure_directory
from config.settings_schema import AuditLogEntry


class AuditService:
    """Service for recording maintenance operation audit trails."""

    def __init__(self, repo_root: Path, cli_version: str = "0.1.0"):
        """Initialize the audit service.

        Args:
            repo_root: Repository root directory
            cli_version: CLI version string
        """
        self.repo_root = repo_root
        self.cli_version = cli_version
        self.audit_dir = repo_root / "logs" / "audit"
        ensure_directory(self.audit_dir)

    def log_operation(
        self,
        command: str,
        affected_paths: list[str] | None = None,
        metadata: dict | None = None,
        operator: str | None = None,
    ) -> None:
        """Log a maintenance operation.

        Args:
            command: Command executed
            affected_paths: List of file paths affected
            metadata: Additional metadata
            operator: Operator name (defaults to current user)
        """
        # Determine operator
        if operator is None:
            operator = os.getenv("USER", os.getenv("USERNAME", "unknown"))

        # Create audit entry
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            operator=operator,
            cli_version=self.cli_version,
            command=command,
            affected_paths=affected_paths or [],
            metadata=metadata,
        )

        # Write to audit log
        today = datetime.now().strftime("%Y-%m-%d")
        audit_path = self.audit_dir / f"{today}.jsonl"

        append_jsonl(audit_path, entry.model_dump())

    def log_cleanup(
        self,
        removed_files: list[str],
        removed_locks: list[str],
        bytes_freed: int,
        dry_run: bool = False,
        git_clean: bool = True,
        dirty_files: list[str] | None = None,
        cloudflare_deploy_id: str | None = None,
    ) -> None:
        """Log a cleanup operation.

        Args:
            removed_files: List of removed file paths
            removed_locks: List of removed lock paths
            bytes_freed: Bytes freed
            dry_run: Whether this was a dry run
        """
        metadata = {
            "operation": "cleanup",
            "dry_run": dry_run,
            "files_removed": len(removed_files),
            "locks_removed": len(removed_locks),
            "bytes_freed": bytes_freed,
            "git_clean": git_clean,
            "dirty_files": dirty_files or [],
            "cloudflare_deploy_id": cloudflare_deploy_id,
        }

        affected_paths = removed_files + removed_locks

        self.log_operation(
            command=f"nh cleanup{' --dry-run' if dry_run else ''}",
            affected_paths=affected_paths,
            metadata=metadata,
        )

    def log_reprocess(
        self,
        date: str,
        forced_items: list[str],
        regenerated_files: list[str],
        dry_run: bool = False,
    ) -> None:
        """Log a reprocess operation.

        Args:
            date: Date being reprocessed
            forced_items: List of forced prompt/wave IDs
            regenerated_files: List of regenerated file paths
            dry_run: Whether this was a dry run
        """
        metadata = {
            "operation": "reprocess",
            "dry_run": dry_run,
            "date": date,
            "forced_items": forced_items,
            "files_regenerated": len(regenerated_files),
        }

        self.log_operation(
            command=f"nh reprocess --date {date}{' --dry-run' if dry_run else ''}",
            affected_paths=regenerated_files,
            metadata=metadata,
        )

    def log_publish(
        self,
        date: str,
        deploy_url: Optional[str],
        success: bool,
        duration_seconds: float,
    ) -> None:
        """Log a publish operation.

        Args:
            date: Date being published
            deploy_url: Cloudflare deployment URL
            success: Whether publish succeeded
            duration_seconds: Deployment duration
        """
        metadata = {
            "operation": "publish",
            "date": date,
            "deploy_url": deploy_url,
            "success": success,
            "duration_seconds": duration_seconds,
        }

        self.log_operation(
            command=f"nh publish --date {date}",
            metadata=metadata,
        )

    def log_automation_install(
        self, plist_path: str, schedule: dict, success: bool
    ) -> None:
        """Log automation installation.

        Args:
            plist_path: Path to plist file
            schedule: Schedule configuration
            success: Whether installation succeeded
        """
        metadata = {
            "operation": "automation_install",
            "plist_path": plist_path,
            "schedule": schedule,
            "success": success,
        }

        self.log_operation(
            command="nh automation install",
            affected_paths=[plist_path],
            metadata=metadata,
        )

    def log_automation_remove(self, plist_path: str, success: bool) -> None:
        """Log automation removal.

        Args:
            plist_path: Path to plist file
            success: Whether removal succeeded
        """
        metadata = {
            "operation": "automation_remove",
            "plist_path": plist_path,
            "success": success,
        }

        self.log_operation(
            command="nh automation remove",
            affected_paths=[plist_path],
            metadata=metadata,
        )
