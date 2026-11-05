"""Atomic JSON records in confined opaque-ID directories.

The local application's storage root must be trusted; untrusted HTTP input can
select only one of two collections and a 32-character lowercase UUID identifier.
"""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

MAX_RECORD_BYTES = 16 * 1024 * 1024
COLLECTIONS = frozenset({"runs", "configurations"})
IDENTIFIER = re.compile(r"[0-9a-f]{32}\Z")


class FileRepository:
    def __init__(self, root: Path):
        requested = Path(root).absolute()
        for component in (requested, *requested.parents):
            if component.is_symlink() or component.is_junction():
                raise ValueError("Symlink storage roots are not allowed")
        requested.mkdir(parents=True, exist_ok=True)
        self.root = requested.resolve()

    def _safe(self, path: Path) -> Path:
        if not path.is_relative_to(self.root):
            raise ValueError("Storage path escapes root")
        for component in (path, *path.parents):
            if component == self.root:
                break
            if component.is_symlink() or component.is_junction():
                raise ValueError("Symlink storage paths are not allowed")
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Storage path escapes root")
        return path

    def _collection(self, collection: str) -> Path:
        if collection not in COLLECTIONS:
            raise ValueError("Unknown collection")
        return self._safe(self.root / collection)

    def _directory(self, collection: str, identifier: str) -> Path:
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise ValueError("Record ID must be 32 lowercase hexadecimal characters")
        return self._safe(self._collection(collection) / identifier)

    def directory(self, collection: str, identifier: str) -> Path:
        path = self._directory(collection, identifier)
        path.mkdir(parents=True, exist_ok=True)
        return self._safe(path)

    def save(self, collection: str, identifier: str, record: dict) -> None:
        if not isinstance(record, dict):
            raise ValueError("Records must be JSON objects")
        payload = json.dumps(record, allow_nan=False, ensure_ascii=False).encode("utf-8")
        if len(payload) > MAX_RECORD_BYTES:
            raise ValueError("Record exceeds maximum size")
        directory = self.directory(collection, identifier)
        destination = self._safe(directory / "record.json")
        descriptor, temporary = tempfile.mkstemp(prefix=".record-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            self._safe(destination)
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def get(self, collection: str, identifier: str) -> dict:
        path = self._safe(self._directory(collection, identifier) / "record.json")
        try:
            if path.stat().st_size > MAX_RECORD_BYTES:
                raise ValueError("Record exceeds maximum size")
            with path.open("rb") as handle:
                payload = handle.read(MAX_RECORD_BYTES + 1)
            if len(payload) > MAX_RECORD_BYTES:
                raise ValueError("Record exceeds maximum size")
            value = json.loads(payload)
            if not isinstance(value, dict):
                raise ValueError("Stored record must be a JSON object")
            return value
        except FileNotFoundError as error:
            raise KeyError(identifier) from error

    def list(self, collection: str) -> list[dict]:
        directory = self._collection(collection)
        if not directory.exists():
            return []
        records = []
        for child in sorted(directory.iterdir()):
            if IDENTIFIER.fullmatch(child.name):
                try:
                    records.append(self.get(collection, child.name))
                except KeyError:
                    continue
        return records

    def delete(self, collection: str, identifier: str) -> None:
        directory = self._directory(collection, identifier)
        if not directory.exists():
            raise KeyError(identifier)
        # Reject links throughout the tree before recursive deletion (including Windows junctions).
        for parent, dirs, files in os.walk(directory, followlinks=False):
            self._safe(Path(parent))
            for name in dirs + files:
                self._safe(Path(parent) / name)
        shutil.rmtree(directory)
