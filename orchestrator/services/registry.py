"""Prompt registry loader and validation service."""

import csv
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

from config.settings_schema import ConcurrencyClass, PromptPolicy, WaveType


class RegistryProvider(Protocol):
    """Protocol for registry providers."""

    def load(self) -> list[PromptPolicy]:
        """Load prompts from the registry."""
        ...

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the registry.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        ...


class TSVRegistryProvider:
    """TSV-based prompt registry provider."""

    def __init__(self, tsv_path: Path):
        """Initialize the TSV registry provider.

        Args:
            tsv_path: Path to the prompts.tsv file
        """
        self.tsv_path = tsv_path
        self._prompts: list[PromptPolicy] | None = None

    def load(self) -> list[PromptPolicy]:
        """Load prompts from TSV file.

        Returns:
            List of PromptPolicy objects

        Raises:
            FileNotFoundError: If TSV file doesn't exist
            ValueError: If TSV format is invalid
        """
        if not self.tsv_path.exists():
            raise FileNotFoundError(f"Registry TSV not found: {self.tsv_path}")

        prompts = []
        with open(self.tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            required_columns = {
                "prompt_id",
                "title",
                "wave",
                "category",
                "expected_outputs",
            }
            if not required_columns.issubset(set(reader.fieldnames or [])):
                missing = required_columns - set(reader.fieldnames or [])
                raise ValueError(f"Missing required columns in TSV: {missing}")

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Parse wave enum
                    wave = WaveType(row["wave"].lower())

                    # Parse concurrency class if present
                    concurrency_class = ConcurrencyClass.MEDIUM
                    if "concurrency_class" in row and row["concurrency_class"]:
                        concurrency_class = ConcurrencyClass(row["concurrency_class"].lower())

                    # Build prompt policy
                    policy = PromptPolicy(
                        prompt_id=row["prompt_id"],
                        title=row["title"],
                        wave=wave,
                        category=row["category"],
                        model=row.get("model", "gemini-2.5-pro"),
                        tools=row.get("tools") if row.get("tools") else None,
                        temperature=float(row.get("temperature", "0.7")),
                        token_budget=int(row.get("token_budget", "32000")),
                        timeout_sec=int(row.get("timeout_sec", "120")),
                        max_retries=int(row.get("max_retries", "3")),
                        concurrency_class=concurrency_class,
                        expected_outputs=row["expected_outputs"],
                        notes=row.get("notes") if row.get("notes") else None,
                    )
                    prompts.append(policy)
                except (ValueError, KeyError) as e:
                    raise ValueError(
                        f"Error parsing TSV row {row_num}: {e}"
                    ) from e

        self._prompts = prompts
        return prompts

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the loaded registry.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Load if not already loaded
        if self._prompts is None:
            try:
                self.load()
            except Exception as e:
                return False, [f"Failed to load registry: {e}"]

        if not self._prompts:
            return False, ["Registry is empty"]

        # Check for duplicate prompt IDs
        prompt_ids = [p.prompt_id for p in self._prompts]
        duplicates = set([pid for pid in prompt_ids if prompt_ids.count(pid) > 1])
        if duplicates:
            errors.append(f"Duplicate prompt IDs found: {duplicates}")

        # Check wave ordering is valid
        wave_order = {
            WaveType.SEARCH: 1,
            WaveType.AGGREGATOR: 2,
            WaveType.TAGGER: 3,
            WaveType.RENDER: 4,
            WaveType.EXPORT: 5,
            WaveType.PUBLISH: 6,
        }

        # Group by wave and validate each wave
        waves_present = set(p.wave for p in self._prompts)
        for wave in waves_present:
            wave_prompts = [p for p in self._prompts if p.wave == wave]

            # Validate temperature limits for prompts with tools
            for prompt in wave_prompts:
                if prompt.tools and prompt.temperature > 1.0:
                    errors.append(
                        f"Prompt '{prompt.prompt_id}' has tools enabled but temperature > 1.0"
                    )

        # Validate that waves are in logical order (no missing critical waves)
        if WaveType.SEARCH not in waves_present:
            errors.append("Missing critical wave: SEARCH")

        if WaveType.AGGREGATOR not in waves_present:
            errors.append("Missing critical wave: AGGREGATOR")

        return len(errors) == 0, errors


class SQLiteRegistryProvider:
    """SQLite-based prompt registry provider (future implementation)."""

    def __init__(self, db_path: Path):
        """Initialize the SQLite registry provider.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        raise NotImplementedError("SQLite registry provider not yet implemented")

    def load(self) -> list[PromptPolicy]:
        """Load prompts from SQLite database."""
        raise NotImplementedError("SQLite registry provider not yet implemented")

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the loaded registry."""
        raise NotImplementedError("SQLite registry provider not yet implemented")


def get_registry_provider(registry_path: Path, format_type: str = "tsv") -> RegistryProvider:
    """Factory function to get the appropriate registry provider.

    Args:
        registry_path: Path to the registry file/database
        format_type: Format type ("tsv" or "sqlite")

    Returns:
        RegistryProvider instance

    Raises:
        ValueError: If format_type is not supported
    """
    if format_type == "tsv":
        return TSVRegistryProvider(registry_path)
    elif format_type == "sqlite":
        return SQLiteRegistryProvider(registry_path)
    else:
        raise ValueError(f"Unsupported registry format: {format_type}")
