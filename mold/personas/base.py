"""Shared helpers for Mold personas. Instance code — not part of ensemble."""

from __future__ import annotations

from typing import Sequence

from ensemble.providers.model import Message


def messages(base_prompt: str, task: str) -> Sequence[Message]:
    """Build a minimal system+user message pair from a persona's base prompt."""
    return [
        Message(role="system", content=base_prompt),
        Message(role="user", content=task),
    ]


def evidence_block(evidence) -> str:
    """Render PERCEIVE's deep-verify output for an author prompt."""
    if not evidence:
        return "EVIDENCE: none returned — you cannot write; say so in one line."
    lines = ["EVIDENCE (current, dated, sourced — these facts and no others):"]
    for e in evidence:
        lines.append(f"- {e.title} (published {e.published}) {e.url}\n  {e.summary}")
    return "\n".join(lines)


PROSE_RULES = (
    "\n\nFORM: plain prose paragraphs separated by blank lines. No markdown "
    "headings, no bold titles, no bullet lists — the Editor writes your "
    "headline. Cite a link as [anchor text](https://...) only."
)


def strip_scaffolding(body: str) -> str:
    """Remove self-supplied titles/headings a model prepends despite the rules.

    Live models routinely open with '# Verdict: X' or a bold-only title line;
    those render as literal markdown in the DOM. Drop heading-shaped lines in
    the first few lines; leave everything else untouched.
    """
    lines = body.strip().splitlines()
    out: list[str] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if i < 4 and s and (
            s.startswith("#")
            or (s.startswith("**") and s.endswith("**") and len(s) < 90)
            or (s.startswith("*") and s.endswith("*") and not s.startswith("**") and len(s) < 90)
        ):
            continue
        out.append(line)
    return "\n".join(out).strip()
