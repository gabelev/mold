"""The Art Director: composes each issue's page from the primitive kit.

Consumes the planning brief + the authors' pieces (each with a declared
stance), selects and parametrizes primitives via ensemble's Composer
(form-follows-opinion + taboo memory), and renders ONE bespoke,
self-contained, infinite-scroll HTML page.

Doctrine enforced here: CSS/SVG-first; type stays in the DOM; no raster.
"""

from __future__ import annotations

import html as html_mod
from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona
from ensemble.design.composer import Composer
from ensemble.state.taboo import TabooMemory

from mold.design.constraints import constrained_stance_map
from mold.design.palette import PALETTE
from mold.design.primitives import build_library

BASE_PROMPT = (
    "You are the Art Director of MOLD. You art-direct each issue in CSS/SVG and "
    "argue with the copy. The design is the editorial position: the primitive "
    "assigned to each piece must ENACT the writer's stance toward it."
)


class ArtDirectorAgent(Agent):
    """Composes the issue page. Model calls arrive later (Phase 2, vision pass);
    Phase 1 composition is deterministic kit-recombination under taboo memory."""

    def __init__(
        self,
        model,
        *,
        taboo: TabooMemory | None = None,
        constraint: str = "house",
        variant: int = 0,
        **kw: Any,
    ) -> None:
        super().__init__(Persona(name="art-director", base_prompt=BASE_PROMPT), model, **kw)
        self.library = build_library()
        self.composer = Composer(self.library, taboo=taboo)
        self.constraint = constraint
        self.variant = variant

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        return Perception(data={
            "planning": context["planning"],
            "authors": list(context.get("authors", [])),
            "issue_id": context.get("issue_id", "000"),
        })

    def decide(self, perception: Perception) -> Decision:
        authors = perception.data["authors"]
        # (section_name, declared_stance) pairs drive the composition.
        sections = [
            (f"piece-{i}", a.metadata.get("stance", "neutral"))
            for i, a in enumerate(authors)
        ]
        return Decision(data={**perception.data, "sections": sections})

    def execute(self, decision: Decision) -> Artifact:
        planning: Artifact = decision.data["planning"]
        authors: list[Artifact] = decision.data["authors"]
        issue_id: str = decision.data["issue_id"]
        theme = planning.metadata.get("theme") or "UNTITLED"

        stance_map = constrained_stance_map(self.constraint, self.variant)
        composition = self.composer.compose(
            decision.data["sections"], stance_map, constraint=self.constraint
        )
        css = composition.render(self.library)
        page = _render_page(issue_id, theme, authors, css)

        return Artifact(
            kind="design",
            body=page,
            metadata={
                "theme": theme,
                "issue_id": issue_id,
                "constraint": self.constraint,
                "variant": self.variant,
                "moves": [m.signature for m in composition.moves],
                # Structured description for the taste discriminator's judges.
                "assignments": [
                    {"section": a.section, "stance": a.stance,
                     "primitive": a.primitive, "params": dict(a.params)}
                    for a in composition.assignments
                ],
            },
        )


def _paragraphs(text: str) -> str:
    """Prose -> DOM paragraphs. Type stays text; everything is escaped."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{html_mod.escape(p)}</p>" for p in paras)


def _render_page(issue_id: str, theme: str, authors: list[Artifact], css: str) -> str:
    theme_esc = html_mod.escape(theme)
    sections = []
    for i, a in enumerate(authors):
        byline = html_mod.escape(a.metadata.get("byline", "Staff"))
        sections.append(f"""
  <section id="piece-{i}" class="piece">
    <h2 class="headline" data-text="{byline}">{byline}</h2>
    <div class="body">
{_paragraphs(a.body)}
    </div>
  </section>""")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MOLD — Issue {issue_id}: {theme_esc}</title>
<style>
:root {{
  --substrate: {PALETTE["substrate"]};
  --agar: {PALETTE["agar"]};
  --viridian: {PALETTE["viridian"]};
  --chartreuse: {PALETTE["chartreuse"]};
  --sulphur: {PALETTE["sulphur"]};
  --bruise: {PALETTE["bruise"]};
  --spore: {PALETTE["spore"]};
}}
* {{ margin: 0; box-sizing: border-box; }}
body {{
  background: var(--substrate);
  color: var(--agar);
  font-family: Georgia, 'Times New Roman', serif;
  overflow-x: hidden;
}}
header.masthead {{
  min-height: 92vh;
  display: grid; place-content: center; text-align: center;
  position: relative;
}}
header.masthead h1 {{
  font-size: clamp(3rem, 14vw, 11rem);
  font-weight: 900; letter-spacing: -0.05em;
  color: var(--chartreuse);
  mix-blend-mode: screen;
}}
header.masthead .issue-line {{
  font-size: clamp(0.9rem, 2vw, 1.2rem);
  color: var(--spore); letter-spacing: 0.35em; text-transform: uppercase;
  margin-top: 1rem;
}}
main {{ display: grid; gap: 20vh; padding: 10vh clamp(1rem, 6vw, 6rem) 30vh; }}
section.piece h2.headline {{
  font-size: clamp(2rem, 7vw, 5rem);
  color: var(--sulphur);
  margin-bottom: 1.2rem;
}}
section.piece .body p {{ margin-bottom: 1em; line-height: 1.6; font-size: 1.06rem; }}
footer {{
  padding: 8vh clamp(1rem, 6vw, 6rem);
  color: var(--spore); font-size: 0.85rem; line-height: 1.7;
}}
footer a {{ color: var(--viridian); }}
/* ---- composed primitives (this issue's moves) ---- */
{css}
</style>
</head>
<body>
<svg width="0" height="0" aria-hidden="true">
  <filter id="bloom">
    <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="4" seed="7" result="noise"/>
    <feDisplacementMap in="SourceGraphic" in2="noise" scale="60"/>
  </filter>
</svg>
<header class="masthead" id="masthead">
  <h1>{theme_esc}</h1>
  <p class="issue-line">MOLD · Issue {issue_id} · grown, not written</p>
</header>
<main>
{"".join(sections)}
</main>
<footer>
  <p>MOLD is an autonomous zine about AI culture. The theme precipitated from a
  public ledger; nobody chose it. Coverage describes, quotes briefly, and links
  — it never reproduces the work.</p>
  <p><a href="../../index.html">archive</a></p>
</footer>
</body>
</html>
"""
