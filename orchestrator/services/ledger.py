"""Ledger and audit logging service."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings_schema import AuditLogEntry, LedgerEntry
from adapters.filesystem import append_jsonl, ensure_directory, read_jsonl


class LedgerService:
    """Service for execution ledger and audit logging."""

    def __init__(self, repo_root: Path):
        """Initialize the ledger service.

        Args:
            repo_root: Repository root directory
        """
        self.repo_root = repo_root
        self.ledger_dir = repo_root / "logs" / "ledger"
        self.audit_dir = repo_root / "logs" / "audit"
        self.runs_dir = repo_root / "logs" / "runs"

        ensure_directory(self.ledger_dir)
        ensure_directory(self.audit_dir)
        ensure_directory(self.runs_dir)

    def write_ledger_entry(
        self,
        date: str,
        run_id: str,
        prompt_id: str,
        registry_hash: str,
        config_fingerprint: str,
        started_at: datetime,
        ended_at: Optional[datetime],
        success: bool,
        retries: int = 0,
        output_sha256: Optional[str] = None,
        dependent_inputs: list[str] | None = None,
        output_paths: list[str] | None = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Write an entry to the execution ledger.

        Args:
            date: Run date (YYYY-MM-DD)
            run_id: Associated run ID
            prompt_id: Prompt identifier
            registry_hash: Hash of registry configuration
            config_fingerprint: Configuration fingerprint
            started_at: Start timestamp
            ended_at: End timestamp
            success: Whether execution succeeded
            retries: Number of retries
            output_sha256: Output file hash
            dependent_inputs: List of input dependencies
            output_paths: Output file paths
            error_message: Error message if failed
        """
        duration = None
        if ended_at:
            duration = (ended_at - started_at).total_seconds()

        entry = LedgerEntry(
            run_id=run_id,
            prompt_id=prompt_id,
            registry_hash=registry_hash,
            config_fingerprint=config_fingerprint,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration,
            success=success,
            retries=retries,
            output_sha256=output_sha256,
            dependent_inputs=dependent_inputs or [],
            output_paths=output_paths or [],
            error_message=error_message,
        )

        ledger_path = self.ledger_dir / f"{date}.jsonl"
        append_jsonl(ledger_path, entry.model_dump())

    def read_ledger_entries(self, date: str) -> list[LedgerEntry]:
        """Read all ledger entries for a date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            List of LedgerEntry objects
        """
        ledger_path = self.ledger_dir / f"{date}.jsonl"
        entries = read_jsonl(ledger_path)
        return [LedgerEntry(**entry) for entry in entries]

    def write_audit_entry(
        self,
        operator: str,
        cli_version: str,
        command: str,
        affected_paths: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Write an entry to the audit log.

        Args:
            operator: Operator (user or system)
            cli_version: CLI version
            command: Command executed
            affected_paths: Affected file paths
            metadata: Additional metadata
        """
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            operator=operator,
            cli_version=cli_version,
            command=command,
            affected_paths=affected_paths or [],
            metadata=metadata,
        )

        # Write to daily audit log
        today = datetime.now().strftime("%Y-%m-%d")
        audit_path = self.audit_dir / f"{today}.jsonl"
        append_jsonl(audit_path, entry.model_dump())

    def read_audit_entries(self, date: str) -> list[AuditLogEntry]:
        """Read all audit entries for a date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            List of AuditLogEntry objects
        """
        audit_path = self.audit_dir / f"{date}.jsonl"
        entries = read_jsonl(audit_path)
        return [AuditLogEntry(**entry) for entry in entries]

    def compute_registry_hash(self, prompts_tsv_path: Path) -> str:
        """Compute hash of the registry file.

        Args:
            prompts_tsv_path: Path to prompts.tsv

        Returns:
            SHA256 hash of the file
        """
        if not prompts_tsv_path.exists():
            return ""

        sha256 = hashlib.sha256()
        with open(prompts_tsv_path, "rb") as f:
            sha256.update(f.read())
        return sha256.hexdigest()

    def compute_config_fingerprint(self, config: dict) -> str:
        """Compute fingerprint of configuration.

        Args:
            config: Configuration dictionary

        Returns:
            SHA256 hash of configuration
        """
        config_str = str(sorted(config.items()))
        sha256 = hashlib.sha256(config_str.encode())
        return sha256.hexdigest()

    def get_run_log_path(self, date: str) -> Path:
        """Get path to human-readable run log.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Path to log file
        """
        return self.runs_dir / f"{date}.log"

    def write_run_log(self, date: str, message: str, level: str = "INFO") -> None:
        """Write a message to the human-readable run log.

        Args:
            date: Date string (YYYY-MM-DD)
            message: Log message
            level: Log level (INFO, WARNING, ERROR)
        """
        log_path = self.get_run_log_path(date)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)

    def get_summary_stats(self, date: str) -> dict:
        """Get summary statistics from ledger entries.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Dictionary with summary statistics
        """
        entries = self.read_ledger_entries(date)

        if not entries:
            return {
                "total_prompts": 0,
                "successful_prompts": 0,
                "failed_prompts": 0,
                "total_duration_seconds": 0,
                "total_retries": 0,
            }

        successful = sum(1 for e in entries if e.success)
        failed = len(entries) - successful
        total_duration = sum(e.duration_seconds or 0 for e in entries)
        total_retries = sum(e.retries for e in entries)

        return {
            "total_prompts": len(entries),
            "successful_prompts": successful,
            "failed_prompts": failed,
            "total_duration_seconds": total_duration,
            "total_retries": total_retries,
        }
