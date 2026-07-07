"""End-to-end test of the vertical slice on a throwaway git repo.

Proves: theme precipitates from the ledger -> author writes -> editor assembles
-> publish commits Markdown on the `qa` branch. Fully offline (mock model,
seeded ledger, local git).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from mold.config import build_config
from mold.pipeline import build_pipeline


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
    (path / "README.md").write_text("# scratch terrarium\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t",
         "commit", "-q", "-m", "init"],
        check=True,
    )


def test_slice_precipitates_and_commits(tmp_path: Path) -> None:
    content_root = tmp_path / "terrarium"
    _init_repo(content_root)

    cfg = build_config(content_root=content_root)
    ctx = build_pipeline(cfg).run({"issue_id": "000"})

    # Theme emerged from the ledger, was not hardcoded into planning.
    assert ctx["planning"].metadata["theme"] == "CULTURE"
    assert ctx["planning"].metadata["cluster_label"] == "culture"

    # Author produced a review; editor assembled an issue carrying the theme.
    issue = ctx["editor"]
    assert issue.kind == "issue"
    assert "MOLD — Issue 000: CULTURE" in issue.body
    assert "The Critic" in issue.body

    # Publish committed the Markdown on the qa branch.
    result = ctx["publish"]
    assert result.ok, result.detail
    assert result.branch == "qa"
    assert (content_root / "issues" / "000" / "index.md").exists()
    assert (content_root / "issues" / "000" / "planning.md").exists()
