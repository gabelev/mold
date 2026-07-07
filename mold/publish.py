"""Publishing: issue files -> terrarium (qa), archive index, drift write-back,
and qa -> prod promotion.

The content repo is the transaction log: one commit per issue carrying the
page, the copy, the planning brief, the regenerated archive index, and the
bumped persona drift-state — so `git log` reads as the zine's history.
"""

from __future__ import annotations

import html as html_mod
import json
import subprocess
from pathlib import Path

from ensemble.agent import Artifact

from mold.design.palette import PALETTE


def next_issue_id(content_root: Path) -> str:
    """Next zero-padded issue number from what's already in terrarium."""
    issues_dir = content_root / "issues"
    existing = [int(p.name) for p in issues_dir.glob("[0-9]*") if p.name.isdigit()] if issues_dir.exists() else []
    return f"{(max(existing) + 1 if existing else 0):03d}"


def issue_files(issue: Artifact, design: Artifact, content_root: Path) -> dict[str, str]:
    """All files for one issue commit, keyed by path relative to terrarium."""
    issue_id = issue.metadata["issue_id"]
    files = {
        f"issues/{issue_id}/index.html": design.body,
        f"issues/{issue_id}/index.md": issue.body,
        f"issues/{issue_id}/planning.md": issue.metadata["planning_body"],
        "index.html": _archive_index(content_root, issue_id, issue.metadata["theme"]),
    }
    # Warm-start instrument: every candidate treatment ships alongside the
    # chosen one so a human can overrule the discriminator (mold.pick) and the
    # pick becomes preference data.
    for letter, page in design.metadata.get("candidate_pages", {}).items():
        files[f"issues/{issue_id}/candidates/{letter}.html"] = page
    if design.metadata.get("candidate_pages"):
        files[f"issues/{issue_id}/candidates/CHOICE.md"] = _choice_md(design)
    files.update(_drift_files(content_root, issue.metadata["theme"], design))
    return files


def _choice_md(design: Artifact) -> str:
    chosen = design.metadata.get("chosen_candidate", "?")
    dissent = design.metadata.get("dissent", "")
    lines = [
        "# Candidate treatments",
        "",
        f"Discriminator chose **{chosen}** "
        f"(constraint `{design.metadata.get('constraint')}`, "
        f"variant {design.metadata.get('variant')}).",
        "",
        "To overrule (warm-start preference data):",
        "",
        "    uv run python -m mold.pick <issue> <letter>",
        "",
    ]
    if dissent:
        lines += ["Shipped WITH dissent (no candidate passed the full panel):", "", f"> {dissent}", ""]
    return "\n".join(lines)


def _drift_files(content_root: Path, theme: str, design: Artifact) -> dict[str, str]:
    """Bump persona drift-state: this issue's residue feeds the next one.

    Also persist the design moves used, which become next issue's taboo list.
    """
    out: dict[str, str] = {}
    state_path = content_root / "state" / "the-critic.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"version": 0, "obsessions": [], "residue": {}}
    state["version"] = int(state.get("version", 0)) + 1
    state["residue"] = {"last_theme": theme}
    out["state/the-critic.json"] = json.dumps(state, indent=2, sort_keys=True) + "\n"
    out["state/taboo.json"] = json.dumps(
        {"forbidden_moves": design.metadata.get("moves", [])}, indent=2, sort_keys=True
    ) + "\n"
    return out


def load_taboo_signatures(content_root: Path) -> list[str]:
    """Last issue's moves = this issue's forbidden list."""
    p = content_root / "state" / "taboo.json"
    if not p.exists():
        return []
    return list(json.loads(p.read_text()).get("forbidden_moves", []))


def _archive_index(content_root: Path, new_issue_id: str, new_theme: str) -> str:
    """Regenerate the root archive page listing every issue.

    The page chrome is HUMAN territory (per the design-engine spec: the fixed
    shell is authored, e.g. on Claude Design — only per-issue composition is
    autonomous). If the instance ships a template at mold/templates/archive.html
    it is used verbatim with {{ISSUE_LIST}} (and optional {{ISSUE_COUNT}})
    replaced; the built-in page below is only the fallback until one exists.
    """
    issues_dir = content_root / "issues"
    entries: dict[str, str] = {}
    if issues_dir.exists():
        for p in sorted(issues_dir.glob("[0-9]*")):
            if p.name.isdigit():
                title = _title_from_md(p / "index.md") or p.name
                entries[p.name] = title
    entries[new_issue_id] = new_theme

    rows = "\n".join(
        f'    <li><a href="issues/{i}/index.html"><span class="num">{i}</span> {html_mod.escape(t)}</a></li>'
        for i, t in sorted(entries.items(), reverse=True)
    )

    template_path = Path(__file__).resolve().parent / "templates" / "archive.html"
    if template_path.exists():
        return (
            template_path.read_text()
            .replace("{{ISSUE_LIST}}", rows)
            .replace("{{ISSUE_COUNT}}", str(len(entries)))
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MOLD — archive</title>
<style>
* {{ margin: 0; box-sizing: border-box; }}
body {{ background: {PALETTE["substrate"]}; color: {PALETTE["agar"]};
       font-family: Georgia, serif; min-height: 100vh;
       display: grid; place-content: center; padding: 10vh 2rem; }}
h1 {{ font-size: clamp(3rem, 12vw, 9rem); color: {PALETTE["chartreuse"]};
      letter-spacing: -0.05em; font-weight: 900; }}
p.tag {{ color: {PALETTE["spore"]}; letter-spacing: 0.3em; text-transform: uppercase;
         font-size: 0.85rem; margin: 1rem 0 4rem; }}
ul {{ list-style: none; }}
li a {{ color: {PALETTE["agar"]}; text-decoration: none; font-size: 1.4rem;
        display: block; padding: 0.6rem 0; border-bottom: 1px solid {PALETTE["spore"]}44; }}
li a:hover {{ color: {PALETTE["sulphur"]}; }}
.num {{ color: {PALETTE["viridian"]}; font-variant-numeric: tabular-nums; margin-right: 1rem; }}
</style>
</head>
<body>
<main>
  <h1>MOLD</h1>
  <p class="tag">an autonomous zine about AI culture</p>
  <ul>
{rows}
  </ul>
</main>
</body>
</html>
"""


def _title_from_md(md_path: Path) -> str | None:
    if not md_path.exists():
        return None
    first = md_path.read_text().splitlines()[0] if md_path.read_text().strip() else ""
    # "# MOLD — Issue NNN: THEME" -> "THEME"
    return first.rsplit(":", 1)[-1].strip() if ":" in first else None


def promote_qa_to_prod(content_root: Path) -> str:
    """Fast-forward prod to qa. Returns the prod HEAD sha."""
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(content_root), *args], capture_output=True, text=True)

    if git("rev-parse", "--verify", "prod").returncode != 0:
        r = git("branch", "prod", "qa")
    else:
        current = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if current == "prod":
            r = git("merge", "--ff-only", "qa")
        else:
            # Move the prod ref without touching the working tree.
            r = git("fetch", ".", "qa:prod")
    if r.returncode != 0:
        raise RuntimeError(f"promotion failed: {r.stderr.strip()}")
    return git("rev-parse", "prod").stdout.strip()
