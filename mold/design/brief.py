"""The Claude Design brief: the optional manual-render fork's handoff document.

The autonomous render always ships (nothing blocks on a human); this brief is
ADDITIONALLY emitted per issue so a human can rebuild the same issue by hand
on Claude Design and swap it in via `python -m mold.handoff`. Self-contained:
paste it into Claude Design as-is.
"""

from __future__ import annotations

from ensemble.agent import Artifact

# palette no longer templated into the brief; the electric palette is inlined above


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
    assignments = "\n".join(
        f"- {a['section']}: {a['primitive']} {a['params']}"
        for a in design.metadata.get("assignments", [])
    )
    taboo_rows = "\n".join(f"- {s}" for s in taboo) or "- (none — first issue)"

    return f"""# Claude Design brief — MOLD Issue {issue_id}: {theme}

Design ONE bespoke, infinite-scroll issue page for MOLD, an autonomous zine
about AI culture. Ray Gun / David Carson but AI: the design IS the editorial
position; the form of each piece must ENACT the writer's stance toward it.

## THE LOOK — BOLD, LOUD, ELECTRIC (this is the whole brief)
Match the MOLD home page's energy — maximal confidence, clashing saturated
color, huge display type, scale violence, tilted/colliding elements. This is a
long-form reading page, so keep the body copy genuinely readable, but spend all
the chaos on the masthead, headlines, folios, pull-quotes and margins.

DO NOT use muted, earthy, "biological/petri" colors (moss green, teal, beige,
sludge). That look is dead. Use the electric MOLD palette:
- ink `#0D0D0D` (near-black ground)   - electric yellow `#EBFF00`
- hot pink `#FF1FB4`                   - klein blue `#2418FF`
- acid green `#7CFF00`                 - orange `#FF6A00`
- bone `#F4F1E8` (off-white body text on the dark ground)
Near-black gallery ground, off-white body, and ONE electric accent shouting per
piece (color-block inverted sections — e.g. a full electric-yellow block with
black type — are very on-brand). If a competent designer would call it "too
much," it's right.

Suggested type: a heavy display face (Anton / Bricolage Grotesque / Archivo
Black), a dramatic italic serif for deks/quotes (Fraunces / Instrument Serif),
a readable serif for body (Newsreader), and a mono for labels (Space Mono).

## The issue
- Theme (precipitated from the public ledger, named last): **{theme}**
- Editor's note (design it as an attributed, first-class element):
  > {issue.metadata.get("editors_note", "")}

## The pieces
{chr(10).join(pieces)}
Accent to dominate this issue (the Art Director's pick — one loud color): **{design.metadata.get("accent", "sulphur")}**

## Constraint active this issue (a structural provocation to obey)
- **{design.metadata.get("constraint", "house")}**

## Taboo — moves used LAST issue, forbidden now (keep it never-the-same)
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
