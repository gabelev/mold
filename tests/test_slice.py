"""End-to-end test of the full pipeline on a throwaway git repo.

Proves: theme precipitates from the ledger -> author writes -> editor
assembles -> Art Director composes the page -> verification passes ->
publish commits page + copy + archive + drift-state on qa. Fully offline.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mold.config import build_config
from mold.pipeline import build_pipeline
from mold.publish import next_issue_id, promote_qa_to_prod


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


def test_full_pipeline_end_to_end(tmp_path: Path) -> None:
    content_root = tmp_path / "terrarium"
    _init_repo(content_root)

    cfg = build_config(content_root=content_root)
    issue_id = next_issue_id(cfg.content_root)
    assert issue_id == "000"

    ctx = build_pipeline(cfg).run({"issue_id": issue_id})

    # Theme emerged from the ledger, was not hardcoded into planning.
    assert ctx["planning"].metadata["theme"] == "CULTURE"
    assert ctx["planning"].metadata["cluster_label"] == "culture"

    # Both masthead voices wrote; editor assembled; Art Director rendered.
    assert len(ctx["authors"]) == 2
    assert "MOLD — Issue 000: CULTURE" in ctx["editor"].body
    page = ctx["design"].body
    assert page.startswith("<!doctype html")
    assert "The Critic" in page and "The Culture Writer" in page
    assert "feTurbulence" in page                       # CSS/SVG-first
    assert "<audio" not in page and "<img" not in page  # copyright wall / no raster
    assert ctx["design"].metadata["moves"]              # taboo memory fed
    # The discriminator chose among N candidates.
    assert ctx["design"].metadata["chosen_candidate"] in "abc"

    # Verification passed.
    assert ctx["verify"].metadata["ok"], ctx["verify"].body

    # Publish committed everything on qa.
    result = ctx["publish"]
    assert result.ok, result.detail
    assert result.branch == "qa"
    for rel in (
        "issues/000/index.html",
        "issues/000/index.md",
        "issues/000/planning.md",
        "issues/000/candidates/a.html",   # warm-start: all treatments kept
        "issues/000/candidates/CHOICE.md",
        "index.html",              # regenerated archive
        "state/the-critic.json",   # drift bumped
        "state/taboo.json",        # this issue's moves -> next issue's taboo
    ):
        assert (content_root / rel).exists(), rel

    state = json.loads((content_root / "state/the-critic.json").read_text())
    assert state["version"] == 1
    assert state["residue"]["last_theme"] == "CULTURE"

    # Promotion fast-forwards prod to qa.
    sha = promote_qa_to_prod(content_root)
    assert sha == result.sha

    # Issue numbering advances.
    assert next_issue_id(content_root) == "001"


def test_taboo_rolls_between_issues(tmp_path: Path) -> None:
    """Issue N+1 must not reuse issue N's design moves verbatim."""
    content_root = tmp_path / "terrarium"
    _init_repo(content_root)
    cfg = build_config(content_root=content_root)

    first = build_pipeline(cfg).run({"issue_id": "000"})
    # Rebuild the pipeline: it reloads taboo from the committed state.
    second = build_pipeline(cfg).run({"issue_id": "001"})

    first_moves = set(first["design"].metadata["moves"])
    second_moves = set(second["design"].metadata["moves"])
    # Same stance would pick the same primitive; taboo forces the reroll marker.
    assert first_moves.isdisjoint(second_moves)
