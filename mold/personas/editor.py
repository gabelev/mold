"""The Editor/Namer: assembles the authors' copy into a titled issue.

For the vertical slice the Editor stitches the planning brief + the authors'
pieces into one issue Markdown document, carrying the precipitated theme name as
the masthead. (The full masthead also runs the Namer's titling and the final
edit; the slice keeps it minimal.)
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona

BASE_PROMPT = (
    "You are the Editor of MOLD. You assemble the masthead's pieces into a single "
    "issue, preserving each writer's stance. You do not smooth their edges."
)


class EditorAgent(Agent):
    """Assembles a final issue document from planning + author artifacts."""

    def __init__(self, model, **kw: Any) -> None:
        super().__init__(Persona(name="editor", base_prompt=BASE_PROMPT), model, **kw)

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        planning = context.get("planning")
        authors: Sequence[Artifact] = context.get("authors", [])
        return Perception(data={"planning": planning, "authors": list(authors)})

    def decide(self, perception: Perception) -> Decision:
        return Decision(data=perception.data)

    def execute(self, decision: Decision) -> Artifact:
        planning: Artifact = decision.data["planning"]
        authors: list[Artifact] = decision.data["authors"]
        theme = planning.metadata.get("theme") or "UNTITLED"
        issue_id = "000"

        parts = [
            f"# MOLD — Issue {issue_id}: {theme}",
            "",
            "*An autonomous zine about AI culture. Theme precipitated from the "
            "ledger; nobody chose it.*",
            "",
            "---",
            "",
        ]
        for art in authors:
            byline = art.metadata.get("byline", "Staff")
            parts.append(f"## {byline}")
            parts.append("")
            parts.append(art.body.strip())
            parts.append("")
            parts.append("---")
            parts.append("")

        return Artifact(
            kind="issue",
            body="\n".join(parts),
            metadata={"theme": theme, "issue_id": issue_id, "planning_body": planning.body},
        )
