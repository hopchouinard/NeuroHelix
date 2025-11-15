"""Unit tests for registry service."""

import tempfile
from pathlib import Path

import pytest

from config.settings_schema import WaveType
from services.registry import TSVRegistryProvider


class TestTSVRegistryProvider:
    """Tests for TSV registry provider."""

    def test_load_valid_registry(self, tmp_path):
        """Test loading a valid registry file."""
        # Create a minimal valid TSV
        tsv_path = tmp_path / "prompts.tsv"
        tsv_content = """prompt_id\ttitle\twave\tcategory\texpected_outputs\tprompt
test_prompt\tTest Prompt\tsearch\tResearch\ttest.md\tThis is a test prompt
"""
        tsv_path.write_text(tsv_content)

        # Load registry
        provider = TSVRegistryProvider(tsv_path)
        prompts = provider.load()

        # Assertions
        assert len(prompts) == 1
        assert prompts[0].prompt_id == "test_prompt"
        assert prompts[0].title == "Test Prompt"
        assert prompts[0].wave == WaveType.SEARCH
        assert prompts[0].category == "Research"
        assert prompts[0].expected_outputs == "test.md"

    def test_load_missing_file(self, tmp_path):
        """Test loading from non-existent file."""
        tsv_path = tmp_path / "missing.tsv"
        provider = TSVRegistryProvider(tsv_path)

        with pytest.raises(FileNotFoundError):
            provider.load()

    def test_load_missing_columns(self, tmp_path):
        """Test loading file with missing required columns."""
        tsv_path = tmp_path / "prompts.tsv"
        tsv_content = """prompt_id\ttitle
test_prompt\tTest Prompt
"""
        tsv_path.write_text(tsv_content)

        provider = TSVRegistryProvider(tsv_path)

        with pytest.raises(ValueError, match="Missing required columns"):
            provider.load()

    def test_validate_duplicate_ids(self, tmp_path):
        """Test validation catches duplicate prompt IDs."""
        tsv_path = tmp_path / "prompts.tsv"
        tsv_content = """prompt_id\ttitle\twave\tcategory\texpected_outputs\tprompt
duplicate\tTest 1\tsearch\tResearch\ttest1.md\tPrompt 1
duplicate\tTest 2\tsearch\tResearch\ttest2.md\tPrompt 2
"""
        tsv_path.write_text(tsv_content)

        provider = TSVRegistryProvider(tsv_path)
        is_valid, errors = provider.validate()

        assert not is_valid
        assert any("Duplicate prompt IDs" in error for error in errors)

    def test_validate_missing_critical_waves(self, tmp_path):
        """Test validation catches missing critical waves."""
        tsv_path = tmp_path / "prompts.tsv"
        tsv_content = """prompt_id\ttitle\twave\tcategory\texpected_outputs\tprompt
test\tTest\trender\tAnalysis\ttest.md\tTest prompt
"""
        tsv_path.write_text(tsv_content)

        provider = TSVRegistryProvider(tsv_path)
        is_valid, errors = provider.validate()

        assert not is_valid
        assert any("Missing critical wave: SEARCH" in error for error in errors)

    def test_validate_temperature_with_tools(self, tmp_path):
        """Test validation catches high temperature with tools."""
        tsv_path = tmp_path / "prompts.tsv"
        tsv_content = """prompt_id\ttitle\twave\tcategory\ttools\ttemperature\texpected_outputs\tprompt
test\tTest\tsearch\tResearch\tcode_execution\t1.5\ttest.md\tTest prompt
aggregator\tAgg\taggregator\tSynthesis\t\t0.7\tagg.md\tAgg prompt
"""
        tsv_path.write_text(tsv_content)

        provider = TSVRegistryProvider(tsv_path)
        is_valid, errors = provider.validate()

        assert not is_valid
        assert any(
            "tools enabled but temperature > 1.0" in error for error in errors
        )

    def test_default_values(self, tmp_path):
        """Test that default values are applied correctly."""
        tsv_path = tmp_path / "prompts.tsv"
        tsv_content = """prompt_id\ttitle\twave\tcategory\texpected_outputs\tprompt
test\tTest\tsearch\tResearch\ttest.md\tTest prompt
"""
        tsv_path.write_text(tsv_content)

        provider = TSVRegistryProvider(tsv_path)
        prompts = provider.load()

        assert prompts[0].model == "gemini-2.5-pro"
        assert prompts[0].temperature == 0.7
        assert prompts[0].timeout_sec == 120
        assert prompts[0].max_retries == 3


@pytest.fixture
def sample_registry(tmp_path):
    """Fixture providing a sample valid registry."""
    tsv_path = tmp_path / "prompts.tsv"
    tsv_content = """prompt_id\ttitle\twave\tcategory\tmodel\ttemperature\texpected_outputs\tprompt
prompt1\tPrompt 1\tsearch\tResearch\tgemini-2.5-pro\t0.7\toutput1.md\tPrompt 1 text
prompt2\tPrompt 2\tsearch\tMarket\tgemini-2.5-pro\t0.8\toutput2.md\tPrompt 2 text
aggregator\tAggregator\taggregator\tSynthesis\tgemini-2.5-pro\t0.7\tdaily_report.md\tAggregator prompt
"""
    tsv_path.write_text(tsv_content)
    return tsv_path
