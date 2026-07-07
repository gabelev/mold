"""The Planning agent: reads the ledger cluster, names the theme, sets stories.

HARD CONSTRAINT (from the brief): the theme EMERGES from the densest ledger
cluster. The planner orchestrates and names — it does NOT invent a theme
top-down. Here that is enforced structurally: `perceive` precipitates the theme
from the ledger; `decide`/`execute` only name and frame what precipitated.
"""

from __future__ import annotations

from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception
from ensemble.ledger import Ledger, precipitate_theme
from mold.personas.base import messages

BASE_PROMPT = (
    "You are the Namer/Editor of MOLD, an autonomous zine about AI culture. "
    "You are the only top-down role, and even you do not invent the theme: you "
    "read the week's densest ledger cluster and give it a name, last. Name it "
    "with a single evocative word or short phrase — biological, wry, exact. "
    "Never explain the joke."
)


class PlanningAgent(Agent):
    """Precipitates the theme from the ledger and frames the issue."""

    def __init__(self, model, ledger: Ledger, **kw: Any) -> None:
        from ensemble.agent import Persona

        super().__init__(Persona(name="planner", base_prompt=BASE_PROMPT), model, **kw)
        self.ledger = ledger

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        fragments = list(self.ledger.read())
        cluster = precipitate_theme(fragments)  # densest cluster = emergent theme
        return Perception(data={"cluster": cluster, "fragment_count": len(fragments)})

    def decide(self, perception: Perception) -> Decision:
        cluster = perception.data["cluster"]
        if cluster is None:
            return Decision(data={"theme_seed": None})
        # Stories are seeded by the beat of each fragment in the winning cluster.
        stories = [
            {"beat": f.beat, "seed": f.content, "assigned_to": _role_for_beat(f.beat)}
            for f in cluster.fragments
        ]
        return Decision(data={"cluster_label": cluster.label, "density": cluster.density, "stories": stories})

    def execute(self, decision: Decision) -> Artifact:
        label = decision.data.get("cluster_label")
        if label is None:
            return Artifact(kind="planning", body="# No theme precipitated\n", metadata={"theme": None})
        # The model NAMES what precipitated (it does not choose the topic).
        name = _clean_title(self.model.complete(
            messages(
                self.persona.base_prompt,
                f"The densest cluster this week is about: {label!r}. Name the issue. "
                "Reply with the name only: 1-3 words, no markdown, no quotes, no explanation.",
            )
        ))
        stories = decision.data["stories"]
        body = _planning_md(name, label, decision.data["density"], stories)
        return Artifact(
            kind="planning",
            body=body,
            metadata={"theme": name, "cluster_label": label, "stories": stories},
        )


def _clean_title(raw: str) -> str:
    """A live model wraps names in markdown/quotes/preamble; the title must be
    plain text — it lands in <title>, filenames, and commit messages."""
    line = raw.strip().splitlines()[0] if raw.strip() else "UNTITLED"
    line = line.strip(" \t*_`\"'#:.!").strip()
    # "The issue is called: X" style preamble -> keep what follows the colon.
    if ":" in line and len(line.split(":", 1)[1].strip()) >= 3:
        tail = line.split(":", 1)[1].strip(" \t*_`\"'#:.!").strip()
        if tail and len(tail.split()) <= 4:
            line = tail
    words = line.split()
    return " ".join(words[:4]) if words else "UNTITLED"


def _role_for_beat(beat: str) -> str:
    return "the-critic" if beat.startswith("verdict") else "the-surveyor"


def _planning_md(name: str, label: str, density: float, stories: list) -> str:
    lines = [
        f"# Planning brief — Issue theme: {name}",
        "",
        f"*Theme precipitated from the densest ledger cluster (`{label}`, "
        f"density {density:.0%}). The Namer titled it; nobody chose it.*",
        "",
        "## Stories",
    ]
    for i, s in enumerate(stories, 1):
        lines.append(f"{i}. **[{s['assigned_to']}]** ({s['beat']}) — {s['seed']}")
    lines.append("")
    return "\n".join(lines)
