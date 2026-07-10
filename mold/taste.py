"""Mold's taste discriminator: the bar-keeper (Phase 1, description-based).

Implements the taste-critic spec on ensemble's harness: N candidate treatments
go in; safe ones are killed; regeneration is forced RISKIER, not more polished.

Heterogeneous grounding (load-bearing — same-lineage disagreement is fake):
  - TabooComplianceJudge  → grounded in the anti-repetition store
  - RiskFloorJudge        → grounded in the risk floor ("≥1 element a competent
                            designer would call wrong"; all-balanced = FAIL)
  - AntiTemplateJudge     → grounded in the NEGATIVE corpus (templated/
                            AI-generic design), model-judged on a structured
                            description of the composition

Phase 2 (per spec): judge rendered pixels via the vision pass, and anchor to
the real positive/negative image corpora. Description-based judging is the
warm-start, same as Experiment 001.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from ensemble.providers.model import Message, ModelProvider
from ensemble.taste.discriminator import Discriminator
from ensemble.taste.judge import ScoreVector, Verdict

# Params at or beyond these are "wrong on purpose" — the risk floor's currency.
_RISK_THRESHOLDS = {
    "collision": ("angle", lambda v: abs(float(v)) >= 4.0),
    "decay": ("severity", lambda v: float(v) >= 0.5),
    "colonization": ("coverage", lambda v: float(v) >= 0.6),
    "bleed": ("overflow", lambda v: float(v) >= 0.3),
    "scale-violence": ("ratio", lambda v: float(v) >= 2.4),
    "broken-column": ("jitter", lambda v: float(v) >= 2.5),
}

TASTE_PROMPT = (
    "You are the taste-critic of MOLD — the bar-keeper, grounded in a negative "
    "corpus of templated Behance/Canva/corporate-deck/AI-generic design. Your "
    "only job is contempt for the competent-generic. Given a structured "
    "description of a composed layout, judge ONLY whether it reads as templated "
    "or AI-generic. Reply with exactly PASS (it escapes the negative corpus) or "
    "FAIL (it smells like a template), then one short reason."
)


class TabooComplianceJudge:
    """Zero reuse of last cycle's moves. Exact-signature check."""

    grounding = "taboo memory (anti-repetition store)"

    def __init__(self, forbidden: Iterable[str]) -> None:
        self.forbidden = frozenset(forbidden)

    def evaluate(self, candidate: Mapping[str, Any]) -> Verdict:
        reused = sorted(set(candidate.get("moves", [])) & self.forbidden)
        ok = not reused
        return Verdict(
            passed=ok,
            scores=ScoreVector(anchors={"taboo_compliance": 1.0 if ok else 0.0}),
            rationale="no reuse" if ok else f"reused moves: {', '.join(reused)}",
            grounding=self.grounding,
        )


class RiskFloorJudge:
    """≥1 element a competent designer would call wrong, or the issue fails.

    The inverse of a QA gate: this removes the ABSENCE of mistakes.
    """

    grounding = "risk floor (the required wrongness)"

    def evaluate(self, candidate: Mapping[str, Any]) -> Verdict:
        risky = []
        for a in candidate.get("assignments", []):
            rule = _RISK_THRESHOLDS.get(a.get("primitive", ""))
            if rule:
                key, test = rule
                if key in a.get("params", {}) and test(a["params"][key]):
                    risky.append(f"{a['primitive']}({a['section']})")
        ok = bool(risky)
        return Verdict(
            passed=ok,
            scores=ScoreVector(anchors={"risk_floor": 1.0 if ok else 0.0}),
            rationale=(
                f"wrong on purpose: {', '.join(risky)}" if ok
                else "everything is balanced and readable — that is a failure"
            ),
            grounding=self.grounding,
        )


class AntiTemplateJudge:
    """Distance from the negative corpus, judged by a model on a structured
    description. PASS/FAIL protocol keeps it un-collapsible to a scalar."""

    grounding = "negative corpus (templated/AI-generic design)"

    def __init__(self, model: ModelProvider) -> None:
        self.model = model

    @staticmethod
    def _describe(candidate: Mapping[str, Any]) -> str:
        lines = [f"constraint this issue: {candidate.get('constraint', 'house')}"]
        for a in candidate.get("assignments", []):
            params = ", ".join(f"{k}={v}" for k, v in a.get("params", {}).items() if k != "section")
            lines.append(
                f"- section {a['section']}: stance '{a['stance']}' enacted by "
                f"primitive '{a['primitive']}' ({params})"
            )
        return "\n".join(lines)

    def evaluate(self, candidate: Mapping[str, Any]) -> Verdict:
        reply = self.model.complete([
            Message(role="system", content=TASTE_PROMPT),
            Message(role="user", content=self._describe(candidate)),
        ]).strip()
        ok = reply.upper().startswith("PASS")
        return Verdict(
            passed=ok,
            scores=ScoreVector(anchors={"anti_template": 1.0 if ok else 0.0}),
            rationale=reply[:200],
            grounding=self.grounding,
        )


def build_discriminator(model: ModelProvider, forbidden: Iterable[str]) -> Discriminator:
    """The pass-all panel. Anchors stay separate; no scalar to climb."""
    return Discriminator([
        TabooComplianceJudge(forbidden),
        RiskFloorJudge(),
        AntiTemplateJudge(model),
    ])


def candidate_view(artifact) -> dict[str, Any]:
    """Project a design Artifact into the mapping the judges consume."""
    m = artifact.metadata
    return {
        "moves": m.get("moves", []),
        "assignments": m.get("assignments", []),
        "constraint": m.get("constraint", "house"),
    }
