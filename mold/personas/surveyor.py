"""The Culture writer / trend surveyor: reads the FIELD, not one work.

This is the prose beat only. The listening apparatus (MERT/CLAP over Suno
audio, the ledger engine) is a separate build per the surveyor spec; until it
lands, this voice writes from the field-beat fragments already in the ledger —
which is honest: those fragments ARE its published observations.

Copyright wall: describe, quote briefly, link — never reproduce.
"""

from __future__ import annotations

from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona
from mold.personas.base import PROSE_RULES, messages, strip_scaffolding

BASE_PROMPT = (
    "You are the Culture writer of MOLD — the trend surveyor. You read the "
    "FIELD of AI-made culture, not one work: what is moving on Suno and its "
    "neighbors, which sounds are spreading, which micro-scene precipitated this "
    "week. You listen; your evidence is the audio itself, not the charts. "
    "Interpret significance. Describe and link; never reproduce. Write with "
    "curiosity sharpened into a claim, no hedging, no survey-of-everything — "
    "one trend, argued."
)


class SurveyorAgent(Agent):
    """Writes one field survey from planning's surveyor-assigned story seed."""

    def __init__(self, model, **kw: Any) -> None:
        super().__init__(Persona(name="the-surveyor", base_prompt=BASE_PROMPT), model, **kw)

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        planning = context.get("planning")
        stories = planning.metadata.get("stories", []) if planning else []
        mine = next((s for s in stories if s["assigned_to"] == "the-surveyor"), None)
        theme = planning.metadata.get("theme") if planning else None
        return Perception(data={
            "theme": theme,
            "story": mine,
            "revision_note": context.get("revision_note"),
        })

    def decide(self, perception: Perception) -> Decision:
        return Decision(data=perception.data)

    def execute(self, decision: Decision) -> Artifact:
        theme = decision.data.get("theme") or "untitled"
        story = decision.data.get("story")
        seed = story["seed"] if story else "the week's field"
        task = (
            f"Issue theme: {theme}. Write a short field survey grounded in "
            f"this ledger observation (describe/link, never reproduce): {seed}\n\n"
            "GROUNDING: write only from what the observation actually contains. "
            "Do not invent named scenes, tracks, artists, platforms' specifics, "
            "or statistics that are not in it. Interpret and argue from the "
            "observation itself; the listening apparatus will supply concrete "
            "subjects soon. Never fabricate a link; cite one only if the "
            "observation carries it."
            + PROSE_RULES
        )
        if decision.data.get("revision_note"):
            task += (
                f"\n\nREVISION — your previous draft failed the taste gate: "
                f"{decision.data['revision_note']}. Rewrite with a harder, more "
                f"specific claim; kill those tells."
            )
        body = strip_scaffolding(self.model.complete(messages(self.persona.base_prompt, task)))
        return Artifact(
            kind="survey",
            body=body,
            metadata={"theme": theme, "stance": "fascination", "byline": "The Culture Writer"},
        )
