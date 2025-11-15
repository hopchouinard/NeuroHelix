"""Runner service for wave scheduling and concurrent execution."""

import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings_schema import ConcurrencyClass, PromptPolicy, WaveType
from adapters.gemini_cli import GeminiCLIAdapter, GeminiCLIError
from services.ledger import LedgerService
from services.manifest import ManifestService


class RunnerService:
    """Service for executing prompts with wave scheduling and concurrency."""

    def __init__(
        self,
        repo_root: Path,
        gemini_adapter: GeminiCLIAdapter,
        ledger_service: LedgerService,
        manifest_service: ManifestService,
    ):
        """Initialize the runner service.

        Args:
            repo_root: Repository root directory
            gemini_adapter: Gemini CLI adapter
            ledger_service: Ledger service
            manifest_service: Manifest service
        """
        self.repo_root = repo_root
        self.gemini_adapter = gemini_adapter
        self.ledger_service = ledger_service
        self.manifest_service = manifest_service

        # Concurrency pool sizes
        self.pool_sizes = {
            ConcurrencyClass.SEQUENTIAL: 1,
            ConcurrencyClass.LOW: 2,
            ConcurrencyClass.MEDIUM: 4,
            ConcurrencyClass.HIGH: 8,
        }

    def execute_wave(
        self,
        wave: WaveType,
        prompts: list[PromptPolicy],
        date: str,
        run_id: str,
        registry_hash: str,
        config_fingerprint: str,
        forced_prompts: list[str] | None = None,
        forced_waves: list[WaveType] | None = None,
        dry_run: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Execute all prompts in a wave.

        Args:
            wave: Wave type to execute
            prompts: All prompt policies
            date: Run date (YYYY-MM-DD)
            run_id: Run identifier
            registry_hash: Registry hash
            config_fingerprint: Config fingerprint
            forced_prompts: Prompts forced to rerun
            forced_waves: Waves forced to rerun
            dry_run: Whether this is a dry run

        Returns:
            Tuple of (completed_prompt_ids, failed_prompt_ids)
        """
        # Filter prompts for this wave
        wave_prompts = [p for p in prompts if p.wave == wave]
        if not wave_prompts:
            return [], []

        self.ledger_service.write_run_log(
            date, f"Starting wave: {wave.value} ({len(wave_prompts)} prompts)"
        )

        # Determine max workers based on concurrency classes
        max_workers = self._get_max_workers(wave_prompts)

        completed = []
        failed = []

        # Execute prompts with appropriate concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for prompt in wave_prompts:
                future = executor.submit(
                    self._execute_single_prompt,
                    prompt,
                    prompts,
                    date,
                    run_id,
                    registry_hash,
                    config_fingerprint,
                    forced_prompts,
                    forced_waves,
                    dry_run,
                )
                futures[future] = prompt.prompt_id

            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                prompt_id = futures[future]
                try:
                    success = future.result()
                    if success:
                        completed.append(prompt_id)
                    else:
                        failed.append(prompt_id)
                except Exception as e:
                    self.ledger_service.write_run_log(
                        date, f"Unexpected error for {prompt_id}: {e}", "ERROR"
                    )
                    failed.append(prompt_id)

        self.ledger_service.write_run_log(
            date,
            f"Wave {wave.value} complete: {len(completed)} succeeded, {len(failed)} failed",
        )

        return completed, failed

    def _execute_single_prompt(
        self,
        prompt: PromptPolicy,
        all_prompts: list[PromptPolicy],
        date: str,
        run_id: str,
        registry_hash: str,
        config_fingerprint: str,
        forced_prompts: list[str] | None,
        forced_waves: list[WaveType] | None,
        dry_run: bool,
    ) -> bool:
        """Execute a single prompt.

        Args:
            prompt: Prompt policy
            all_prompts: All prompts for dependency resolution
            date: Run date
            run_id: Run ID
            registry_hash: Registry hash
            config_fingerprint: Config fingerprint
            forced_prompts: Forced prompt IDs
            forced_waves: Forced waves
            dry_run: Dry run mode

        Returns:
            True if successful
        """
        # Determine output path
        output_path = self._get_output_path(prompt, date)

        # Check if already completed
        force = (forced_prompts and prompt.prompt_id in forced_prompts) or (
            forced_waves and prompt.wave in forced_waves
        )

        if self.manifest_service.is_completed(
            output_path,
            force=force,
            forced_prompts=forced_prompts,
            forced_waves=forced_waves,
            prompt_policy=prompt,
        ):
            self.ledger_service.write_run_log(
                date, f"Skipping {prompt.prompt_id} (already completed)"
            )
            return True

        self.ledger_service.write_run_log(date, f"Executing {prompt.prompt_id}")

        # Load prompt text and context
        prompt_text, context_data = self._load_prompt_and_context(
            prompt, all_prompts, date
        )

        started_at = datetime.now()

        try:
            # Execute via Gemini CLI
            exit_code, output, exec_start, exec_end, retries = (
                self.gemini_adapter.execute_prompt(
                    policy=prompt,
                    prompt_text=prompt_text,
                    output_path=output_path,
                    context_data=context_data,
                    dry_run=dry_run,
                )
            )

            # Write completion marker
            self.manifest_service.write_completion_marker(
                output_path=output_path,
                prompt_id=prompt.prompt_id,
                started_at=exec_start,
                ended_at=exec_end,
                exit_code=exit_code,
                retries=retries,
            )

            # Write ledger entry
            from adapters.filesystem import compute_file_hash

            output_sha256 = None
            if output_path.exists():
                try:
                    output_sha256 = compute_file_hash(output_path)
                except:
                    pass

            deps = self.manifest_service.build_dependency_graph(all_prompts, date)
            dependent_inputs = deps.get(prompt.prompt_id, [])

            self.ledger_service.write_ledger_entry(
                date=date,
                run_id=run_id,
                prompt_id=prompt.prompt_id,
                registry_hash=registry_hash,
                config_fingerprint=config_fingerprint,
                started_at=exec_start,
                ended_at=exec_end,
                success=(exit_code == 0),
                retries=retries,
                output_sha256=output_sha256,
                dependent_inputs=dependent_inputs,
                output_paths=[str(output_path)],
            )

            if exit_code == 0:
                self.ledger_service.write_run_log(
                    date, f"Completed {prompt.prompt_id}"
                )
                return True
            else:
                self.ledger_service.write_run_log(
                    date, f"Failed {prompt.prompt_id} (exit code: {exit_code})", "ERROR"
                )
                return False

        except GeminiCLIError as e:
            # Write failure marker
            ended_at = datetime.now()
            self.manifest_service.write_completion_marker(
                output_path=output_path,
                prompt_id=prompt.prompt_id,
                started_at=started_at,
                ended_at=ended_at,
                exit_code=1,
                error_message=str(e),
            )

            # Write ledger entry
            self.ledger_service.write_ledger_entry(
                date=date,
                run_id=run_id,
                prompt_id=prompt.prompt_id,
                registry_hash=registry_hash,
                config_fingerprint=config_fingerprint,
                started_at=started_at,
                ended_at=ended_at,
                success=False,
                error_message=str(e),
            )

            self.ledger_service.write_run_log(
                date, f"Failed {prompt.prompt_id}: {e}", "ERROR"
            )
            return False

    def _get_max_workers(self, prompts: list[PromptPolicy]) -> int:
        """Determine maximum workers based on concurrency classes.

        Args:
            prompts: Prompts in the wave

        Returns:
            Maximum number of workers
        """
        # If any prompt is sequential, use 1 worker
        if any(p.concurrency_class == ConcurrencyClass.SEQUENTIAL for p in prompts):
            return 1

        # Otherwise use the minimum pool size across all prompts
        pool_sizes = [self.pool_sizes[p.concurrency_class] for p in prompts]
        return min(pool_sizes) if pool_sizes else 1

    def _get_output_path(self, prompt: PromptPolicy, date: str) -> Path:
        """Get output path for a prompt.

        Args:
            prompt: Prompt policy
            date: Date string

        Returns:
            Output file path
        """
        # Most outputs go to daily directory
        if prompt.wave == WaveType.SEARCH:
            outputs_dir = self.repo_root / "data" / "outputs" / "daily" / date
            return outputs_dir / prompt.expected_outputs

        elif prompt.wave == WaveType.AGGREGATOR:
            reports_dir = self.repo_root / "data" / "reports"
            return reports_dir / prompt.expected_outputs.replace("{date}", date)

        elif prompt.wave == WaveType.TAGGER:
            publishing_dir = self.repo_root / "data" / "publishing"
            return publishing_dir / prompt.expected_outputs.replace("{date}", date)

        elif prompt.wave == WaveType.RENDER:
            dashboards_dir = self.repo_root / "dashboards"
            return dashboards_dir / prompt.expected_outputs.replace("{date}", date)

        elif prompt.wave == WaveType.EXPORT:
            publishing_dir = self.repo_root / "data" / "publishing"
            return publishing_dir / prompt.expected_outputs.replace("{date}", date)

        else:
            # Default fallback
            return self.repo_root / "data" / "outputs" / prompt.expected_outputs

    def _load_prompt_and_context(
        self, prompt: PromptPolicy, all_prompts: list[PromptPolicy], date: str
    ) -> tuple[str, Optional[str]]:
        """Load prompt text and context data.

        Args:
            prompt: Prompt policy
            all_prompts: All prompts
            date: Date string

        Returns:
            Tuple of (prompt_text, context_data)
        """
        # Use the actual prompt from the registry
        prompt_text = prompt.prompt

        # Add context for special prompts (similar to Bash orchestrator)
        context_data = None

        # Context-aware prompts can be enhanced here
        # For example, Novelty Filter, Continuity Builder, Meta-Project Explorer

        return prompt_text, context_data
