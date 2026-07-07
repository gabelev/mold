"""The Editor/Namer: the final edit, and the only top-down role.

Per the operating brief the Namer reads the finished copy and titles the issue
LAST — the name responds to what the masthead actually wrote, not to a keyword.
The Editor also writes each piece's display headline + dek and a short
editor's note, but does NOT rewrite the writers: their edges stay.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona
from ensemble.providers.model import Message

BASE_PROMPT = (
    "You are the Editor of MOLD — and its Namer, the only top-down role. You "
    "read the masthead's finished pieces and do the final edit: title the "
    "issue (responding to what was actually written — you name what "
    "precipitated, never invent a topic), give each piece a display headline "
    "and a one-line dek, and write a 2-3 sentence editor's note. You do not "
    "smooth the writers' edges and you never rewrite their copy."
)

_EDIT_PROMPT = """The ledger's densest cluster this week was {label!r}. The masthead wrote:

{pieces}

Return ONLY a JSON object, no markdown fences, exactly this shape:
{{"title": "<issue name, 1-3 plain words, no punctuation flourishes>",
 "editors_note": "<2-3 sentences, your voice, no hedging>",
 "pieces": [{{"headline": "<display headline, punchy, 2-8 words>", "dek": "<one-line dek>"}}, ...]}}

The "pieces" array must have exactly {n} entries, in the order given."""


class EditorAgent(Agent):
    """Final edit: names the issue last, heads the pieces, writes the note."""

    def __init__(self, model, **kw: Any) -> None:
        super().__init__(Persona(name="editor", base_prompt=BASE_PROMPT), model, **kw)

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        planning = context.get("planning")
        authors: Sequence[Artifact] = context.get("authors", [])
        return Perception(data={
            "planning": planning,
            "authors": list(authors),
            "issue_id": context.get("issue_id", "000"),
        })

    def decide(self, perception: Perception) -> Decision:
        return Decision(data=perception.data)

    def execute(self, decision: Decision) -> Artifact:
        planning: Artifact = decision.data["planning"]
        authors: list[Artifact] = decision.data["authors"]
        issue_id = decision.data["issue_id"]
        label = planning.metadata.get("cluster_label") or "untitled"
        working_title = planning.metadata.get("theme") or "UNTITLED"

        edit = self._edit_pass(label, authors) or {}
        theme = _plain_title(edit.get("title")) or working_title
        note = (edit.get("editors_note") or "").strip()
        heads = edit.get("pieces") or []

        # Attach display heads to the author artifacts so design renders them.
        for i, art in enumerate(authors):
            head = heads[i] if i < len(heads) and isinstance(heads[i], dict) else {}
            art.metadata = dict(art.metadata)
            art.metadata["headline"] = _plain_title(head.get("headline")) or art.metadata.get("byline", "Untitled")
            art.metadata["dek"] = (head.get("dek") or "").strip()

        parts = [
            f"# MOLD — Issue {issue_id}: {theme}",
            "",
            "*An autonomous zine about AI culture. Theme precipitated from the "
            "ledger; the Namer titled it last; nobody chose it.*",
            "",
        ]
        if note:
            parts += [f"> {note}", ""]
        parts += ["---", ""]
        for art in authors:
            byline = art.metadata.get("byline", "Staff")
            parts.append(f"## {art.metadata['headline']}")
            if art.metadata.get("dek"):
                parts.append(f"*{art.metadata['dek']}*")
            parts.append(f"**{byline}**")
            parts.append("")
            parts.append(art.body.strip())
            parts += ["", "---", ""]

        return Artifact(
            kind="issue",
            body="\n".join(parts),
            metadata={
                "theme": theme,
                "issue_id": issue_id,
                "editors_note": note,
                "planning_body": planning.body,
            },
        )

    def _edit_pass(self, label: str, authors: list[Artifact]) -> dict | None:
        pieces = "\n\n".join(
            f"--- piece {i} (byline: {a.metadata.get('byline', 'Staff')}, "
            f"stance: {a.metadata.get('stance', 'neutral')}) ---\n{a.body.strip()}"
            for i, a in enumerate(authors)
        )
        prompt = _EDIT_PROMPT.format(label=label, pieces=pieces, n=len(authors))
        for attempt in range(2):  # one retry on malformed JSON, then degrade
            reply = self.model.complete([
                Message(role="system", content=self.persona.base_prompt),
                Message(role="user", content=prompt),
            ])
            parsed = _parse_json(reply)
            if parsed is not None:
                return parsed
            prompt += "\n\nYour last reply was not valid JSON. Return ONLY the JSON object."
        return None


def _parse_json(raw: str) -> dict | None:
    """Model JSON arrives bare or fenced; anything else degrades gracefully."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        out = json.loads(text[start:end + 1])
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


def _plain_title(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    line = raw.strip().splitlines()[0].strip(" \t*_`\"'#:.!")
    words = line.split()
    return " ".join(words[:6]) if words else None
