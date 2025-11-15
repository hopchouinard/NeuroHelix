"""Pydantic models for configuration and settings."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class WaveType(str, Enum):
    """Pipeline wave types in execution order."""

    SEARCH = "search"
    AGGREGATOR = "aggregator"
    TAGGER = "tagger"
    RENDER = "render"
    EXPORT = "export"
    PUBLISH = "publish"


class ConcurrencyClass(str, Enum):
    """Concurrency classes for prompt execution."""

    SEQUENTIAL = "sequential"
    LOW = "low"  # 2 workers
    MEDIUM = "medium"  # 4 workers
    HIGH = "high"  # 8 workers


class PromptPolicy(BaseModel):
    """Policy configuration for a single prompt."""

    prompt_id: str = Field(..., description="Unique identifier for the prompt")
    title: str = Field(..., description="Human-readable title")
    wave: WaveType = Field(..., description="Pipeline wave this prompt belongs to")
    category: str = Field(..., description="Category for grouping")
    model: str = Field(default="gemini-2.5-pro", description="Gemini model to use")
    tools: Optional[str] = Field(default=None, description="Tools to enable")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature setting")
    token_budget: int = Field(default=32000, gt=0, description="Maximum tokens")
    timeout_sec: int = Field(default=120, gt=0, description="Timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    concurrency_class: ConcurrencyClass = Field(
        default=ConcurrencyClass.MEDIUM, description="Concurrency class"
    )
    expected_outputs: str = Field(..., description="Expected output file pattern")
    prompt: str = Field(..., description="The actual prompt text to execute")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    @field_validator("prompt_id")
    @classmethod
    def validate_prompt_id(cls, v: str) -> str:
        """Ensure prompt_id is valid."""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("prompt_id must be alphanumeric with underscores/hyphens")
        return v


class NHSettings(BaseModel):
    """Global settings for NeuroHelix orchestrator."""

    repo_root: Path = Field(..., description="Repository root directory")
    default_model: str = Field(default="gemini-2.5-pro", description="Default Gemini model")
    max_parallel_jobs: int = Field(default=4, gt=0, description="Maximum parallel jobs")
    enable_static_site_publishing: bool = Field(
        default=True, description="Enable Cloudflare publishing"
    )
    cloudflare_project_name: str = Field(
        default="neurohelix-site", description="Cloudflare project name"
    )
    lock_ttl_seconds: int = Field(default=7200, gt=0, description="Lock TTL in seconds (2 hours)")
    cleanup_keep_days: int = Field(default=90, gt=0, description="Days to keep old artifacts")

    class Config:
        """Pydantic config."""

        frozen = True


class RunManifest(BaseModel):
    """Manifest for a single pipeline run."""

    run_id: str = Field(..., description="Unique run identifier")
    date: str = Field(..., description="Run date (YYYY-MM-DD)")
    started_at: datetime = Field(..., description="Run start timestamp")
    ended_at: Optional[datetime] = Field(default=None, description="Run end timestamp")
    forced_prompts: list[str] = Field(
        default_factory=list, description="Prompts forced to rerun"
    )
    forced_waves: list[WaveType] = Field(default_factory=list, description="Waves forced to rerun")
    completed_prompts: list[str] = Field(
        default_factory=list, description="Successfully completed prompts"
    )
    failed_prompts: list[str] = Field(default_factory=list, description="Failed prompts")
    publish_metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Publishing metadata"
    )
    dry_run: bool = Field(default=False, description="Whether this was a dry run")


class CompletionMarker(BaseModel):
    """Completion status for a single artifact."""

    prompt_id: str = Field(..., description="Associated prompt ID")
    started_at: datetime = Field(..., description="Start timestamp")
    ended_at: datetime = Field(..., description="End timestamp")
    exit_code: int = Field(..., description="Process exit code")
    retries: int = Field(default=0, ge=0, description="Number of retries")
    sha256: Optional[str] = Field(default=None, description="SHA256 hash of output file")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class LedgerEntry(BaseModel):
    """Single entry in the execution ledger."""

    run_id: str = Field(..., description="Associated run ID")
    prompt_id: str = Field(..., description="Prompt identifier")
    registry_hash: str = Field(..., description="Hash of registry configuration")
    config_fingerprint: str = Field(..., description="Configuration fingerprint")
    started_at: datetime = Field(..., description="Start timestamp")
    ended_at: Optional[datetime] = Field(default=None, description="End timestamp")
    duration_seconds: Optional[float] = Field(default=None, description="Execution duration")
    success: bool = Field(..., description="Whether execution succeeded")
    retries: int = Field(default=0, ge=0, description="Number of retries")
    output_sha256: Optional[str] = Field(default=None, description="Output file hash")
    dependent_inputs: list[str] = Field(
        default_factory=list, description="List of input dependencies"
    )
    output_paths: list[str] = Field(default_factory=list, description="Output file paths")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class AuditLogEntry(BaseModel):
    """Single entry in the audit log for maintenance operations."""

    timestamp: datetime = Field(..., description="Operation timestamp")
    operator: str = Field(..., description="Operator (user or system)")
    cli_version: str = Field(..., description="CLI version")
    command: str = Field(..., description="Command executed")
    affected_paths: list[str] = Field(default_factory=list, description="Affected file paths")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )
