"""The Critic: a verdict on a single work. Deep, opinionated, one thing.

Personality = what it rates and how hard it swings. The Critic MUST be able to
pan things — genuine, specific negativity is the signature of real taste.
Copyright wall: describe, quote briefly, link — never reproduce.
"""

from __future__ import annotations

from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona
from mold.personas.base import messages

BASE_PROMPT = (
    "You are The Critic of MOLD. You deliver a verdict on ONE work — an AI track, "
    "a generated clip, a model's behavior. Deep, opinionated, specific. You are "
    "allowed, even obligated, to pan things: vague praise is a tell. Describe and "
    "quote briefly and link; never reproduce the work. Write with a stance, not a "
    "summary. No hedging, no 'isn't just X it's Y', no rule-of-three, no gentle "
    "positivity."
)


class CriticAgent(Agent):
    """Writes one review, driven by an assigned story seed from planning."""

    def __init__(self, model, **kw: Any) -> None:
        super().__init__(Persona(name="the-critic", base_prompt=BASE_PROMPT), model, **kw)

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        planning = context.get("planning")
        theme = planning.metadata.get("theme") if planning else None
        # Take the first story assigned to the critic.
        stories = planning.metadata.get("stories", []) if planning else []
        mine = next((s for s in stories if s["assigned_to"] == "the-critic"), None)
        return Perception(data={"theme": theme, "story": mine})

    def decide(self, perception: Perception) -> Decision:
        return Decision(data=perception.data)

    def execute(self, decision: Decision) -> Artifact:
        theme = decision.data.get("theme") or "untitled"
        story = decision.data.get("story")
        seed = story["seed"] if story else "the week's subject"
        stance = "contempt"  # drives form-follows-opinion downstream in design
        body = self.model.complete(
            messages(
                self.persona.base_prompt,
                f"Issue theme: {theme}. Write a short verdict grounded in this "
                f"ledger seed (describe/quote/link, never reproduce): {seed}",
            )
        )
        return Artifact(
            kind="review",
            body=body,
            metadata={"theme": theme, "stance": stance, "byline": "The Critic"},
        )
