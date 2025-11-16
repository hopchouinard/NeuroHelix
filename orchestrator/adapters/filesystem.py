"""Filesystem utilities for path management, hashing, and locking."""

import fcntl
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional


class LockError(Exception):
    """Exception raised when lock operations fail."""

    pass


class FileLock:
    """File-based locking mechanism for single-run safety."""

    def __init__(self, lock_path: Path, ttl_seconds: int = 7200):
        """Initialize the file lock.

        Args:
            lock_path: Path to the lock file
            ttl_seconds: Time-to-live in seconds (default 2 hours)
        """
        self.lock_path = lock_path
        self.ttl_seconds = ttl_seconds
        self.lock_file: Optional[int] = None
        self.metadata: dict = {}

    def acquire(self, command: str, force: bool = False) -> None:
        """Acquire the lock.

        Args:
            command: Command being executed
            force: Force acquire by removing stale locks

        Raises:
            LockError: If lock cannot be acquired
        """
        # Create lock directory if needed
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing lock
        if self.lock_path.exists():
            if force:
                # Force mode - remove existing lock
                self.lock_path.unlink()
            else:
                existing_metadata = self._read_lock_metadata()
                if existing_metadata:
                    timestamp = existing_metadata.get("timestamp", 0)
                    ttl = self.ttl_seconds  # Always use configured TTL for security
                    age = time.time() - timestamp

                    if age < ttl:
                        raise LockError(
                            f"Lock already held by PID {existing_metadata.get('pid')} "
                            f"for command '{existing_metadata.get('command')}' "
                            f"(age: {int(age)}s, TTL: {int(ttl)}s)"
                        )
                    else:
                        # Stale lock - remove it
                        self.lock_path.unlink()

        # Write lock metadata
        self.metadata = {
            "pid": os.getpid(),
            "command": command,
            "timestamp": time.time(),
            "ttl": self.ttl_seconds,
        }

        # Create lock file
        try:
            self.lock_file = os.open(
                str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
            )
            os.write(self.lock_file, json.dumps(self.metadata).encode())
            os.close(self.lock_file)
            self.lock_file = os.open(str(self.lock_path), os.O_RDONLY)
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError) as e:
            if self.lock_file is not None:
                try:
                    os.close(self.lock_file)
                except:
                    pass
            raise LockError(f"Failed to acquire lock: {e}") from e

    def release(self) -> None:
        """Release the lock."""
        if self.lock_file is not None:
            try:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                os.close(self.lock_file)
            except:
                pass
            finally:
                self.lock_file = None

        if self.lock_path.exists():
            try:
                self.lock_path.unlink()
            except:
                pass

    def _read_lock_metadata(self) -> dict:
        """Read metadata from existing lock file."""
        try:
            with open(self.lock_path, "r") as f:
                return json.load(f)
        except:
            return {}

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal SHA256 hash

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def compute_directory_hash(directory: Path, pattern: str = "*") -> str:
    """Compute combined hash of all files in a directory matching pattern.

    Args:
        directory: Directory path
        pattern: Glob pattern for files (default: "*")

    Returns:
        Hexadecimal SHA256 hash of combined file hashes
    """
    if not directory.exists():
        return ""

    hashes = []
    for file_path in sorted(directory.glob(pattern)):
        if file_path.is_file():
            try:
                file_hash = compute_file_hash(file_path)
                hashes.append(f"{file_path.name}:{file_hash}")
            except:
                pass

    combined = "\n".join(hashes)
    return hashlib.sha256(combined.encode()).hexdigest()


def ensure_directory(path: Path, mode: int = 0o755) -> None:
    """Ensure a directory exists with proper permissions.

    Args:
        path: Directory path
        mode: Permission mode (default: 0o755)
    """
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)


def get_dated_path(base_path: Path, date_str: str, filename: str) -> Path:
    """Get a dated path for outputs.

    Args:
        base_path: Base directory
        date_str: Date string (YYYY-MM-DD)
        filename: Filename

    Returns:
        Full path to dated file
    """
    dated_dir = base_path / date_str
    ensure_directory(dated_dir)
    return dated_dir / filename


def write_json(path: Path, data: dict, indent: int = 2) -> None:
    """Write JSON data to file.

    Args:
        path: File path
        data: Data to write
        indent: JSON indentation (default: 2)
    """
    ensure_directory(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)


def read_json(path: Path) -> dict:
    """Read JSON data from file.

    Args:
        path: File path

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def append_jsonl(path: Path, data: dict) -> None:
    """Append a JSON line to a JSONL file.

    Args:
        path: File path
        data: Data to append
    """
    ensure_directory(path.parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read all entries from a JSONL file.

    Args:
        path: File path

    Returns:
        List of parsed JSON objects
    """
    if not path.exists():
        return []

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries
