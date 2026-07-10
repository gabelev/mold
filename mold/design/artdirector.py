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
    "Ray Gun but AI: the design IS the editorial position. The palette is LOUD "
    "and electric — a near-black ground, off-white body, and shouting accents "
    "(electric yellow, hot pink, klein blue, acid green). Nothing muted, "
    "nothing tasteful, nothing beige. You compose each issue from a "
    "parametrized CSS/SVG primitive kit; the primitive assigned to a piece "
    "must ENACT the writer's stance toward it (form follows opinion). Pick the "
    "accent that hits hardest for the piece and push parameters toward risk: a "
    "composition a competent designer would call safe is a failure."
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


def _pull_quote(body: str) -> str:
    """Extract one punchy sentence for the giant pull-quote — a short, link-free
    declarative from the body's middle. Plain text (markdown/links stripped)."""
    plain = _MD_LINK.sub(r"\1", body)
    plain = plain.replace("**", "").replace("*", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
    candidates = [
        s for s in sentences
        if 40 <= len(s) <= 120 and "http" not in s and "—" not in s[:2]
    ]
    pool = candidates or [s for s in sentences if 30 <= len(s) <= 160]
    if not pool:
        return ""
    # Prefer the middle of the piece (the argument, not the setup/wrap).
    return pool[len(pool) // 2]


def _sections_html(authors: list[Artifact]) -> str:
    """The per-piece DOM contract shared by template and fallback shells.

    Primitives target these hooks: section ids piece-0..N, plus .folio .kicker
    .headline (data-text for collision doubling) .dek .pullquote .body. A
    template may restyle freely but must keep the class names.
    """
    out = []
    for i, a in enumerate(authors):
        byline = html_mod.escape(a.metadata.get("byline", "Staff"))
        headline = html_mod.escape(a.metadata.get("headline", byline))
        dek = html_mod.escape(a.metadata.get("dek", ""))
        dek_html = f'\n    <p class="dek">{dek}</p>' if dek else ""
        quote = html_mod.escape(_pull_quote(a.body))
        quote_html = f'\n    <blockquote class="pullquote">{quote}</blockquote>' if quote else ""
        out.append(f"""
  <section id="piece-{i}" class="piece">
    <p class="folio" aria-hidden="true">{i + 1:02d}</p>
    <p class="kicker">{byline}</p>
    <h2 class="headline" data-text="{headline}">{headline}</h2>{dek_html}{quote_html}
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
            f'<aside class="note"><p class="note-kicker">A note from the Editor</p>'
            f'<p>{html_mod.escape(editors_note)}</p></aside>'
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

    note_html = (
        f'\n  <aside class="note"><p class="note-kicker">From the Editor</p>'
        f'<p>{html_mod.escape(editors_note)}</p></aside>'
        if editors_note else ""
    )

    P = PALETTE
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Instrument+Serif:ital@0;1&family=Newsreader:opsz,wght@6..72,400..500&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<title>MOLD — Issue {issue_id}: {theme_esc}</title>
<style>
:root {{
  --substrate: {P["substrate"]}; --agar: {P["agar"]};
  --viridian: {P["viridian"]}; --chartreuse: {P["chartreuse"]};
  --sulphur: {P["sulphur"]}; --bruise: {P["bruise"]}; --orange: {P["orange"]};
  --spore: {P["spore"]}; --accent: {accent_hex};
  --display: "Anton", system-ui, sans-serif;
  --serif: "Instrument Serif", Georgia, serif;
  --body: "Newsreader", Georgia, serif;
  --mono: "Space Mono", ui-monospace, monospace;
  --bg: var(--sulphur); --fg: var(--substrate); --pop: var(--viridian);
}}
* {{ margin: 0; box-sizing: border-box; }}
html, body {{ overflow-x: clip; }}
body {{ background: var(--sulphur); color: var(--substrate); font-family: var(--body); font-size: clamp(1.05rem, 1.35vw, 1.25rem); }}
::selection {{ background: var(--bruise); color: var(--sulphur); }}

/* ---- masthead: electric yellow, the wordmark theme in black ---- */
header.masthead {{
  min-height: 96vh; padding: clamp(1.5rem, 5vw, 4rem); background: var(--sulphur); color: var(--substrate);
  display: grid; grid-template-rows: auto 1fr auto; position: relative; isolation: isolate; overflow: clip;
}}
header.masthead .blob {{
  position: absolute; z-index: 0; width: clamp(200px, 42vw, 620px); height: auto;
  top: -8%; right: -8%; pointer-events: none;
}}
header.masthead .bar {{
  position: absolute; z-index: 0; left: -6%; bottom: 16%; width: 62%; height: clamp(30px, 6vw, 84px);
  background: var(--bruise); transform: rotate(-6deg);
}}
.folio-top {{
  position: relative; z-index: 2; display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  font-family: var(--mono); font-weight: 700; font-size: clamp(0.7rem, 1.4vw, 0.95rem);
  letter-spacing: 0.28em; text-transform: uppercase;
}}
header.masthead h1 {{
  position: relative; z-index: 1; align-self: center;
  font-family: var(--display); text-transform: uppercase;
  font-size: clamp(3.8rem, 23vw, 19rem); line-height: 0.82; letter-spacing: -0.02em;
  color: var(--substrate); margin-left: -0.04em; max-width: 15ch; text-wrap: balance;
}}
header.masthead .strap {{
  position: relative; z-index: 2; font-family: var(--serif); font-style: italic;
  font-size: clamp(1.1rem, 2.6vw, 1.9rem); color: var(--substrate); max-width: 44ch;
}}

/* ---- editor's note: a hard black band ---- */
aside.note {{ background: var(--substrate); color: var(--agar); padding: clamp(3rem, 9vw, 9rem) clamp(1.5rem, 5vw, 5rem); }}
aside.note .note-kicker {{
  font-family: var(--mono); font-weight: 700; font-size: 0.8rem; letter-spacing: 0.3em;
  text-transform: uppercase; color: var(--sulphur); margin-bottom: 1.4rem;
}}
aside.note p:last-child {{
  font-family: var(--serif); font-style: italic; line-height: 1.32;
  font-size: clamp(1.5rem, 4.4vw, 3rem); max-width: 24ch; color: var(--agar);
}}
aside.note p:last-child::first-letter {{ color: var(--chartreuse); }}

/* ---- pieces: full-bleed color blocks, cycling like the home archive ---- */
section.piece {{
  --bg: var(--sulphur); --fg: var(--substrate); --pop: var(--viridian);
  background: var(--bg); color: var(--fg); position: relative; overflow: clip;
  overflow-clip-margin: 8vw;
  padding: clamp(4rem, 12vh, 12rem) clamp(1.5rem, 5vw, 5rem);
  display: grid; column-gap: clamp(1.5rem, 4vw, 4rem);
  grid-template-columns: minmax(0, 1fr) minmax(0, 44rem) minmax(0, 1fr);
  grid-auto-rows: min-content; align-content: start;
}}
/* the cycle: yellow / pink / blue / orange / black */
section.piece:nth-of-type(5n+2) {{ --bg: var(--bruise); --fg: var(--substrate); --pop: var(--viridian); }}
section.piece:nth-of-type(5n+3) {{ --bg: var(--viridian); --fg: var(--agar);      --pop: var(--sulphur);  }}
section.piece:nth-of-type(5n+4) {{ --bg: var(--orange);  --fg: var(--substrate); --pop: var(--viridian); }}
section.piece:nth-of-type(5n+5) {{ --bg: var(--substrate); --fg: var(--agar);    --pop: var(--chartreuse); }}
section.piece > * {{ grid-column: 2; position: relative; z-index: 1; }}
section.piece .folio {{
  position: absolute; top: clamp(1.5rem, 5vh, 4rem); left: clamp(1rem, 2vw, 2.5rem); z-index: 0;
  font-family: var(--display); font-size: clamp(3.5rem, 10vw, 9rem); line-height: 0.8;
  color: transparent; -webkit-text-stroke: 2px var(--pop); transform: rotate(-8deg); opacity: 0.85;
}}
section.piece .kicker {{
  font-family: var(--mono); font-weight: 700; font-size: 0.82rem; letter-spacing: 0.3em;
  text-transform: uppercase; color: var(--pop); margin-bottom: 1.1rem;
}}
section.piece .headline {{
  font-family: var(--display); text-transform: uppercase;
  font-size: clamp(2.6rem, 9vw, 6.5rem); line-height: 0.96; letter-spacing: -0.01em;
  color: var(--fg); margin-bottom: 1.4rem;
}}
section.piece .dek {{
  font-family: var(--serif); font-style: italic; color: var(--pop);
  font-size: clamp(1.2rem, 2.8vw, 1.8rem); line-height: 1.28; margin-bottom: 3rem; max-width: 32ch;
}}
/* pull-quote is a big in-flow callout between the dek and the body — bold and
   collision-proof (it's in the content column, not floated) */
section.piece .pullquote {{
  grid-column: 2; margin: 0.5rem 0 2.8rem; max-width: 20ch;
  quotes: none; border: none; border-top: 4px solid var(--pop);
  padding-top: 1rem; color: var(--pop); transform: rotate(-1.5deg);
  font-family: var(--display); font-size: clamp(1.7rem, 4vw, 3rem); line-height: 0.98;
  text-transform: uppercase;
}}
section.piece .body {{ line-height: 1.6; max-width: 40rem; }}
section.piece .body p {{ margin-bottom: 1.15em; }}
section.piece .body p:first-of-type {{ font-size: 1.15em; }}
section.piece .body a {{ color: var(--pop); text-decoration-thickness: 2px; text-underline-offset: 3px; }}

section.piece:nth-of-type(even) .folio {{ left: auto; right: clamp(1rem, 2vw, 2.5rem); transform: rotate(8deg); }}
section.piece:nth-of-type(even) .pullquote {{ margin-left: auto; text-align: right; transform: rotate(1.5deg); }}

@media (max-width: 900px) {{
  section.piece {{ grid-template-columns: 1fr; }}
  section.piece > * {{ grid-column: 1; }}
  section.piece .folio {{ position: static; font-size: 3.5rem; transform: none; margin-bottom: 0.5rem; opacity: 1; }}
  section.piece:nth-of-type(even) .folio {{ right: auto; }}
  section.piece .pullquote,
  section.piece:nth-of-type(even) .pullquote {{ grid-column: 1; margin-left: 0; max-width: none; text-align: left; transform: rotate(-1.5deg); }}
}}

footer {{
  background: var(--substrate); color: var(--agar);
  padding: clamp(4rem, 10vh, 10rem) clamp(1.5rem, 5vw, 5rem) 6vh;
  font-family: var(--mono); font-size: 0.82rem; line-height: 1.9;
}}
footer a {{ color: var(--chartreuse); }}
/* ---- composed primitives (this issue's moves) ---- */
{css}
</style>
</head>
<body>
<svg width="0" height="0" aria-hidden="true">
  <filter id="bloom">
    <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="11" result="noise"/>
    <feDisplacementMap in="SourceGraphic" in2="noise" scale="70"/>
  </filter>
</svg>
<header class="masthead" id="masthead">
  <svg class="blob" viewBox="0 0 400 400" aria-hidden="true"><circle cx="200" cy="200" r="150" fill="{accent_hex}" filter="url(#bloom)"/></svg>
  <div class="bar" aria-hidden="true"></div>
  <p class="folio-top"><span>MOLD</span><span>Issue {issue_id}</span><span>grown, not written</span></p>
  <h1>{theme_esc}</h1>
  <p class="strap">An autonomous zine about AI culture. The theme precipitated from the public ledger; the Namer titled it last.</p>
</header>{note_html}
<main>
{_sections_html(authors)}
</main>
<footer>
  <p>MOLD · autonomous zine about AI culture · describe, quote briefly, link — never reproduce.</p>
  <p><a href="../../index.html">← archive</a> &nbsp;·&nbsp; <a href="https://www.chaosdimension.fyi/mold">the living ledger →</a></p>
</footer>
</body>
</html>
"""
