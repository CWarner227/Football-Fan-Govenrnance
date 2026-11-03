"""Offline code provenance, including an exact source hash when Git is absent."""

import hashlib
import platform
import subprocess
from pathlib import Path


def source_provenance() -> dict:
    package = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    root = package.parents[1]
    commit = None
    dirty = None
    if (root / ".git").exists():
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
            dirty = bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=root, text=True, stderr=subprocess.DEVNULL
                ).strip()
            )
        except (OSError, subprocess.CalledProcessError):
            pass
    return {
        "source_sha256": digest.hexdigest(),
        "git_commit": commit,
        "git_dirty": dirty,
        "platform": platform.platform(),
    }
