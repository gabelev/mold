"""The Critic: a verdict on a single work. Deep, opinionated, one thing.

Personality = what it rates and how hard it swings. The Critic MUST be able to
pan things — genuine, specific negativity is the signature of real taste.
Copyright wall: describe, quote briefly, link — never reproduce.
"""

from __future__ import annotations

from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona
from mold.personas.base import PROSE_RULES, evidence_block, messages, strip_scaffolding

BASE_PROMPT = (
    "You are The Critic of MOLD. You deliver a verdict on ONE work — an AI track, "
    "a generated clip, a model's behavior. Deep, opinionated, specific. You are "
    "allowed, even obligated, to pan things: vague praise is a tell. Describe and "
    "quote briefly and link; never reproduce the work. Write with a stance, not a "
    "summary. No hedging, no 'isn't just X it's Y', no rule-of-three, no gentle "
    "positivity.\n"
    "VOICE (yours, non-negotiable): sharp, cold, verdict-first. Short declarative "
    "sentences. Open ON the verdict, never build to it. Zero warmth. You judge "
    "one thing and you name it in the first sentence."
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
        return Perception(data={
            "theme": theme,
            "story": mine,
            "evidence": list(context.get("evidence", [])),
            "revision_note": context.get("revision_note"),
        })

    def decide(self, perception: Perception) -> Decision:
        return Decision(data=perception.data)

    def execute(self, decision: Decision) -> Artifact:
        theme = decision.data.get("theme") or "untitled"
        story = decision.data.get("story")
        seed = story["seed"] if story else "the week's subject"
        stance = "contempt"  # drives form-follows-opinion downstream in design
        task = (
            f"Issue theme: {theme}. The ledger seed below is your LENS — a way "
            f"of seeing — never your subject: {seed}\n\n"
            f"{evidence_block(decision.data.get('evidence', []))}\n"
            "Your verdict is on ONE real, named work from the evidence above. "
            "Name it in the first sentence. Use the CURRENT facts (numbers, "
            "dates) the evidence gives — no other facts exist. Cite at least "
            "one source as a markdown link. Describe and quote briefly; never "
            "reproduce lyrics or audio. Unsourced pieces are rejected."
            + PROSE_RULES
        )
        if decision.data.get("revision_note"):
            task += (
                f"\n\nREVISION — your previous draft failed the taste gate: "
                f"{decision.data['revision_note']}. Rewrite with a harder, more "
                f"specific stance; kill those tells."
            )
        body = strip_scaffolding(self.model.complete(messages(self.persona.base_prompt, task)))
        return Artifact(
            kind="review",
            body=body,
            metadata={"theme": theme, "stance": stance, "byline": "The Critic"},
        )
