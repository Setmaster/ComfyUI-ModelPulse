"""
ModelPulse - Storage Layer

JSON-based persistence for model usage data with cross-platform file locking.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Cross-platform file locking
if sys.platform == "win32":
    import msvcrt

    def _lock_file(f, exclusive: bool = False) -> None:
        """Lock file on Windows using msvcrt."""
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK if exclusive else msvcrt.LK_LOCK, 1)

    def _unlock_file(f) -> None:
        """Unlock file on Windows using msvcrt."""
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass  # Already unlocked or file closed
else:
    import fcntl

    def _lock_file(f, exclusive: bool = False) -> None:
        """Lock file on Unix using fcntl."""
        fcntl.flock(f.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)

    def _unlock_file(f) -> None:
        """Unlock file on Unix using fcntl."""
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class FileLock:
    """Cross-platform file lock context manager using a .lock file."""

    def __init__(self, path: Path, timeout: float = 10.0):
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.timeout = timeout
        self._lock_file = None

    def __enter__(self):
        start = time.time()
        while True:
            try:
                # Create lock file exclusively
                self._lock_file = open(self.lock_path, "x")
                return self
            except FileExistsError:
                # Check if lock is stale (older than timeout)
                try:
                    lock_age = time.time() - self.lock_path.stat().st_mtime
                    if lock_age > self.timeout:
                        # Stale lock, remove it
                        self.lock_path.unlink()
                        continue
                except FileNotFoundError:
                    continue  # Lock was released, retry

                if time.time() - start > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_path}")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock_file:
            self._lock_file.close()
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass


SCHEMA_VERSION = 1


def get_storage_path() -> Path:
    """Get the path to the usage data file."""
    # ComfyUI stores user data in user/default/
    # We need to find the ComfyUI root directory
    # This file is in custom_nodes/ComfyUI-ModelPulse/py/
    current_file = Path(__file__).resolve()
    custom_nodes_dir = current_file.parent.parent.parent  # Go up to custom_nodes
    comfyui_root = custom_nodes_dir.parent  # Go up to ComfyUI root

    storage_dir = comfyui_root / "user" / "default" / "modelpulse"
    storage_dir.mkdir(parents=True, exist_ok=True)

    return storage_dir / "usage_data.json"


def get_backup_path() -> Path:
    """Get the path for backup files."""
    storage_path = get_storage_path()
    return storage_path.with_suffix(".backup.json")


def create_empty_data() -> dict[str, Any]:
    """Create an empty data structure."""
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "version": SCHEMA_VERSION,
        "models": {},
        "metadata": {
            "tracking_started": now,
            "last_updated": now,
        },
    }


def load_data() -> dict[str, Any]:
    """
    Load usage data from JSON file.

    Creates the file with empty data if it doesn't exist.
    Handles schema migrations if needed.
    """
    storage_path = get_storage_path()

    if not storage_path.exists():
        data = create_empty_data()
        save_data(data)
        return data

    try:
        with FileLock(storage_path):
            with open(storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Handle schema migrations
        data = migrate_schema(data)
        return data

    except (json.JSONDecodeError, KeyError) as e:
        # Corrupted file - backup and create fresh
        print(f"[ModelPulse] Warning: Corrupted data file, creating backup. Error: {e}")
        backup_corrupted_file(storage_path)
        data = create_empty_data()
        save_data(data)
        return data


def save_data(data: dict[str, Any]) -> None:
    """
    Save usage data to JSON file with file locking.

    Uses exclusive lock to prevent concurrent writes.
    """
    storage_path = get_storage_path()

    # Update last_updated timestamp
    data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Write to temp file first, then rename (atomic operation)
    temp_path = storage_path.with_suffix(".tmp")

    try:
        with FileLock(storage_path):
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(storage_path)

    except Exception as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise e


def migrate_schema(data: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate data to the current schema version.

    Creates a backup before migration.
    """
    current_version = data.get("version", 0)

    if current_version == SCHEMA_VERSION:
        return data

    # Backup before migration
    backup_path = get_backup_path()
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[ModelPulse] Created backup at {backup_path} before schema migration")

    # Apply migrations sequentially
    if current_version < 1:
        data = migrate_to_v1(data)

    # Future migrations would go here:
    # if current_version < 2:
    #     data = migrate_to_v2(data)

    data["version"] = SCHEMA_VERSION
    return data


def migrate_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate from pre-v1 (or no version) to v1 schema."""
    # Ensure required structure exists
    if "models" not in data:
        data["models"] = {}

    if "metadata" not in data:
        now = datetime.utcnow().isoformat() + "Z"
        data["metadata"] = {
            "tracking_started": now,
            "last_updated": now,
        }

    # Ensure all models have required fields
    for model_id, model_data in data.get("models", {}).items():
        if "usage_log" not in model_data:
            model_data["usage_log"] = []
        if "first_used" not in model_data:
            model_data["first_used"] = model_data.get(
                "last_used", datetime.utcnow().isoformat() + "Z"
            )

    return data


def backup_corrupted_file(storage_path: Path) -> None:
    """Backup a corrupted file for manual recovery."""
    if storage_path.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = storage_path.with_suffix(f".corrupted_{timestamp}.json")
        storage_path.rename(backup_path)
        print(f"[ModelPulse] Backed up corrupted file to {backup_path}")


def cleanup_old_usage_logs(data: dict[str, Any], max_days: int = 365) -> dict[str, Any]:
    """
    Clean up old daily usage logs to prevent unbounded growth.

    Keeps the last `max_days` days of daily data.
    """
    cutoff_date = datetime.utcnow().date()
    from datetime import timedelta

    cutoff_str = (cutoff_date - timedelta(days=max_days)).isoformat()

    for model_data in data.get("models", {}).values():
        usage_log = model_data.get("usage_log", [])
        model_data["usage_log"] = [
            entry for entry in usage_log if entry.get("date", "") >= cutoff_str
        ]

    return data
