"""The warm-start human pick: overrule the discriminator, log the preference.

    uv run python -m mold.pick 000 b

Replaces the issue's page with candidate <letter>, appends the pick to
state/preferences.jsonl (the discriminator's future training data), and
commits on qa. Per the taste-critic spec: each pick is preference data; when
the discriminator reproduces the house revulsions, the human drops out.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from ensemble.adapters.vcs import LocalGitVCS

from mold.config import build_config


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m mold.pick <issue_id> <candidate letter>")
        return 2
    issue_id, letter = argv[0], argv[1].lower()

    cfg = build_config()
    issue_dir = cfg.content_root / "issues" / issue_id
    candidate = issue_dir / "candidates" / f"{letter}.html"
    if not candidate.exists():
        have = sorted(p.stem for p in (issue_dir / "candidates").glob("*.html")) if (issue_dir / "candidates").exists() else []
        print(f"no candidate {letter!r} for issue {issue_id} (have: {', '.join(have) or 'none'})")
        return 1

    # Record the preference BEFORE swapping, so the data survives a bad swap.
    prefs_path = cfg.content_root / "state" / "preferences.jsonl"
    record = {
        "issue": issue_id,
        "picked": letter,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    existing = prefs_path.read_text() if prefs_path.exists() else ""

    vcs = LocalGitVCS(cfg.content_root, author="mold-human <pick@mold.zine>")
    result = vcs.write_and_commit(
        {
            f"issues/{issue_id}/index.html": candidate.read_text(),
            "state/preferences.jsonl": existing + json.dumps(record) + "\n",
        },
        message=f"issue {issue_id}: human pick -> candidate {letter}",
        branch="qa",
    )
    if not result.ok:
        print(f"pick failed: {result.detail}")
        return 1
    print(f"issue {issue_id} now ships candidate {letter!r} ({result.sha[:10]} on qa)")
    print("preference logged to state/preferences.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
