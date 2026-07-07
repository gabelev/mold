"""Phase 0 bench harness: plumbing proof with the mock embedder."""

from __future__ import annotations

import json
from pathlib import Path

from mold.perception.bench import run_bench
from mold.perception.embedder import MockEmbedder


def test_bench_end_to_end(tmp_path: Path) -> None:
    # Two near-identical files (shared bytes -> near vectors) + one outlier.
    (tmp_path / "a.mp3").write_bytes(b"\x01" * 64)
    (tmp_path / "b.mp3").write_bytes(b"\x01" * 63 + b"\x02")
    (tmp_path / "c.mp3").write_bytes(bytes(range(64)))
    manifest = [
        {"id": "a", "path": str(tmp_path / "a.mp3"), "week": "2026-W27", "link": "https://suno.com/song/a"},
        {"id": "b", "path": str(tmp_path / "b.mp3"), "week": "2026-W27", "link": "https://suno.com/song/b"},
        {"id": "c", "path": str(tmp_path / "c.mp3"), "week": "2026-W28", "link": "https://suno.com/song/c"},
    ]
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest))

    report = run_bench(mpath, MockEmbedder(), threshold=0.95, out_path=tmp_path / "report.md")

    assert "cluster 0" in report
    assert "https://suno.com/song/a" in report
    assert "Week-over-week centroid drift" in report
    assert "2026-W27 → 2026-W28" in report
    assert "fragment: the field is converging" in report  # ledger-drop draft
    assert (tmp_path / "report.md").exists()
