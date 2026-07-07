"""Vertical slice entry point.

Runs the whole thin path on mocks and prints what happened:

    Planning (reads the seeded ledger, precipitates the theme)
      -> one Author (The Critic)
      -> Editor (assembles the issue)
      -> Publish (commits Markdown into terrarium on the `qa` branch)

    uv run python -m mold.slice
"""

from __future__ import annotations

from mold.config import build_config
from mold.pipeline import build_pipeline


def main() -> int:
    cfg = build_config()
    pipeline = build_pipeline(cfg)
    ctx = pipeline.run({"issue_id": "000"})

    planning = ctx["planning"]
    issue = ctx["editor"]
    result = ctx["publish"]

    print("=== PLANNING (theme precipitated from ledger) ===")
    print(f"theme: {planning.metadata['theme']!r} "
          f"(cluster {planning.metadata['cluster_label']!r})")
    print()
    print("=== ISSUE (first 400 chars) ===")
    print(issue.body[:400])
    print("...")
    print()
    print("=== PUBLISH ===")
    if result.ok:
        print(f"committed {result.sha[:10]} on branch {result.branch!r} "
              f"-> {cfg.content_root}")
        return 0
    print(f"publish FAILED: {result.detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
