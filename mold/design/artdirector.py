"""The Art Director: art-directs each issue from the primitive kit.

Phase 1.5: the model REASONS about the composition — which primitive enacts
each piece's stance, how hard to push its parameters, which accent dominates
this issue — and returns a proposal that is validated against the kit's
schema bounds, clamped, taboo-checked, and only then rendered. A broken or
absent proposal degrades to the deterministic stance map, so the pipeline
never fails on a bad model day.

Doctrine enforced here: CSS/SVG-first; type stays in the DOM; no raster;
palette moves within the gamut, never out of the biological family.
"""

from __future__ import annotations

import html as html_mod
import json
import re
from pathlib import Path
from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona
from ensemble.providers.model import Message
from ensemble.state.taboo import Move, TabooMemory

from mold.design.constraints import constrained_stance_map
from mold.design.palette import GAMUT, PALETTE
from mold.design.primitives import build_library

BASE_PROMPT = (
    "You are the Art Director of MOLD, an autonomous zine about AI culture. "
    "Ray Gun but AI: the design IS the editorial position. You compose each "
    "issue from a parametrized CSS/SVG primitive kit; the primitive assigned "
    "to a piece must ENACT the writer's stance toward it (form follows "
    "opinion). Push parameters toward risk: a composition a competent "
    "designer would call safe is a failure."
)

_DIRECTION_PROMPT = """Issue theme: {theme!r}. Constraint this issue (obey it): {constraint!r}.

The pieces:
{pieces}

The kit (primitive -> parameter bounds):
{kit}

Accent palette for this issue (pick ONE to dominate): {accents}

Return ONLY a JSON object, no fences:
{{"accent": "<one accent name>",
 "rationale": "<one sentence: how the composition argues with the copy>",
 "assignments": [{{"section": "<section id>", "primitive": "<kit name>", "params": {{<numeric params within bounds>}}}}, ...]}}

One assignment per section, every section covered. Choose parameters near the
edges of their bounds when the stance earns it."""


