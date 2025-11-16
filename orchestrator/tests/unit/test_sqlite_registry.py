"""Unit tests for SQLiteRegistryProvider."""

import tempfile
from pathlib import Path

import pytest

from config.settings_schema import PromptPolicy, WaveType, ConcurrencyClass
from services.sqlite_registry import SQLiteRegistryProvider, migrate_tsv_to_sqlite


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def sample_prompts():
    """Create sample prompt policies."""
    return [
        PromptPolicy(
            prompt_id="test_prompt_1",
            title="Test Prompt 1",
            wave=WaveType.SEARCH,
            category="Research",
            model="gemini-2.5-flash",
            temperature=0.7,
            token_budget=32000,
            timeout_sec=120,
            max_retries=3,
            concurrency_class=ConcurrencyClass.MEDIUM,
            expected_outputs="test_prompt_1.md",
            prompt="Test prompt 1 text",
        ),
        PromptPolicy(
            prompt_id="test_prompt_2",
            title="Test Prompt 2",
            wave=WaveType.AGGREGATOR,
            category="Synthesis",
            model="gemini-2.5-pro",
            temperature=0.8,
            token_budget=64000,
            timeout_sec=300,
            max_retries=3,
            concurrency_class=ConcurrencyClass.SEQUENTIAL,
            expected_outputs="test_report.md",
            prompt="Test prompt 2 text",
            notes="Test notes",
        ),
    ]


def test_sqlite_provider_initialization(temp_db):
    """Test SQLite provider initialization creates schema."""
    provider = SQLiteRegistryProvider(temp_db)

    # Database should be created
    assert temp_db.exists()

    # Should have prompts table
    import sqlite3

    with sqlite3.connect(temp_db) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='prompts'"
        )
        assert cursor.fetchone() is not None


def test_save_and_load_prompts(temp_db, sample_prompts):
    """Test saving and loading prompts."""
    provider = SQLiteRegistryProvider(temp_db)

    # Save prompts
    provider.save(sample_prompts)

    # Load prompts
    loaded = provider.load()

    assert len(loaded) == 2
    assert loaded[0].prompt_id == "test_prompt_1"
    assert loaded[1].prompt_id == "test_prompt_2"
    assert loaded[0].wave == WaveType.SEARCH
    assert loaded[1].wave == WaveType.AGGREGATOR


def test_save_rejects_duplicates(temp_db, sample_prompts):
    """Test that saving rejects duplicate prompt IDs."""
    provider = SQLiteRegistryProvider(temp_db)

    # Create duplicate
    duplicate_prompts = sample_prompts + [sample_prompts[0]]

    with pytest.raises(ValueError) as exc_info:
        provider.save(duplicate_prompts)

    assert "Duplicate prompt IDs" in str(exc_info.value)


def test_get_by_id(temp_db, sample_prompts):
    """Test getting a prompt by ID."""
    provider = SQLiteRegistryProvider(temp_db)
    provider.save(sample_prompts)

    # Get existing prompt
    prompt = provider.get_by_id("test_prompt_1")
    assert prompt is not None
    assert prompt.prompt_id == "test_prompt_1"
    assert prompt.title == "Test Prompt 1"

    # Get non-existent prompt
    prompt = provider.get_by_id("nonexistent")
    assert prompt is None


def test_get_by_wave(temp_db, sample_prompts):
    """Test getting prompts by wave."""
    provider = SQLiteRegistryProvider(temp_db)
    provider.save(sample_prompts)

    # Get search wave
    search_prompts = provider.get_by_wave(WaveType.SEARCH)
    assert len(search_prompts) == 1
    assert search_prompts[0].prompt_id == "test_prompt_1"

    # Get aggregator wave
    aggregator_prompts = provider.get_by_wave(WaveType.AGGREGATOR)
    assert len(aggregator_prompts) == 1
    assert aggregator_prompts[0].prompt_id == "test_prompt_2"

    # Get empty wave
    tagger_prompts = provider.get_by_wave(WaveType.TAGGER)
    assert len(tagger_prompts) == 0


