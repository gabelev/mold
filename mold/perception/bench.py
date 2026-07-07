"""Phase 0 bench: is the trend visible in embedding space, and can it be named?

    uv run python -m mold.perception.bench manifest.json [--threshold 0.92]

Manifest: a hand-picked JSON list (20-40 Suno tracks across 2-3 weeks):

    [{"id": "t1", "path": "audio/t1.mp3", "week": "2026-W27",
      "link": "https://suno.com/song/...", "note": "optional"}]

The bench embeds every track (transiently — audio is read, never copied),
clusters by cosine similarity, measures week-over-week centroid drift, and
writes a Markdown report whose final section is ledger-drop DRAFTS: the
'field is moving this way' fragments a surveyor would write from.

Pure Python on purpose: 40 tracks need no numpy. The embedder is the seam —
run with MockEmbedder to prove plumbing, swap MERT in to test the hypothesis.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

from mold.perception.embedder import AudioEmbedder, MockEmbedder


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _centroid(vectors: list[Sequence[float]]) -> list[float]:
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def cluster(embedded: list[dict[str, Any]], threshold: float) -> list[list[dict[str, Any]]]:
    """Greedy leader clustering by cosine similarity. Order-stable, dead simple.

    Right-sized for a 20-40 track bench; the production clusterer (pgvector +
    a real algorithm) replaces this without touching the report.
    """
    clusters: list[dict[str, Any]] = []  # {"centroid": [...], "members": [...]}
    for item in embedded:
        best, best_sim = None, threshold
        for c in clusters:
            sim = _cosine(item["vector"], c["centroid"])
            if sim >= best_sim:
                best, best_sim = c, sim
        if best is None:
            clusters.append({"centroid": list(item["vector"]), "members": [item]})
        else:
            best["members"].append(item)
            best["centroid"] = _centroid([m["vector"] for m in best["members"]])
    clusters.sort(key=lambda c: len(c["members"]), reverse=True)
    return [c["members"] for c in clusters]


def week_drift(embedded: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    """Cosine distance between consecutive weeks' centroids — literal drift."""
    weeks: dict[str, list[Sequence[float]]] = {}
    for item in embedded:
        weeks.setdefault(item["week"], []).append(item["vector"])
    ordered = sorted(weeks)
    out = []
    for prev, cur in zip(ordered, ordered[1:]):
        d = 1.0 - _cosine(_centroid(weeks[prev]), _centroid(weeks[cur]))
        out.append((prev, cur, d))
    return out


def render_report(embedder_name: str, clusters: list[list[dict[str, Any]]],
                  drift: list[tuple[str, str, float]], threshold: float) -> str:
    lines = [
        "# Surveyor bench — Phase 0",
        "",
        f"Embedder: `{embedder_name}` · cluster threshold: {threshold}",
        "",
        "## The two questions",
        "1. Is a trend visible as structure/drift in this space?",
        "2. Can a cluster be named in words a surveyor could write from?",
        "",
        "## Clusters (densest first)",
    ]
    for i, members in enumerate(clusters):
        lines.append(f"\n### cluster {i} — {len(members)} tracks")
        for m in members:
            note = f" — {m['note']}" if m.get("note") else ""
            lines.append(f"- [{m['id']}]({m['link']}) ({m['week']}){note}")
        lines.append(f"- **NAME THIS CLUSTER** (CLAP's job later; yours now): _____")
    lines += ["", "## Week-over-week centroid drift"]
    if drift:
        lines += [f"- {a} → {b}: {d:.4f}" for a, b, d in drift]
    else:
        lines.append("- (single week; add a second week to measure drift)")
    lines += [
        "",
        "## Ledger-drop drafts (edit, then drop into the mold workstream)",
    ]
    for i, members in enumerate(clusters):
        if len(members) < 2:
            continue
        links = ", ".join(m["link"] for m in members[:3])
        lines.append(
            f"- fragment: the field is converging on <cluster-{i} name> — "
            f"{len(members)} of {sum(len(c) for c in clusters)} sampled tracks "
            f"cluster here ({links})"
        )
    lines += [
        "",
        "_Copyright wall: audio was read transiently for features and not "
        "retained; only vectors, metadata, and links persist._",
        "",
    ]
    return "\n".join(lines)


def run_bench(manifest_path: Path, embedder: AudioEmbedder, *,
              threshold: float, out_path: Path) -> str:
    manifest = json.loads(manifest_path.read_text())
    embedded = []
    for entry in manifest:
        vector = embedder.embed(Path(entry["path"]))
        embedded.append({**entry, "vector": vector})
    clusters = cluster(embedded, threshold)
    report = render_report(embedder.name, clusters, week_drift(embedded), threshold)
    out_path.write_text(report)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--threshold", type=float, default=0.92)
    ap.add_argument("--out", type=Path, default=Path("bench-report.md"))
    ap.add_argument("--embedder", choices=["mock", "mert"], default="mock")
    args = ap.parse_args(argv)

    if args.embedder == "mert":
        from mold.perception.embedder import MERTEmbedder
        embedder: AudioEmbedder = MERTEmbedder()
    else:
        embedder = MockEmbedder()

    run_bench(args.manifest, embedder, threshold=args.threshold, out_path=args.out)
    print(f"report -> {args.out}")
    if args.embedder == "mock":
        print("NOTE: mock embedder proves plumbing, not the hypothesis — "
              "swap in --embedder mert for the real Phase 0 test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
