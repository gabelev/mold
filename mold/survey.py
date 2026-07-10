"""The daily ledger drop — the surveyor's web-search beat.

    uv run python -m mold.survey

Runs PERCEIVE's broad scan over the AI-culture surfaces and appends the fresh,
dated, sourced candidates to the Chaos Dimension ledger as `fragment:` tasks.
This is the daily-drip cadence from the operating brief: fragments accrete
between issues, and whatever cluster is densest at deadline becomes the theme.

Reuses the web-search PERCEIVE already built — no Suno/MERT needed. The audio
surveyor (Phase 1) becomes a SECOND adapter feeding the same ledger later.

Requires CD_AGENT_TOKEN (write access). Without it this is a no-op that says
so — the daily timer stays green, nothing is written.
"""

from __future__ import annotations

import re

from mold.config import build_config
from mold.perception_web import BROAD_QUERIES, evidence_to_fragment

_URL = re.compile(r"https?://[^\s)\"']+")


def _seen_urls(ledger) -> set[str]:
    """URLs already represented on the board — avoid re-dropping the same story
    every day. The ledger stores the URL inside each fragment's content."""
    seen: set[str] = set()
    try:
        for f in ledger.read():
            seen.update(_URL.findall(f.content))
            url = f.metadata.get("url") if hasattr(f, "metadata") else None
            if url:
                seen.add(url)
    except Exception as e:  # a read hiccup shouldn't block the whole drop
        print(f"warn: could not read existing ledger for dedup ({e})")
    return seen


def main() -> int:
    cfg = build_config()
    if not cfg.ledger_writable:
        print("survey: no CD_AGENT_TOKEN — read-only ledger, nothing to drop "
              "(set the token to enable daily fragments)")
        return 0
    mode = "LIVE web search" if cfg.live else "mock (offline)"
    print(f"survey: broad scan ({mode}) -> {cfg.ledger.workstream} ledger")

    evidence = cfg.perceiver.broad_scan(BROAD_QUERIES, cycle_id="daily")
    seen = _seen_urls(cfg.ledger)

    dropped, skipped = 0, 0
    for e in evidence:
        if e.url in seen:
            skipped += 1
            continue
        cfg.ledger.append(evidence_to_fragment(e))
        seen.add(e.url)
        dropped += 1
        print(f"  + [{e.published}] {e.title[:70]}")

    print(f"survey complete: {dropped} new fragment(s), {skipped} already on the board")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
