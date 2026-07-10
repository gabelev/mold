"""The primitive kit (design-production engine).

Parametrized CSS/SVG primitives implementing ensemble's `Primitive` protocol.
Two families:

  TEXTURE (surface effects on the petri aesthetic)
    colonization  — scroll-linked feTurbulence bloom overlay (the signature)
    collision     — headline overlaps itself, rotated, blend-moded
    decay         — progressive type destruction down the body
    agar          — body sits on a tilted pale growth-medium slab

  STRUCTURE (layout-as-argument — the interesting half)
    bleed         — the headline runs off the edge of the page, clipped
    scale-violence— a giant drop-word / oversized first line
    broken-column — body splits into unstable columns with rotated intrusions
    marginalia    — dek + kicker rotated vertically into the margin

Type stays in the DOM always; nothing here produces raster. Each primitive
scopes its CSS to `#piece-N` and the shared per-piece DOM hooks the shell
emits: .kicker .headline .dek .body .pullquote .folio.
"""

from __future__ import annotations

from typing import Any, Mapping

from mold.design.palette import PALETTE

_ACCENTS = ["viridian", "chartreuse", "sulphur", "bruise"]


# -- TEXTURE -------------------------------------------------------------------

class ColonizationOverlay:
    """The signature: mold blooms over the section as you scroll into it."""

    name = "colonization"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "coverage": {"type": "float", "min": 0.2, "max": 0.9},
            "base_frequency": {"type": "float", "min": 0.008, "max": 0.06},
            "accent": {"type": "str", "choices": _ACCENTS},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        coverage = float(params.get("coverage", 0.5))
        return f"""
/* colonization: {s} */
#{s} {{ position: relative; isolation: isolate; }}
#{s}::after {{
  content: ""; position: absolute; inset: -6%; pointer-events: none;
  background:
    radial-gradient(ellipse 120% 60% at 8% 108%, var(--pop), transparent 62%),
    radial-gradient(ellipse 60% 44% at 92% 96%, var(--pop), transparent 70%);
  filter: url(#bloom); mix-blend-mode: multiply; opacity: 0; z-index: 2;
}}
@supports (animation-timeline: view()) {{
  #{s}::after {{ animation: colonize-{s} linear both; animation-timeline: view(); animation-range: entry 0% cover 88%; }}
  @keyframes colonize-{s} {{ from {{ opacity: 0; transform: translateY(10%) scale(1.03); }} to {{ opacity: {coverage}; transform: none; }} }}
}}
@supports not (animation-timeline: view()) {{ #{s}::after {{ opacity: {coverage * 0.72:.2f}; }} }}
@media (prefers-reduced-motion: reduce) {{ #{s}::after {{ animation: none; opacity: {coverage * 0.6:.2f}; }} }}
"""


class CollisionType:
    """Collision typesetting: the headline overlaps a bruised ghost of itself."""

    name = "collision"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "angle": {"type": "float", "min": -9.0, "max": 9.0},
            "overlap": {"type": "float", "min": 0.1, "max": 0.6},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        angle = float(params.get("angle", -4.0))
        overlap = float(params.get("overlap", 0.3))
        return f"""
/* collision: {s} */
#{s} .headline {{ position: relative; transform: rotate({angle:.2f}deg); }}
#{s} .headline::before {{
  content: attr(data-text); position: absolute; left: {overlap:.2f}em; top: {overlap * 0.55:.2f}em;
  color: var(--pop); mix-blend-mode: difference; z-index: -1;
}}
"""


class TypeDecay:
    """The copy rots as it descends. Gated: illegibility must be earned."""

    name = "decay"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {"section": {"type": "str"}, "severity": {"type": "float", "min": 0.2, "max": 0.9}}

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        sev = float(params.get("severity", 0.5))
        return f"""
/* decay: {s} */
#{s} .body p:nth-last-child(-n+2) {{ opacity: {max(0.4, 1 - sev * 0.45):.2f}; letter-spacing: {sev * 0.06:.3f}em; }}
#{s} .body p:last-child {{ opacity: {max(0.28, 1 - sev * 0.6):.2f}; filter: blur({sev * 0.5:.2f}px); transform: skewX({-sev * 3:.1f}deg); }}
"""


class AgarCard:
    """Body rests on a tilted pale growth-medium slab — the resting surface."""

    name = "agar"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {"section": {"type": "str"}, "tilt": {"type": "float", "min": -2.5, "max": 2.5}}

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        tilt = float(params.get("tilt", -1.0))
        return f"""
/* agar: {s} */
#{s} .body {{
  background: {PALETTE["agar"]}; color: {PALETTE["substrate"]};
  padding: clamp(1.6rem, 4vw, 3.2rem); transform: rotate({tilt:.2f}deg);
  box-shadow: 0 0 0 1px {PALETTE["spore"]}66, 0 30px 70px -34px {PALETTE["viridian"]}88;
}}
#{s} .body a {{ color: {PALETTE["bruise"]}; }}
"""


# -- STRUCTURE -----------------------------------------------------------------

class Bleed:
    """The headline is too big for the page and runs off the edge."""

    name = "bleed"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "overflow": {"type": "float", "min": 0.1, "max": 0.6},  # fraction pushed off-edge
            "side": {"type": "str", "choices": ["left", "right"]},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        of = float(params.get("overflow", 0.3))
        side = params.get("side", "left")
        edge = "margin-left" if side == "left" else "margin-right"
        return f"""
/* bleed: {s} ({side}) — oversized headline pushed toward the edge (still wraps) */
#{s} .headline {{
  font-size: clamp(3rem, 13vw, 9.5rem); line-height: 0.92; letter-spacing: -0.03em;
  {edge}: -{of * 10:.0f}vw; color: var(--pop);
}}
@media (max-width: 720px) {{ #{s} .headline {{ {edge}: -3vw; font-size: clamp(2.4rem, 14vw, 5rem); }} }}
"""


class ScaleViolence:
    """A giant drop-word: the first letter of the body detonates."""

    name = "scale-violence"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "ratio": {"type": "float", "min": 1.4, "max": 4.5},  # dropcap scale
            "accent": {"type": "str", "choices": _ACCENTS},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        ratio = float(params.get("ratio", 2.4))
        return f"""
/* scale-violence: {s} */
#{s} .body > p:first-of-type::first-letter {{
  float: left; font-family: var(--display); font-weight: 800; line-height: 0.7;
  font-size: {ratio * 3.2:.1f}em; padding: 0.02em 0.12em 0 0; margin-top: 0.06em;
  color: var(--pop); -webkit-text-stroke: 2px var(--bg);
}}
#{s} .headline {{ font-size: clamp(2rem, {5 + ratio * 1.5:.0f}vw, {4 + ratio:.0f}rem); }}
"""


class BrokenColumn:
    """The body fractures into unstable columns with a rotated intrusion."""

    name = "broken-column"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "columns": {"type": "float", "min": 2.0, "max": 3.0},
            "jitter": {"type": "float", "min": 0.0, "max": 6.0},  # per-paragraph rotation
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        cols = int(round(float(params.get("columns", 2))))
        jit = float(params.get("jitter", 2.0))
        return f"""
/* broken-column: {s} */
#{s} .body {{ columns: {cols}; column-gap: clamp(1.2rem, 3vw, 2.6rem); column-rule: 2px solid var(--pop); }}
#{s} .body p {{ break-inside: avoid; }}
#{s} .body p:nth-child(3n+2) {{ transform: rotate({jit:.1f}deg); }}
#{s} .body p:nth-child(3n) {{ transform: rotate({-jit * 0.7:.1f}deg); }}
@media (max-width: 720px) {{ #{s} .body {{ columns: 1; }} #{s} .body p {{ transform: none; }} }}
"""


class Marginalia:
    """Dek and kicker rotate vertically into the margin, like field notes."""

    name = "marginalia"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {"section": {"type": "str"}, "side": {"type": "str", "choices": ["left", "right"]}}

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        side = params.get("side", "right")
        wm = "vertical-rl" if side == "right" else "vertical-lr"
        return f"""
/* marginalia: {s} ({side}) */
@media (min-width: 900px) {{
  #{s} .dek {{
    writing-mode: {wm}; position: absolute; {side}: clamp(0.5rem, 2vw, 2rem); top: 0;
    max-width: none; margin: 0; text-orientation: mixed; letter-spacing: 0.02em;
    border-{side}: 3px solid var(--pop); padding-{side}: 0.6rem;
  }}
  #{s} {{ position: relative; }}
}}
"""


_KIT = (
    ColonizationOverlay(), CollisionType(), TypeDecay(), AgarCard(),
    Bleed(), ScaleViolence(), BrokenColumn(), Marginalia(),
)


def build_library():
    """Register the kit into an ensemble PrimitiveLibrary."""
    from ensemble.design.primitive import PrimitiveLibrary

    lib = PrimitiveLibrary()
    for p in _KIT:
        lib.register(p)
    return lib


# Form-follows-opinion: the writer's declared stance picks the primitive that
# ENACTS it. This is the deterministic fallback; the Art Director model may
# override within the kit. Instance taste — ensemble's Composer just applies it.
def _mk(primitive: str, **params: Any):
    def factory(section: str) -> tuple[str, Mapping[str, Any]]:
        return primitive, {"section": section, **params}
    return factory


STANCE_MAP = {
    # despised → the type is attacked and shoved off the page
    "contempt": _mk("bleed", overflow=0.4, side="left"),
    # boring → the copy visibly rots
    "boredom": _mk("decay", severity=0.75),
    # sacred → rests clean on agar
    "reverence": _mk("agar", tilt=-1.2),
    # spreading → the signature colonization
    "fascination": _mk("colonization", coverage=0.78, base_frequency=0.02, accent="chartreuse"),
    # default → a giant detonating drop-word
    "neutral": _mk("scale-violence", ratio=2.6, accent="sulphur"),
}
