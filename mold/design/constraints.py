"""Per-issue constraint injection — Oblique Strategies for layout.

Each candidate composition gets a different constraint operating over the kit
("no collision grid this issue", "type-destruction only", ...). Constraints
force recombination beyond what taboo memory alone produces. Selection is
deterministic by issue number so a re-run of the same issue composes the same
candidates (and tests stay stable).
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from mold.design.primitives import STANCE_MAP, _mk

StanceMap = Mapping[str, Callable[[str], tuple[str, Mapping[str, Any]]]]

# Each constraint is a name + a stance-map override. None = the house map.
# Each pushes the whole issue toward a different structural register so no two
# consecutive weeks share a dominant move (rotated deterministically per issue).
CONSTRAINTS: dict[str, dict] = {
    "house": {},
    "off-the-page": {
        # everything bleeds — headlines run off both edges
        "contempt": _mk("bleed", overflow=0.5, side="left"),
        "fascination": _mk("bleed", overflow=0.35, side="right"),
        "neutral": _mk("bleed", overflow=0.3, side="left"),
    },
    "fractured": {
        # the copy itself breaks into unstable columns
        "fascination": _mk("broken-column", columns=3, jitter=4.0),
        "neutral": _mk("broken-column", columns=2, jitter=2.5),
        "reverence": _mk("broken-column", columns=2, jitter=1.0),
    },
    "full-bloom": {
        # colonization dominates; the issue is mostly organism
        "fascination": _mk("colonization", coverage=0.9, base_frequency=0.02, accent="chartreuse"),
        "neutral": _mk("colonization", coverage=0.55, base_frequency=0.03, accent="viridian"),
    },
    "giant-caps": {
        # scale violence everywhere: detonating drop-words
        "contempt": _mk("scale-violence", ratio=3.6, accent="bruise"),
        "neutral": _mk("scale-violence", ratio=2.8, accent="sulphur"),
        "fascination": _mk("scale-violence", ratio=3.2, accent="chartreuse"),
    },
    "field-notes": {
        # deks and labels rotate into the margins like lab annotations
        "reverence": _mk("marginalia", side="right"),
        "neutral": _mk("marginalia", side="left"),
        "boredom": _mk("decay", severity=0.85),
    },
}

_ORDER = list(CONSTRAINTS)


def pick_constraints(issue_id: str, k: int) -> list[str]:
    """k distinct constraints for this issue, rotating deterministically."""
    start = int(issue_id) if issue_id.isdigit() else 0
    return [_ORDER[(start + i) % len(_ORDER)] for i in range(k)]


def _jitter(params: Mapping[str, Any], variant: int) -> dict[str, Any]:
    """Bounded per-candidate parameter drift so variants differ in degree."""
    out = dict(params)
    _bump = {  # key: (delta-per-variant, lo, hi)
        "angle": (2.0, -9.0, 9.0), "coverage": (0.08, 0.2, 0.9),
        "severity": (0.1, 0.2, 0.9), "tilt": (0.5, -2.5, 2.5),
        "overflow": (0.08, 0.1, 0.6), "ratio": (0.35, 1.4, 4.5),
        "jitter": (0.9, 0.0, 6.0),
    }
    for key, (delta, lo, hi) in _bump.items():
        if key in out:
            out[key] = max(lo, min(hi, float(out[key]) + delta * variant))
    return out


def constrained_stance_map(constraint: str, variant: int = 0) -> StanceMap:
    """The house stance map with one constraint's overrides + variant jitter."""
    base = dict(STANCE_MAP)
    base.update(CONSTRAINTS.get(constraint, {}))

    def wrap(factory):
        def jittered(section: str):
            primitive, params = factory(section)
            return primitive, _jitter(params, variant)
        return jittered

    return {stance: wrap(f) for stance, f in base.items()}
