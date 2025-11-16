"""SQLite-backed registry provider for prompt policies."""

import sqlite3
from pathlib import Path
from typing import Optional

from config.settings_schema import (
    PromptPolicy,
    WaveType,
    ConcurrencyClass,
)
from services.registry import RegistryProvider


class SQLiteRegistryProvider(RegistryProvider):
    """Registry provider backed by SQLite database."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path):
        """Initialize SQLite registry provider.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure database schema exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prompts (
                    prompt_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    wave TEXT NOT NULL,
                    category TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tools TEXT,
                    temperature REAL NOT NULL,
                    token_budget INTEGER NOT NULL,
                    timeout_sec INTEGER NOT NULL,
                    max_retries INTEGER NOT NULL,
                    concurrency_class TEXT NOT NULL,
                    expected_outputs TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create indices for common queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_wave ON prompts(wave)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_category ON prompts(category)"
            )

            # Record schema version
            cursor = conn.execute(
                "SELECT version FROM schema_version WHERE version = ?",
                (self.SCHEMA_VERSION,),
            )
            if not cursor.fetchone():
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )

            conn.commit()

    def load(self) -> list[PromptPolicy]:
        """Load all prompt policies from SQLite database.

        Returns:
            List of PromptPolicy objects

        Raises:
            ValueError: If database contains invalid data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT prompt_id, title, wave, category, model, tools,
                       temperature, token_budget, timeout_sec, max_retries,
                       concurrency_class, expected_outputs, prompt, notes
                FROM prompts
                ORDER BY prompt_id
                """
            )

            prompts = []
            for row in cursor:
                try:
                    policy = PromptPolicy(
                        prompt_id=row["prompt_id"],
                        title=row["title"],
                        wave=WaveType(row["wave"]),
                        category=row["category"],
                        model=row["model"],
                        tools=row["tools"] or None,
                        temperature=row["temperature"],
                        token_budget=row["token_budget"],
                        timeout_sec=row["timeout_sec"],
                        max_retries=row["max_retries"],
                        concurrency_class=ConcurrencyClass(row["concurrency_class"]),
                        expected_outputs=row["expected_outputs"],
                        prompt=row["prompt"],
                        notes=row["notes"],
                    )
                    prompts.append(policy)
                except Exception as e:
                    raise ValueError(
                        f"Invalid prompt policy for '{row['prompt_id']}': {e}"
                    ) from e

            return prompts

    def save(self, prompts: list[PromptPolicy]) -> None:
        """Save prompt policies to SQLite database.

        Args:
            prompts: List of PromptPolicy objects to save

        Raises:
            ValueError: If duplicate prompt_id found
        """
        # Validate no duplicates
        prompt_ids = [p.prompt_id for p in prompts]
        if len(prompt_ids) != len(set(prompt_ids)):
            duplicates = [pid for pid in prompt_ids if prompt_ids.count(pid) > 1]
            raise ValueError(f"Duplicate prompt IDs: {set(duplicates)}")

        with sqlite3.connect(self.db_path) as conn:
            # Clear existing prompts
            conn.execute("DELETE FROM prompts")

            # Insert new prompts
            for prompt in prompts:
                conn.execute(
                    """
                    INSERT INTO prompts (
                        prompt_id, title, wave, category, model, tools,
                        temperature, token_budget, timeout_sec, max_retries,
                        concurrency_class, expected_outputs, prompt, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt.prompt_id,
                        prompt.title,
                        prompt.wave.value,
                        prompt.category,
                        prompt.model,
                        prompt.tools,
                        prompt.temperature,
                        prompt.token_budget,
                        prompt.timeout_sec,
                        prompt.max_retries,
                        prompt.concurrency_class.value,
                        prompt.expected_outputs,
                        prompt.prompt,
                        prompt.notes,
                    ),
                )

            conn.commit()

    def get_by_id(self, prompt_id: str) -> Optional[PromptPolicy]:
        """Get a single prompt policy by ID.

        Args:
            prompt_id: Prompt identifier

        Returns:
            PromptPolicy if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT prompt_id, title, wave, category, model, tools,
                       temperature, token_budget, timeout_sec, max_retries,
                       concurrency_class, expected_outputs, prompt, notes
                FROM prompts
                WHERE prompt_id = ?
                """,
                (prompt_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return PromptPolicy(
                prompt_id=row["prompt_id"],
                title=row["title"],
                wave=WaveType(row["wave"]),
                category=row["category"],
                model=row["model"],
                tools=row["tools"] or None,
                temperature=row["temperature"],
                token_budget=row["token_budget"],
                timeout_sec=row["timeout_sec"],
                max_retries=row["max_retries"],
                concurrency_class=ConcurrencyClass(row["concurrency_class"]),
                expected_outputs=row["expected_outputs"],
                prompt=row["prompt"],
                notes=row["notes"],
            )

    def get_by_wave(self, wave: WaveType) -> list[PromptPolicy]:
        """Get all prompt policies for a specific wave.

        Args:
            wave: Wave type to filter by

        Returns:
            List of PromptPolicy objects for the wave
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT prompt_id, title, wave, category, model, tools,
                       temperature, token_budget, timeout_sec, max_retries,
                       concurrency_class, expected_outputs, prompt, notes
                FROM prompts
                WHERE wave = ?
                ORDER BY prompt_id
                """,
                (wave.value,),
            )

            prompts = []
            for row in cursor:
                prompts.append(
                    PromptPolicy(
                        prompt_id=row["prompt_id"],
                        title=row["title"],
                        wave=WaveType(row["wave"]),
                        category=row["category"],
                        model=row["model"],
                        tools=row["tools"] or None,
                        temperature=row["temperature"],
                        token_budget=row["token_budget"],
                        timeout_sec=row["timeout_sec"],
                        max_retries=row["max_retries"],
                        concurrency_class=ConcurrencyClass(row["concurrency_class"]),
                        expected_outputs=row["expected_outputs"],
                        prompt=row["prompt"],
                        notes=row["notes"],
                    )
                )

            return prompts

    def count(self) -> int:
        """Get total number of prompts in registry.

        Returns:
            Count of prompts
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM prompts")
            return cursor.fetchone()[0]


def migrate_tsv_to_sqlite(tsv_path: Path, sqlite_path: Path) -> int:
    """Migrate TSV registry to SQLite database.

    Args:
        tsv_path: Path to existing TSV registry
        sqlite_path: Path to SQLite database (will be created/overwritten)

    Returns:
        Number of prompts migrated

    Raises:
        ValueError: If TSV file is invalid
    """
    from services.registry import TSVRegistryProvider

    # Load from TSV
    tsv_provider = TSVRegistryProvider(tsv_path)
    prompts = tsv_provider.load()

    # Save to SQLite
    sqlite_provider = SQLiteRegistryProvider(sqlite_path)
    sqlite_provider.save(prompts)

    return len(prompts)
