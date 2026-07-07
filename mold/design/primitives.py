"""The starter primitive kit (Phase 0/1 of the design-production engine).

Four hand-authored, parametrized CSS/SVG primitives implementing ensemble's
`Primitive` protocol. Each renders a CSS fragment (and shares the SVG filter
defs emitted once by the page shell). Type stays in the DOM always; nothing
here produces raster.

Kit (from the design spec's menu):
  colonization  — scroll-linked feTurbulence bloom overlay (the signature)
  collision     — collision typesetting: overlapped, rotated, blend-mode type
  agar          — the calm growth-medium card (the reader's resting surface)
  decay         — progressive type destruction: opacity/letter-spacing rot

Every primitive takes a `section` param (the CSS scope) plus its own knobs,
each bounded so the composer parametrizes within limits.
"""

from __future__ import annotations

from typing import Any, Mapping

from mold.design.palette import PALETTE


class ColonizationOverlay:
    """The signature: mold blooms over the section as you scroll into it."""

    name = "colonization"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "coverage": {"type": "float", "min": 0.2, "max": 0.85},
            "base_frequency": {"type": "float", "min": 0.008, "max": 0.06},
            "accent": {"type": "str", "choices": ["viridian", "chartreuse", "sulphur", "bruise"]},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        coverage = float(params.get("coverage", 0.5))
        accent = PALETTE[params.get("accent", "viridian")]
        return f"""
/* colonization: {s} */
#{s} {{ position: relative; isolation: isolate; }}
#{s}::after {{
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(ellipse 120% 60% at 10% 110%, {accent}cc, transparent 60%),
    radial-gradient(ellipse 70% 40% at 90% 100%, {accent}88, transparent 70%);
  filter: url(#bloom);
  mix-blend-mode: screen;
  opacity: 0;
  z-index: 1;
}}
@supports (animation-timeline: view()) {{
  #{s}::after {{
    animation: colonize-{s} linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 90%;
  }}
  @keyframes colonize-{s} {{
    from {{ opacity: 0; transform: translateY(12%) scale(1.02); }}
    to   {{ opacity: {coverage}; transform: translateY(0) scale(1); }}
  }}
}}
@supports not (animation-timeline: view()) {{
  #{s}::after {{ opacity: {coverage * 0.7}; }}
}}
@media (prefers-reduced-motion: reduce) {{
  #{s}::after {{ animation: none; opacity: {coverage * 0.6}; }}
}}
"""


class CollisionType:
    """Collision typesetting: the headline overlaps itself, rotated, blended."""

    name = "collision"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "angle": {"type": "float", "min": -8.0, "max": 8.0},
            "overlap": {"type": "float", "min": 0.1, "max": 0.5},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        angle = float(params.get("angle", -3.0))
        overlap = float(params.get("overlap", 0.25))
        return f"""
/* collision: {s} */
#{s} .headline {{
  position: relative;
  transform: rotate({angle}deg);
  letter-spacing: -0.04em;
  line-height: 0.9;
}}
#{s} .headline::before {{
  content: attr(data-text);
  position: absolute;
  left: {overlap}em; top: {overlap * 0.6}em;
  color: {PALETTE["bruise"]};
  mix-blend-mode: difference;
  z-index: -1;
}}
"""


class AgarCard:
    """The calm resting surface: body copy sits on pale agar."""

    name = "agar"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "tilt": {"type": "float", "min": -1.5, "max": 1.5},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        tilt = float(params.get("tilt", 0.0))
        return f"""
/* agar: {s} */
#{s} .body {{
  background: {PALETTE["agar"]};
  color: {PALETTE["substrate"]};
  padding: clamp(1.5rem, 4vw, 3rem);
  max-width: 42rem;
  transform: rotate({tilt}deg);
  box-shadow: 0 0 0 1px {PALETTE["spore"]}55, 0 24px 60px -30px {PALETTE["viridian"]}66;
}}
"""


class TypeDecay:
    """Progressive type destruction: the copy rots as it goes.

    Gated per the spec: illegibility must be justified by content stance —
    the composer only assigns this to pieces whose stance earns it.
    """

    name = "decay"

    @property
    def params_schema(self) -> Mapping[str, Any]:
        return {
            "section": {"type": "str"},
            "severity": {"type": "float", "min": 0.2, "max": 0.9},
        }

    def render(self, params: Mapping[str, Any]) -> str:
        s = params["section"]
        severity = float(params.get("severity", 0.5))
        return f"""
/* decay: {s} */
#{s} .body p:nth-child(n+3) {{
  opacity: {max(0.35, 1 - severity * 0.5)};
  letter-spacing: {severity * 0.12:.3f}em;
}}
#{s} .body p:last-child {{
  opacity: {max(0.25, 1 - severity * 0.7)};
  filter: blur({severity * 0.6:.2f}px);
}}
"""


def build_library():
    """Register the starter kit into an ensemble PrimitiveLibrary."""
    from ensemble.design.primitive import PrimitiveLibrary

    lib = PrimitiveLibrary()
    for p in (ColonizationOverlay(), CollisionType(), AgarCard(), TypeDecay()):
        lib.register(p)
    return lib


# Form-follows-opinion: the writer's declared stance picks the primitive that
# ENACTS it. This mapping is Mold's taste; ensemble's Composer just applies it.
def _mk(primitive: str, **params: Any):
    def factory(section: str) -> tuple[str, Mapping[str, Any]]:
        return primitive, {"section": section, **params}
    return factory


STANCE_MAP = {
    # a despised piece gets its type attacked
    "contempt": _mk("collision", angle=-6.0, overlap=0.4),
    # a boring subject earns decay (the reader watches it rot)
    "boredom": _mk("decay", severity=0.7),
    # something sacred rests on clean agar
    "reverence": _mk("agar", tilt=0.0),
    # something spreading gets the signature colonization
    "fascination": _mk("colonization", coverage=0.7, accent="chartreuse"),
    # default register
    "neutral": _mk("agar", tilt=-0.8),
}