def test_count(temp_db, sample_prompts):
    """Test counting prompts."""
    provider = SQLiteRegistryProvider(temp_db)

    # Empty database
    assert provider.count() == 0

    # After saving
    provider.save(sample_prompts)
    assert provider.count() == 2


def test_save_overwrites_existing(temp_db, sample_prompts):
    """Test that save overwrites existing prompts."""
    provider = SQLiteRegistryProvider(temp_db)

    # Save initial prompts
    provider.save(sample_prompts)
    assert provider.count() == 2

    # Save different prompts (overwrites)
    new_prompts = [sample_prompts[0]]  # Only one prompt
    provider.save(new_prompts)
    assert provider.count() == 1

    loaded = provider.load()
    assert len(loaded) == 1
    assert loaded[0].prompt_id == "test_prompt_1"


def test_preserve_all_fields(temp_db, sample_prompts):
    """Test that all fields are preserved during save/load."""
    provider = SQLiteRegistryProvider(temp_db)
    provider.save(sample_prompts)

    loaded = provider.load()
    original = sample_prompts[1]  # Use the one with notes
    persisted = loaded[1]

    assert persisted.prompt_id == original.prompt_id
    assert persisted.title == original.title
    assert persisted.wave == original.wave
    assert persisted.category == original.category
    assert persisted.model == original.model
    assert persisted.temperature == original.temperature
    assert persisted.token_budget == original.token_budget
    assert persisted.timeout_sec == original.timeout_sec
    assert persisted.max_retries == original.max_retries
    assert persisted.concurrency_class == original.concurrency_class
    assert persisted.expected_outputs == original.expected_outputs
    assert persisted.prompt == original.prompt
    assert persisted.notes == original.notes


def test_migration_tsv_to_sqlite(temp_db):
    """Test migrating from TSV to SQLite."""
    import tempfile

    # Create temporary TSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        tsv_path = Path(f.name)
        f.write("prompt_id\ttitle\twave\tcategory\tmodel\ttools\ttemperature\ttoken_budget\ttimeout_sec\tmax_retries\tconcurrency_class\texpected_outputs\tprompt\tnotes\n")
        f.write("test1\tTest 1\tsearch\tResearch\tgemini-2.5-flash\t\t0.7\t32000\t120\t3\tmedium\ttest1.md\tTest prompt\t\n")
        f.write("test2\tTest 2\taggregator\tSynthesis\tgemini-2.5-pro\t\t0.8\t64000\t300\t3\tsequential\ttest2.md\tAnother prompt\tNotes\n")

    try:
        # Perform migration
        count = migrate_tsv_to_sqlite(tsv_path, temp_db)

        assert count == 2

        # Verify migration
        provider = SQLiteRegistryProvider(temp_db)
        prompts = provider.load()

        assert len(prompts) == 2
        assert prompts[0].prompt_id == "test1"
        assert prompts[1].prompt_id == "test2"

    finally:
        # Cleanup
        tsv_path.unlink()


def test_schema_version_tracking(temp_db):
    """Test that schema version is tracked."""
    provider = SQLiteRegistryProvider(temp_db)

    import sqlite3

    with sqlite3.connect(temp_db) as conn:
        cursor = conn.execute("SELECT version FROM schema_version")
        version = cursor.fetchone()[0]
        assert version == SQLiteRegistryProvider.SCHEMA_VERSION


def test_indices_created(temp_db):
    """Test that indices are created."""
    provider = SQLiteRegistryProvider(temp_db)

    import sqlite3

    with sqlite3.connect(temp_db) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indices = [row[0] for row in cursor.fetchall()]

        # Should have indices for wave and category
        assert "idx_wave" in indices
        assert "idx_category" in indices
