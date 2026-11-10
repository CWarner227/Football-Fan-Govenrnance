"""Lossless event retention must not destroy the sole original on bad input."""

import json

import pytest

from examples.archive_campaign_events import archive


def test_archive_restores_exact_event_bytes_and_keeps_other_artifacts(tmp_path):
    identifier = "a" * 32
    run = tmp_path / "runs" / identifier
    (run / "artifacts").mkdir(parents=True)
    (run / "record.json").write_text(json.dumps({"status": "completed"}))
    original = run / "artifacts/events.jsonl"
    content = ('{"supporter":"caf\u00e9","event":1}\n' * 1000).encode()
    original.write_bytes(content)
    summary = run / "artifacts/summary.jsonl"
    summary.write_text("unchanged")
    info = archive(tmp_path, identifier)
    assert info["compressed_bytes"] < info["original_bytes"]
    assert not original.exists()
    assert archive(tmp_path, identifier)["status"] == "already_archived"
    assert archive(tmp_path, identifier, restore=True)["status"] == "restored"
    assert original.read_bytes() == content
    assert summary.read_text() == "unchanged"


def test_active_run_and_path_input_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="opaque"):
        archive(tmp_path, "../other")
    identifier = "b" * 32
    run = tmp_path / "runs" / identifier
    run.mkdir(parents=True)
    (run / "record.json").write_text(json.dumps({"status": "running"}))
    with pytest.raises(ValueError, match="completed"):
        archive(tmp_path, identifier)
