"""Manual-render override: publish a hand-built (Claude Design) issue page
IN PLACE OF the autonomous render.

    uv run python -m mold.handoff 000 ~/Downloads/issue-000.html

The swap is clean and audited: the page passes the SAME verification gate as
autonomous renders (copyright wall, doctrine, links), the previous render is
kept alongside as `autonomous.html`, and provenance records which path shipped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ensemble.adapters.vcs import LocalGitVCS

from mold.config import build_config
from mold.verify import audit_html


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m mold.handoff <issue_id> <path-to-html>")
        return 2
    issue_id, src = argv[0], Path(argv[1]).expanduser()
    if not src.exists():
        print(f"no such file: {src}")
        return 1

    cfg = build_config()
    issue_dir = cfg.content_root / "issues" / issue_id
    current = issue_dir / "index.html"
    if not current.exists():
        print(f"issue {issue_id} has no published render to replace")
        return 1

    page = src.read_text()
    errors, warnings = audit_html(page)
    if errors:
        print("REJECTED — the hand-built page fails the same gate as autonomous renders:")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    for w in warnings:
        print(f"  warn: {w}")

    # Provenance: record the swap; keep the autonomous render inspectable.
    prov_path = issue_dir / "provenance.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {"evidence": []}
    prov["render"] = "manual/claude-design"

    vcs = LocalGitVCS(cfg.content_root, author="mold-human <design@mold.zine>")
    result = vcs.write_and_commit(
        {
            f"issues/{issue_id}/index.html": page,
            f"issues/{issue_id}/autonomous.html": current.read_text(),
            f"issues/{issue_id}/provenance.json": json.dumps(prov, indent=1) + "\n",
        },
        message=f"issue {issue_id}: manual render (Claude Design) replaces autonomous",
        branch="qa",
    )
    if not result.ok:
        print(f"handoff failed: {result.detail}")
        return 1
    print(f"issue {issue_id} now ships the hand-built render ({result.sha[:10]} on qa)")
    print("autonomous render preserved as autonomous.html; provenance updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
