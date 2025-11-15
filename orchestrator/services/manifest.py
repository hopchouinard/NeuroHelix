"""Manifest and dependency tracking service."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings_schema import (
    CompletionMarker,
    PromptPolicy,
    RunManifest,
    WaveType,
)
from adapters.filesystem import (
    append_jsonl,
    compute_file_hash,
    read_json,
    write_json,
)


class ManifestService:
    """Service for managing run manifests and completion markers."""

    def __init__(self, repo_root: Path):
        """Initialize the manifest service.

        Args:
            repo_root: Repository root directory
        """
        self.repo_root = repo_root
        self.manifests_dir = repo_root / "data" / "manifests"
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def create_manifest(
        self,
        date: str,
        forced_prompts: list[str] | None = None,
        forced_waves: list[WaveType] | None = None,
        dry_run: bool = False,
    ) -> RunManifest:
        """Create a new run manifest.

        Args:
            date: Run date (YYYY-MM-DD)
            forced_prompts: List of prompt IDs to force rerun
            forced_waves: List of waves to force rerun
            dry_run: Whether this is a dry run

        Returns:
            RunManifest instance
        """
        manifest = RunManifest(
            run_id=str(uuid.uuid4()),
            date=date,
            started_at=datetime.now(),
            forced_prompts=forced_prompts or [],
            forced_waves=forced_waves or [],
            dry_run=dry_run,
        )
        return manifest

    def save_manifest(self, manifest: RunManifest, date: str) -> Path:
        """Save a manifest to disk.

        Args:
            manifest: RunManifest to save
            date: Date string (YYYY-MM-DD)

        Returns:
            Path to saved manifest file
        """
        manifest_path = self.manifests_dir / f"{date}.json"
        write_json(manifest_path, manifest.model_dump())
        return manifest_path

    def load_manifest(self, date: str) -> Optional[RunManifest]:
        """Load a manifest from disk.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            RunManifest if exists, None otherwise
        """
        manifest_path = self.manifests_dir / f"{date}.json"
        if not manifest_path.exists():
            return None

        try:
            data = read_json(manifest_path)
            return RunManifest(**data)
        except Exception:
            return None

    def write_completion_marker(
        self,
        output_path: Path,
        prompt_id: str,
        started_at: datetime,
        ended_at: datetime,
        exit_code: int,
        retries: int = 0,
        error_message: Optional[str] = None,
    ) -> Path:
        """Write a completion marker for an artifact.

        Args:
            output_path: Path to the output file
            prompt_id: Associated prompt ID
            started_at: Start timestamp
            ended_at: End timestamp
            exit_code: Process exit code
            retries: Number of retries
            error_message: Error message if failed

        Returns:
            Path to completion marker file
        """
        # Compute hash of output if it exists
        sha256 = None
        if output_path.exists():
            try:
                sha256 = compute_file_hash(output_path)
            except:
                pass

        # Create completion marker
        marker = CompletionMarker(
            prompt_id=prompt_id,
            started_at=started_at,
            ended_at=ended_at,
            exit_code=exit_code,
            retries=retries,
            sha256=sha256,
            error_message=error_message,
        )

        # Write marker beside the output file
        marker_path = output_path.parent / f".nh_status_{output_path.stem}.json"
        write_json(marker_path, marker.model_dump())
        return marker_path

    def read_completion_marker(self, output_path: Path) -> Optional[CompletionMarker]:
        """Read a completion marker for an artifact.

        Args:
            output_path: Path to the output file

        Returns:
            CompletionMarker if exists, None otherwise
        """
        marker_path = output_path.parent / f".nh_status_{output_path.stem}.json"
        if not marker_path.exists():
            return None

        try:
            data = read_json(marker_path)
            return CompletionMarker(**data)
        except Exception:
            return None

    def is_completed(
        self,
        output_path: Path,
        force: bool = False,
        forced_prompts: list[str] | None = None,
        forced_waves: list[WaveType] | None = None,
        prompt_policy: Optional[PromptPolicy] = None,
    ) -> bool:
        """Check if a prompt execution is already completed.

        Args:
            output_path: Path to the output file
            force: Force rerun regardless of completion status
            forced_prompts: List of prompt IDs forced to rerun
            forced_waves: List of waves forced to rerun
            prompt_policy: Associated prompt policy

        Returns:
            True if completed and should be skipped
        """
        if force:
            return False

        if prompt_policy:
            if forced_prompts and prompt_policy.prompt_id in forced_prompts:
                return False
            if forced_waves and prompt_policy.wave in forced_waves:
                return False

        # Check completion marker
        marker = self.read_completion_marker(output_path)
        if not marker:
            return False

        # Check if output file exists and hash matches
        if not output_path.exists():
            return False

        if marker.exit_code != 0:
            return False

        # Verify hash if available
        if marker.sha256:
            try:
                current_hash = compute_file_hash(output_path)
                if current_hash != marker.sha256:
                    return False
            except:
                return False

        return True

    def invalidate_completion_marker(self, output_path: Path) -> None:
        """Invalidate (delete) a completion marker.

        Args:
            output_path: Path to the output file
        """
        marker_path = output_path.parent / f".nh_status_{output_path.stem}.json"
        if marker_path.exists():
            marker_path.unlink()

    def build_dependency_graph(
        self, prompts: list[PromptPolicy], date: str
    ) -> dict[str, list[str]]:
        """Build dependency graph for prompts.

        Args:
            prompts: List of prompt policies
            date: Date string (YYYY-MM-DD)

        Returns:
            Dictionary mapping prompt_id to list of dependency paths
        """
        deps = {}

        # Wave ordering defines dependencies
        wave_order = {
            WaveType.SEARCH: 1,
            WaveType.AGGREGATOR: 2,
            WaveType.TAGGER: 3,
            WaveType.RENDER: 4,
            WaveType.EXPORT: 5,
            WaveType.PUBLISH: 6,
        }

        outputs_dir = self.repo_root / "data" / "outputs" / "daily" / date
        reports_dir = self.repo_root / "data" / "reports"

        for prompt in prompts:
            deps[prompt.prompt_id] = []

            # Aggregator depends on all search outputs
            if prompt.wave == WaveType.AGGREGATOR:
                search_prompts = [p for p in prompts if p.wave == WaveType.SEARCH]
                for sp in search_prompts:
                    output_file = outputs_dir / sp.expected_outputs
                    deps[prompt.prompt_id].append(str(output_file))

            # Tagger depends on aggregator output (daily report)
            elif prompt.wave == WaveType.TAGGER:
                daily_report = reports_dir / f"daily_report_{date}.md"
                deps[prompt.prompt_id].append(str(daily_report))

            # Render depends on aggregator output
            elif prompt.wave == WaveType.RENDER:
                daily_report = reports_dir / f"daily_report_{date}.md"
                deps[prompt.prompt_id].append(str(daily_report))

            # Export depends on aggregator and tagger
            elif prompt.wave == WaveType.EXPORT:
                daily_report = reports_dir / f"daily_report_{date}.md"
                tags_file = (
                    self.repo_root / "data" / "publishing" / f"tags_{date}.json"
                )
                deps[prompt.prompt_id].extend([str(daily_report), str(tags_file)])

            # Publish depends on export
            elif prompt.wave == WaveType.PUBLISH:
                export_file = self.repo_root / "data" / "publishing" / f"{date}.json"
                deps[prompt.prompt_id].append(str(export_file))

        return deps
