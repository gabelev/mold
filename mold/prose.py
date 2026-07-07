"""The content mirror: the discriminator's prose side.

Per the taste-critic spec, the same bar-keeper rejects prose AI-tells:
hedging, "isn't just X it's Y", rule-of-three, em-dash pivot, gentle
positivity. The Critic MUST be able to pan things — genuine, specific
negativity is the signature of real taste; vague praise is the tell.

Layer 1 (here): computable heuristics — deterministic, testable, free.
Layer 2 (ProseTellJudge): a model pass grounded in the same negative framing.
Pipeline use: each author's copy gets one regeneration with the named tells;
a second failure ships with the dissent logged (the zine must ship).
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from ensemble.providers.model import Message, ModelProvider
from ensemble.taste.judge import ScoreVector, Verdict

# (tell name, compiled pattern). Case-insensitive; tuned for zine copy, not code.
_TELLS: list[tuple[str, re.Pattern[str]]] = [
    ("isn't-just-pivot", re.compile(r"\b(?:isn'?t|not)\s+just\s+\w+[^.]{0,60}?\b(?:it'?s|but)\b", re.I)),
    ("hedging", re.compile(
        r"\b(?:perhaps|arguably|somewhat|it'?s worth noting|in many ways|"
        r"at the end of the day|one could say|to some extent)\b", re.I)),
    ("gentle-positivity", re.compile(
        r"\b(?:delightful|wonderful|a testament to|beautiful reminder|"
        r"truly special|resonates deeply|rich tapestry)\b", re.I)),
    ("stakes-inflation", re.compile(
        r"\b(?:in today'?s (?:fast-paced|ever-changing|digital)|"
        r"now more than ever|in an era of)\b", re.I)),
]

_TRIAD = re.compile(r"\b\w+,\s+\w+,\s+and\s+\w+\b")
_EMDASH = re.compile(r"—|--")


def audit_prose(text: str) -> list[str]:
    """Return the named tells found in a piece of copy (empty = clean)."""
    tells: list[str] = []
    for name, pattern in _TELLS:
        if pattern.search(text):
            tells.append(name)

    words = max(1, len(text.split()))
    # Em-dash pivot: fine as punctuation, a tell as a rhetorical crutch.
    if len(_EMDASH.findall(text)) / words > 0.02:
        tells.append("em-dash-pivot")
    # Rule of three: one triad is rhythm; repeated triads are a template.
    if len(_TRIAD.findall(text)) >= 3:
        tells.append("rule-of-three")
    return tells


PROSE_PROMPT = (
    "You are the taste-critic of MOLD reading COPY, grounded in a negative "
    "corpus of AI-generic prose: hedging, symmetrical pivots, vague warmth, "
    "praise without a specific claim. Judge ONLY whether this copy has a real "
    "stance — could you tell what the writer actually thinks, and would they "
    "be able to pan something? Reply exactly PASS or FAIL, then one short reason."
)


class ProseTellJudge:
    """Model-grounded stance check; heuristics ride along as hard anchors."""

    grounding = "negative corpus (AI-generic prose)"

    def __init__(self, model: ModelProvider) -> None:
        self.model = model

    def evaluate(self, candidate: Mapping[str, Any]) -> Verdict:
        text = candidate.get("text", "")
        tells = audit_prose(text)
        reply = self.model.complete([
            Message(role="system", content=PROSE_PROMPT),
            Message(role="user", content=text),
        ]).strip()
        model_ok = reply.upper().startswith("PASS")
        ok = model_ok and not tells
        rationale = reply[:150] + (f" | tells: {', '.join(tells)}" if tells else "")
        return Verdict(
            passed=ok,
            scores=ScoreVector(anchors={
                "stance": 1.0 if model_ok else 0.0,
                "no_tells": 1.0 if not tells else 0.0,
            }),
            rationale=rationale,
            grounding=self.grounding,
        )
