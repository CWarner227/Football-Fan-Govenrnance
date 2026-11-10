"""Losslessly archive/restore a completed run's large event log inside Docker.

Copy this script into the dashboard data volume, then execute there. All other
artifacts and the original scientific manifest stay unchanged. Dashboard event
viewing and complete ZIP export require restoring events first.
"""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


def digest(path, compressed=False):
    sha = hashlib.sha256()
    opener = gzip.open if compressed else open
    with opener(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b""):
            sha.update(chunk)
    return sha.hexdigest()


def archive(root, identifier, restore=False):
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise ValueError("Expected opaque dashboard run ID")
    run = root / "runs" / identifier
    record = json.loads((run / "record.json").read_text())
    if record["status"] != "completed":
        raise ValueError("Only completed runs may be archived")
    original = run / "artifacts/events.jsonl"
    zipped = run / "events.jsonl.gz"
    metadata = run / "event_archive.json"
    if restore:
        if original.exists():
            return {"id": identifier, "status": "already_online"}
        info = json.loads(metadata.read_text())
        temporary = original.with_suffix(".restore.tmp")
        with gzip.open(zipped, "rb") as source, temporary.open("wb") as target:
            for chunk in iter(lambda: source.read(4 * 1024**2), b""):
                target.write(chunk)
        if digest(temporary) != info["uncompressed_sha256"]:
            temporary.unlink()
            raise ValueError("Restored event checksum mismatch")
        temporary.replace(original)
        return {"id": identifier, "status": "restored"}
    if not original.exists():
        if zipped.exists() and metadata.exists():
            return {"id": identifier, "status": "already_archived"}
        raise FileNotFoundError(original)
    temporary = zipped.with_suffix(".tmp")
    sha = hashlib.sha256()
    with original.open("rb") as source, gzip.open(temporary, "wb", compresslevel=1) as target:
        for chunk in iter(lambda: source.read(4 * 1024**2), b""):
            sha.update(chunk)
            target.write(chunk)
    if digest(temporary, compressed=True) != sha.hexdigest():
        temporary.unlink()
        raise ValueError("Compressed event checksum mismatch")
    temporary.replace(zipped)
    info = dict(
        id=identifier,
        original_bytes=original.stat().st_size,
        compressed_bytes=zipped.stat().st_size,
        uncompressed_sha256=sha.hexdigest(),
        restore_command=f"python /app/data/dashboard/archive_campaign_events.py restore {identifier}",
    )
    metadata.write_text(json.dumps(info, indent=2), encoding="utf-8")
    original.unlink()
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("archive", "restore"))
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument("--root", type=Path, default=Path("/app/data/dashboard"))
    args = parser.parse_args()
    for identifier in args.run_ids:
        print(json.dumps(archive(args.root, identifier, args.action == "restore")), flush=True)


if __name__ == "__main__":
    main()
