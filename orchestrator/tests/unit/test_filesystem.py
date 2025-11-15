"""Unit tests for filesystem utilities."""

import tempfile
import time
from pathlib import Path

import pytest

from adapters.filesystem import (
    FileLock,
    LockError,
    compute_file_hash,
    compute_directory_hash,
    ensure_directory,
    write_json,
    read_json,
    append_jsonl,
    read_jsonl,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_filelock_acquire_and_release(temp_dir):
    """Test acquiring and releasing a file lock."""
    lock_path = temp_dir / "test.lock"
    lock = FileLock(lock_path, ttl_seconds=60)

    # Acquire lock
    lock.acquire(command="test command")
    assert lock_path.exists()

    # Release lock
    lock.release()
    assert not lock_path.exists()


def test_filelock_acquire_twice_fails(temp_dir):
    """Test that acquiring the same lock twice fails."""
    lock_path = temp_dir / "test.lock"

    lock1 = FileLock(lock_path, ttl_seconds=60)
    lock1.acquire(command="test command 1")

    lock2 = FileLock(lock_path, ttl_seconds=60)

    with pytest.raises(LockError) as exc_info:
        lock2.acquire(command="test command 2")

    assert "Lock already held" in str(exc_info.value)

    # Cleanup
    lock1.release()


def test_filelock_stale_lock_removed(temp_dir):
    """Test that stale locks are automatically removed."""
    lock_path = temp_dir / "test.lock"

    # Create lock with 1 second TTL
    lock1 = FileLock(lock_path, ttl_seconds=1)
    lock1.acquire(command="test command 1")

    # Wait for lock to become stale
    time.sleep(2)

    # Should be able to acquire stale lock
    lock2 = FileLock(lock_path, ttl_seconds=60)
    lock2.acquire(command="test command 2")  # Should succeed

    assert lock_path.exists()

    # Cleanup
    lock2.release()


def test_filelock_force_acquire(temp_dir):
    """Test force acquiring a lock."""
    lock_path = temp_dir / "test.lock"

    lock1 = FileLock(lock_path, ttl_seconds=60)
    lock1.acquire(command="test command 1")

    lock2 = FileLock(lock_path, ttl_seconds=60)
    lock2.acquire(command="test command 2", force=True)  # Force should succeed

    assert lock_path.exists()

    # Cleanup
    lock2.release()


def test_filelock_context_manager(temp_dir):
    """Test FileLock as context manager."""
    lock_path = temp_dir / "test.lock"

    with FileLock(lock_path, ttl_seconds=60) as lock:
        lock.acquire(command="test command")
        assert lock_path.exists()

    # Lock should be released after context exit
    assert not lock_path.exists()


def test_compute_file_hash(temp_dir):
    """Test computing file hash."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("Test content")

    hash1 = compute_file_hash(test_file)

    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256 hex digest

    # Same content should produce same hash
    hash2 = compute_file_hash(test_file)
    assert hash1 == hash2

    # Different content should produce different hash
    test_file.write_text("Different content")
    hash3 = compute_file_hash(test_file)
    assert hash1 != hash3


def test_compute_file_hash_nonexistent(temp_dir):
    """Test computing hash of nonexistent file raises error."""
    test_file = temp_dir / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        compute_file_hash(test_file)


def test_compute_directory_hash(temp_dir):
    """Test computing directory hash."""
    # Create test files
    (temp_dir / "file1.txt").write_text("Content 1")
    (temp_dir / "file2.txt").write_text("Content 2")

    hash1 = compute_directory_hash(temp_dir, "*.txt")

    assert isinstance(hash1, str)
    assert len(hash1) == 64

    # Same files should produce same hash
    hash2 = compute_directory_hash(temp_dir, "*.txt")
    assert hash1 == hash2

    # Adding a file should change hash
    (temp_dir / "file3.txt").write_text("Content 3")
    hash3 = compute_directory_hash(temp_dir, "*.txt")
    assert hash1 != hash3


def test_compute_directory_hash_nonexistent(temp_dir):
    """Test computing hash of nonexistent directory returns empty string."""
    nonexistent = temp_dir / "nonexistent"

    hash_val = compute_directory_hash(nonexistent)

    assert hash_val == ""


def test_ensure_directory(temp_dir):
    """Test ensuring directory exists."""
    test_dir = temp_dir / "subdir" / "nested"

    ensure_directory(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()


def test_write_and_read_json(temp_dir):
    """Test writing and reading JSON."""
    test_file = temp_dir / "test.json"
    test_data = {"key1": "value1", "key2": 42, "key3": [1, 2, 3]}

    write_json(test_file, test_data)

    assert test_file.exists()

    loaded_data = read_json(test_file)

    assert loaded_data == test_data


def test_read_json_nonexistent(temp_dir):
    """Test reading nonexistent JSON file raises error."""
    test_file = temp_dir / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        read_json(test_file)


def test_append_and_read_jsonl(temp_dir):
    """Test appending and reading JSONL."""
    test_file = temp_dir / "test.jsonl"

    # Append several entries
    entries = [
        {"id": 1, "data": "first"},
        {"id": 2, "data": "second"},
        {"id": 3, "data": "third"},
    ]

    for entry in entries:
        append_jsonl(test_file, entry)

    # Read all entries
    loaded_entries = read_jsonl(test_file)

    assert len(loaded_entries) == 3
    assert loaded_entries == entries


def test_read_jsonl_nonexistent(temp_dir):
    """Test reading nonexistent JSONL file returns empty list."""
    test_file = temp_dir / "nonexistent.jsonl"

    entries = read_jsonl(test_file)

    assert entries == []


def test_jsonl_with_empty_lines(temp_dir):
    """Test reading JSONL with empty lines."""
    test_file = temp_dir / "test.jsonl"

    # Write entries with empty lines
    with open(test_file, "w") as f:
        f.write('{"id": 1}\n')
        f.write('\n')  # Empty line
        f.write('{"id": 2}\n')
        f.write('  \n')  # Whitespace line
        f.write('{"id": 3}\n')

    entries = read_jsonl(test_file)

    assert len(entries) == 3
    assert entries[0]["id"] == 1
    assert entries[1]["id"] == 2
    assert entries[2]["id"] == 3


def test_write_json_creates_parent_directory(temp_dir):
    """Test that write_json creates parent directories."""
    test_file = temp_dir / "nested" / "deep" / "test.json"

    write_json(test_file, {"test": "data"})

    assert test_file.exists()
    assert test_file.parent.exists()


def test_append_jsonl_creates_parent_directory(temp_dir):
    """Test that append_jsonl creates parent directories."""
    test_file = temp_dir / "nested" / "deep" / "test.jsonl"

    append_jsonl(test_file, {"test": "data"})

    assert test_file.exists()
    assert test_file.parent.exists()
