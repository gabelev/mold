"""Production entrypoint: publish one issue end to end.

    uv run python -m mold.run_issue            # -> qa branch
    MOLD_PROMOTE=1 uv run python -m mold.run_issue  # -> qa, then prod

Bindings are env-driven (see mold.config): with no env set this runs fully
offline on mocks; with ANTHROPIC_API_KEY / CD_AGENT_TOKEN it goes live.
The issue number is whatever comes next in terrarium.
"""

from __future__ import annotations

import os

from mold.config import build_config
from mold.pipeline import VerificationFailed, build_pipeline
from mold.publish import next_issue_id, promote_qa_to_prod


def main() -> int:
    cfg = build_config()
    issue_id = next_issue_id(cfg.content_root)
    mode = "LIVE" if cfg.live else "mock"
    print(f"mold: issue {issue_id} ({mode} model) -> {cfg.content_root}")

    try:
        ctx = build_pipeline(cfg).run({"issue_id": issue_id})
    except VerificationFailed as e:
        print(f"VERIFICATION FAILED — nothing committed:\n{e}")
        return 1

    planning = ctx["planning"]
    verify = ctx["verify"]
    result = ctx["publish"]

    print(f"theme: {planning.metadata['theme']!r} "
          f"(precipitated from cluster {planning.metadata['cluster_label']!r})")
    for w in verify.metadata["warnings"]:
        print(f"  warn: {w}")
    if not result.ok:
        print(f"publish FAILED: {result.detail}")
        return 1
    print(f"published {result.sha[:10]} on {result.branch!r}")

    if os.environ.get("MOLD_PROMOTE") == "1":
        sha = promote_qa_to_prod(cfg.content_root)
        print(f"promoted to prod: {sha[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