class ArtDirectorAgent(Agent):
    """Model-directed composition, schema-validated, taboo-checked."""

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
        self.taboo = taboo or TabooMemory()
        self.constraint = constraint
        self.variant = variant

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        editor = context.get("editor")
        theme = (editor.metadata.get("theme") if editor else None) or \
            context["planning"].metadata.get("theme") or "UNTITLED"
        return Perception(data={
            "theme": theme,
            "editors_note": editor.metadata.get("editors_note", "") if editor else "",
            "authors": list(context.get("authors", [])),
            "issue_id": context.get("issue_id", "000"),
        })

    def decide(self, perception: Perception) -> Decision:
        sections = [
            {
                "section": f"piece-{i}",
                "stance": a.metadata.get("stance", "neutral"),
                "headline": a.metadata.get("headline", a.metadata.get("byline", "")),
                "byline": a.metadata.get("byline", "Staff"),
                "excerpt": a.body.strip()[:280],
            }
            for i, a in enumerate(perception.data["authors"])
        ]
        return Decision(data={**perception.data, "sections": sections})

    def execute(self, decision: Decision) -> Artifact:
        theme: str = decision.data["theme"]
        sections: list[dict] = decision.data["sections"]
        authors: list[Artifact] = decision.data["authors"]
        issue_id: str = decision.data["issue_id"]

        proposal = self._direct(theme, sections)
        assignments, accent, rationale = self._validate(proposal, sections)

        moves, css_parts = [], []
        for a in assignments:
            move = Move(kind="design", signature=f"{a['primitive']}:{a['stance']}")
            if self.taboo.is_forbidden(move):
                move = Move(kind="design", signature=f"{a['primitive']}:{a['stance']}:rerolled")
            self.taboo.record(move)
            moves.append(move)
            css_parts.append(self.library.get(a["primitive"]).render(a["params"]))

        page = _render_page(issue_id, theme, decision.data["editors_note"],
                            authors, "\n".join(css_parts), accent)
        return Artifact(
            kind="design",
            body=page,
            metadata={
                "theme": theme,
                "issue_id": issue_id,
                "constraint": self.constraint,
                "variant": self.variant,
                "accent": accent,
                "rationale": rationale,
                "moves": [m.signature for m in moves],
                "assignments": [
                    {"section": a["section"], "stance": a["stance"],
                     "primitive": a["primitive"], "params": dict(a["params"])}
                    for a in assignments
                ],
            },
        )

    # -- model direction ---------------------------------------------------------

    def _direct(self, theme: str, sections: list[dict]) -> dict | None:
        pieces = "\n".join(
            f"- {s['section']}: stance {s['stance']!r}, headline {s['headline']!r}, "
            f"opens: {s['excerpt'][:160]!r}"
            for s in sections
        )
        kit = "\n".join(
            f"- {name}: " + ", ".join(
                f"{p} ({spec.get('min')}..{spec.get('max')})" if "min" in spec
                else f"{p} in {spec['choices']}" if "choices" in spec else p
                for p, spec in self.library.get(name).params_schema.items()
                if p != "section"
            )
            for name in self.library.names()
        )
        from mold.personas.editor import _parse_json

        prompt = _DIRECTION_PROMPT.format(
            theme=theme, constraint=self.constraint, pieces=pieces,
            kit=kit, accents=list(GAMUT["accents"]),
        )
        for attempt in range(2):  # one retry on malformed JSON, then fall back
            reply = self.model.complete([
                Message(role="system", content=self.persona.base_prompt),
                Message(role="user", content=prompt),
            ])
            parsed = _parse_json(reply)
            if parsed is not None:
                return parsed
            prompt += "\n\nYour last reply was not valid JSON. Return ONLY the JSON object."
        return None

    def _validate(
        self, proposal: dict | None, sections: list[dict]
    ) -> tuple[list[dict], str, str]:
        """Clamp the model's proposal to kit bounds; fill gaps from the stance
        map; on total failure fall back to the deterministic composition."""
        stance_map = constrained_stance_map(self.constraint, self.variant)
        by_section = {}
        if proposal and isinstance(proposal.get("assignments"), list):
            for a in proposal["assignments"]:
                if isinstance(a, dict) and a.get("section"):
                    by_section[a["section"]] = a

        accent = proposal.get("accent") if proposal else None
        if accent not in GAMUT["accents"]:
            accent = "viridian"
        rationale = (proposal.get("rationale") or "").strip() if proposal else ""

        out = []
        for s in sections:
            picked = by_section.get(s["section"], {})
            name = picked.get("primitive")
            if name not in self.library.names():
                name, params = stance_map[s["stance"]](s["section"])
            else:
                params = self._clamp(name, picked.get("params") or {})
                params["section"] = s["section"]
            out.append({"section": s["section"], "stance": s["stance"],
                        "primitive": name, "params": params})
        return out, accent, rationale

    def _clamp(self, primitive: str, raw: Mapping[str, Any]) -> dict:
        schema = self.library.get(primitive).params_schema
        params: dict[str, Any] = {}
        for key, spec in schema.items():
            if key == "section":
                continue
            value = raw.get(key)
            if "choices" in spec:
                params[key] = value if value in spec["choices"] else spec["choices"][0]
            elif "min" in spec:
                try:
                    v = float(value)
                except (TypeError, ValueError):
                    v = (spec["min"] + spec["max"]) / 2
                params[key] = max(spec["min"], min(spec["max"], v))
        return params


# -- page shell -----------------------------------------------------------------

_MD_LINK = re.compile(r"\[([^\]]{1,120})\]\((https://[^)\s]+)\)")
_MD_STRONG = re.compile(r"\*\*([^*\n]+)\*\*")
_MD_EM = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def _inline(text: str) -> str:
    """Escape everything, then re-admit the three markdown forms the prose
    rules allow (links, bold, italics). Escape-first means nothing the model
    writes can smuggle markup; https-only links per the copyright wall."""
    esc = html_mod.escape(text)
    esc = _MD_LINK.sub(r'<a href="\2" rel="noopener">\1</a>', esc)
    esc = _MD_STRONG.sub(r"<strong>\1</strong>", esc)
    esc = _MD_EM.sub(r"<em>\1</em>", esc)
    return esc


def _paragraphs(text: str) -> str:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{_inline(p)}</p>" for p in paras)


def _sections_html(authors: list[Artifact]) -> str:
    """The per-piece DOM contract shared by template and fallback shells.

    Primitives target these hooks: section ids piece-0..N, .kicker, .headline
    (with data-text for collision doubling), .dek, .body. A template restyles
    them freely but must keep the class names.
    """
    out = []
    for i, a in enumerate(authors):
        byline = html_mod.escape(a.metadata.get("byline", "Staff"))
        headline = html_mod.escape(a.metadata.get("headline", byline))
        dek = html_mod.escape(a.metadata.get("dek", ""))
        dek_html = f'\n    <p class="dek">{dek}</p>' if dek else ""
        out.append(f"""
  <section id="piece-{i}" class="piece">
    <p class="kicker">{byline}</p>
    <h2 class="headline" data-text="{headline}">{headline}</h2>{dek_html}
    <div class="body">
{_paragraphs(a.body)}
    </div>
  </section>""")
    return "".join(out)


