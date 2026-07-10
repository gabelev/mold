"""Re-render an existing issue's DESIGN from its committed copy — no content
regen, no PERCEIVE, no model authoring. Use after a design-engine change to
re-skin published issues.

    uv run python -m mold.reskin 001

Reconstructs the author + editor artifacts from issues/<id>/index.md, runs the
Art Director over the current kit, and rewrites issues/<id>/index.html (commit
to qa). The autonomous render is what gets replaced; a hand-built manual render
(mold.handoff) is left alone.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from ensemble.agent import Artifact
from ensemble.adapters.vcs import LocalGitVCS
from ensemble.state.taboo import Move, TabooMemory

from mold.config import build_config
from mold.design import ArtDirectorAgent
from mold.design.constraints import pick_constraints
from mold.publish import load_taboo_signatures

# byline -> declared stance (form-follows-opinion downstream)
_STANCE = {"The Critic": "contempt", "The Culture Writer": "fascination"}


def parse_issue(md: str) -> tuple[str, str, str, list[Artifact]]:
    """(issue_id, theme, editors_note, authors) from a committed index.md."""
    chunks = md.split("\n---\n")
    head = chunks[0]
    m = re.search(r"#\s*MOLD\s*—\s*Issue\s+(\S+):\s*(.+)", head)
    issue_id = m.group(1) if m else "000"
    theme = m.group(2).strip() if m else "UNTITLED"
    note = ""
    if "## A note from the Editor" in head:
        note = head.split("## A note from the Editor", 1)[1].strip()

    authors: list[Artifact] = []
    for chunk in chunks[1:]:
        lines = [l for l in chunk.strip().splitlines()]
        if not lines:
            continue
        headline = byline = dek = ""
        body_start = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("## ") and not headline:
                headline = s[3:].strip()
            elif re.fullmatch(r"\*\*(.+)\*\*", s):
                byline = re.fullmatch(r"\*\*(.+)\*\*", s).group(1).strip()
                body_start = i + 1
            elif re.fullmatch(r"\*(.+)\*", s) and not dek:
                dek = re.fullmatch(r"\*(.+)\*", s).group(1).strip()
        body = "\n".join(lines[body_start:]).strip()
        if not (headline and body):
            continue
        authors.append(Artifact(kind="piece", body=body, metadata={
            "byline": byline or "Staff", "headline": headline, "dek": dek,
            "stance": _STANCE.get(byline, "neutral"),
        }))
    return issue_id, theme, note, authors


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m mold.reskin <issue_id>")
        return 2
    issue_id = argv[0]
    cfg = build_config()
    idx = cfg.content_root / "issues" / issue_id / "index.md"
    if not idx.exists():
        print(f"no such issue: {idx}")
        return 1

    parsed_id, theme, note, authors = parse_issue(idx.read_text())
    if not authors:
        print("could not reconstruct any pieces from index.md")
        return 1
    print(f"reskin issue {issue_id}: {theme!r} — {len(authors)} pieces "
          f"({'LIVE' if cfg.live else 'mock'} art direction)")

    taboo = TabooMemory(forbidden=[
        Move(kind="design", signature=s) for s in load_taboo_signatures(cfg.content_root)
    ])
    constraint = pick_constraints(issue_id if issue_id.isdigit() else "0", 1)[0]
    editor = Artifact(kind="issue", body="", metadata={
        "theme": theme, "issue_id": issue_id, "editors_note": note,
    })
    ctx = {"issue_id": issue_id, "authors": authors, "editor": editor,
           "planning": Artifact(kind="planning", body="", metadata={"theme": theme})}
    design = ArtDirectorAgent(cfg.model, taboo=taboo, constraint=constraint).run(ctx)

    from mold.design.brief import design_brief

    brief = design_brief(editor, design, authors, load_taboo_signatures(cfg.content_root))
    vcs = LocalGitVCS(cfg.content_root, author="mold-bot <bot@mold.zine>")
    result = vcs.write_and_commit(
        {
            f"issues/{issue_id}/index.html": design.body,
            f"issues/{issue_id}/claude-design-brief.md": brief,
        },
        message=f"issue {issue_id}: reskin ({constraint}, accent {design.metadata.get('accent')})",
        branch="qa",
    )
    if not result.ok:
        print(f"reskin failed: {result.detail}")
        return 1
    print(f"reskinned {issue_id}: {result.sha[:10]} on qa "
          f"(constraint {constraint}, moves {design.metadata.get('moves')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
