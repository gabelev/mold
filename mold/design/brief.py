"""The Claude Design brief: the optional manual-render fork's handoff document.

The autonomous render always ships (nothing blocks on a human); this brief is
ADDITIONALLY emitted per issue so a human can rebuild the same issue by hand
on Claude Design and swap it in via `python -m mold.handoff`. Self-contained:
paste it into Claude Design as-is.
"""

from __future__ import annotations

from ensemble.agent import Artifact

from mold.design.palette import GAMUT, PALETTE


def design_brief(issue: Artifact, design: Artifact, authors: list[Artifact],
                 taboo: list[str]) -> str:
    issue_id = issue.metadata["issue_id"]
    theme = issue.metadata["theme"]
    pieces = []
    for i, a in enumerate(authors):
        pieces.append(
            f"### piece-{i} — {a.metadata.get('byline', 'Staff')}\n"
            f"- headline: {a.metadata.get('headline', '')}\n"
            f"- dek: {a.metadata.get('dek', '')}\n"
            f"- declared stance: **{a.metadata.get('stance', 'neutral')}** "
            f"(the form must ENACT this)\n"
            f"- opens: {a.body.strip()[:220]}…"
        )
    palette_rows = "\n".join(f"- `{name}`: `{hexv}`" for name, hexv in PALETTE.items())
    assignments = "\n".join(
        f"- {a['section']}: {a['primitive']} {a['params']}"
        for a in design.metadata.get("assignments", [])
    )
    taboo_rows = "\n".join(f"- {s}" for s in taboo) or "- (none — first issue)"

    return f"""# Claude Design brief — MOLD Issue {issue_id}: {theme}

Design ONE bespoke, infinite-scroll issue page for MOLD, an autonomous zine
about AI culture. Ray Gun but AI: the design IS the editorial position; the
form of each piece must enact the writer's stance toward its subject.

## The issue
- Theme (precipitated from the public ledger, named last): **{theme}**
- Editor's note (design it as an attributed, first-class element):
  > {issue.metadata.get("editors_note", "")}

## The pieces
{chr(10).join(pieces)}

## Palette (the biological family — issue pages stay in it)
{palette_rows}
Accent chosen by the Art Director this issue: **{design.metadata.get("accent", "viridian")}**
(gamut: accents {list(GAMUT["accents"])}; the bruise never exceeds ~15% coverage)

## Constraint active this issue (obey it)
- **{design.metadata.get("constraint", "house")}**

## Taboo — moves used LAST issue, forbidden now
{taboo_rows}

## What the autonomous Art Director chose (reference, not obligation)
{assignments}
- rationale: {design.metadata.get("rationale", "")}

## Hard constraints (non-negotiable)
- One self-contained HTML file: inline CSS, Google Fonts links OK, no frameworks.
- All type stays selectable text in the DOM; zero raster; SVG (feTurbulence etc.) encouraged.
- Copyright wall: the copy quotes briefly and links out; never embed/reproduce audio or lyrics.
- Keep the piece DOM hooks if you restyle rather than rebuild: `#piece-N`, `.kicker`, `.headline`, `.dek`, `.body`.
- Responsive 375px-1440px, no horizontal scroll; motion behind `prefers-reduced-motion`.
- Relative links: archive at `../../index.html`.

When done: `uv run python -m mold.handoff {issue_id} <your-file.html>` swaps it
in for the autonomous render (verified through the same audit, logged as a
manual render in provenance).
"""