def _render_page(issue_id: str, theme: str, editors_note: str,
                 authors: list[Artifact], css: str, accent: str) -> str:
    theme_esc = html_mod.escape(theme)
    accent_hex = PALETTE.get(accent, PALETTE["viridian"])

    # The page's STAGE is human territory (authored on Claude Design, like the
    # archive chrome); the Art Director composes onto it. With a template at
    # mold/templates/issue.html the composed primitives, sections, and issue
    # data are injected into it; the built-in shell below is the fallback.
    template_path = Path(__file__).resolve().parents[1] / "templates" / "issue.html"
    if template_path.exists():
        note_html = (
            f'<aside class="note"><p>{html_mod.escape(editors_note)}</p></aside>'
            if editors_note else ""
        )
        return (
            template_path.read_text()
            .replace("{{THEME}}", theme_esc)
            .replace("{{ISSUE_ID}}", issue_id)
            .replace("{{EDITORS_NOTE}}", note_html)
            .replace("{{SECTIONS}}", _sections_html(authors))
            .replace("{{COMPOSED_CSS}}", css)
            .replace("{{ACCENT_HEX}}", accent_hex)
        )

    sections = [_sections_html(authors)]

    note_html = (
        f'\n  <aside class="note"><p>{html_mod.escape(editors_note)}</p></aside>'
        if editors_note else ""
    )

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
  --accent: {accent_hex};
}}
* {{ margin: 0; box-sizing: border-box; }}
body {{
  background: var(--substrate);
  color: var(--agar);
  font-family: Georgia, 'Times New Roman', serif;
  overflow-x: hidden;
}}
header.masthead {{
  min-height: 96vh;
  display: grid; place-content: center; text-align: center;
  position: relative; isolation: isolate;
}}
header.masthead::before {{
  content: ""; position: absolute; inset: -10%;
  background:
    radial-gradient(ellipse 80% 50% at 20% 90%, var(--accent), transparent 60%),
    radial-gradient(ellipse 50% 35% at 85% 15%, {PALETTE["bruise"]}66, transparent 70%);
  filter: url(#bloom); opacity: 0.5; z-index: -1;
}}
header.masthead h1 {{
  font-size: clamp(3.4rem, 16vw, 12rem);
  font-weight: 900; letter-spacing: -0.06em; line-height: 0.85;
  color: var(--accent);
  mix-blend-mode: screen;
  text-transform: uppercase;
}}
header.masthead .issue-line {{
  font-size: clamp(0.8rem, 1.6vw, 1rem);
  color: var(--spore); letter-spacing: 0.4em; text-transform: uppercase;
  margin-top: 1.4rem;
}}
aside.note {{
  max-width: 34rem; margin: -8vh auto 0; padding: 0 1.5rem 12vh;
  font-style: italic; color: var(--agar); opacity: 0.85; line-height: 1.6;
}}
main {{ display: grid; gap: 24vh; padding: 8vh clamp(1rem, 7vw, 7rem) 30vh; }}
section.piece .kicker {{
  color: var(--spore); letter-spacing: 0.35em; text-transform: uppercase;
  font-size: 0.78rem; margin-bottom: 0.8rem;
}}
section.piece h2.headline {{
  font-size: clamp(2.2rem, 8vw, 6rem);
  font-weight: 900; letter-spacing: -0.04em; line-height: 0.92;
  color: var(--sulphur);
  margin-bottom: 1rem;
  max-width: 16ch;
}}
section.piece .dek {{
  font-size: clamp(1.05rem, 2.2vw, 1.35rem); font-style: italic;
  color: var(--accent); margin-bottom: 2.2rem; max-width: 38rem;
}}
section.piece .body p {{ margin-bottom: 1.1em; line-height: 1.65; font-size: 1.06rem; }}
footer {{
  padding: 8vh clamp(1rem, 7vw, 7rem);
  color: var(--spore); font-size: 0.85rem; line-height: 1.7;
  border-top: 1px solid {PALETTE["spore"]}33;
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
</header>{note_html}
<main>
{"".join(sections)}
</main>
<footer>
  <p>MOLD is an autonomous zine about AI culture. The theme precipitated from a
  public ledger; the Namer titled it last; nobody chose it. Coverage describes,
  quotes briefly, and links — it never reproduces the work.</p>
  <p><a href="../../index.html">archive</a> · <a href="https://www.chaosdimension.fyi/mold">the living ledger</a></p>
</footer>
</body>
</html>
"""
