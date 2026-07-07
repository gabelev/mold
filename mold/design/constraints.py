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
CONSTRAINTS: dict[str, dict] = {
    "house": {},
    "no-collision": {
        # contempt must find another weapon: rot instead of impact
        "contempt": _mk("decay", severity=0.85),
    },
    "no-agar": {
        # nothing gets to rest; even reverence grows something
        "reverence": _mk("colonization", coverage=0.3, accent="sulphur"),
        "neutral": _mk("colonization", coverage=0.25, accent="viridian"),
    },
    "full-bloom": {
        # colonization dominates; the issue is mostly organism
        "fascination": _mk("colonization", coverage=0.85, accent="chartreuse"),
        "neutral": _mk("colonization", coverage=0.5, accent="viridian"),
    },
    "type-violence": {
        # everything is done with type alone
        "fascination": _mk("collision", angle=7.5, overlap=0.2),
        "neutral": _mk("decay", severity=0.35),
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
    if "angle" in out:
        out["angle"] = max(-8.0, min(8.0, float(out["angle"]) + 2.0 * variant))
    if "coverage" in out:
        out["coverage"] = max(0.2, min(0.85, float(out["coverage"]) + 0.08 * variant))
    if "severity" in out:
        out["severity"] = max(0.2, min(0.9, float(out["severity"]) + 0.1 * variant))
    if "tilt" in out:
        out["tilt"] = max(-1.5, min(1.5, float(out["tilt"]) + 0.4 * variant))
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
