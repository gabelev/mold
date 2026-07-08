"""The groundedness gate: unsourced = rejected.

Computable, per the spec: every piece must carry >=1 named work FROM ITS
EVIDENCE, >=1 outbound https URL, and its evidence must be in-window (the
recency contract already enforced upstream by ensemble.perceive — evidence
that reaches an author is in-window by construction, so the gate checks the
piece actually USED it).

A piece that fails gets ONE regeneration with the failure named; a second
failure aborts the run. A missed week beats an ungrounded issue.
"""

from __future__ import annotations

import re
from typing import Sequence

from ensemble.agent import Artifact
from ensemble.perceive import Evidence

_URL = re.compile(r"https://[^\s)\"'>]+")


class GroundednessFailed(RuntimeError):
    """A piece could not be grounded after regeneration; nothing ships."""


def _title_tokens(title: str) -> list[str]:
    """Distinctive tokens of a work's name (len>=4, not generic)."""
    generic = {"song", "track", "trend", "tiktok", "music", "video", "the", "and"}
    return [t for t in re.findall(r"[A-Za-z][A-Za-z']{3,}", title) if t.lower() not in generic]


def audit_groundedness(body: str, evidence: Sequence[Evidence]) -> list[str]:
    """Return failures (empty = grounded)."""
    failures: list[str] = []
    if not evidence:
        failures.append("no evidence attached — PERCEIVE returned nothing for this piece")
        return failures

    urls_in_body = set(_URL.findall(body))
    if not urls_in_body:
        failures.append("zero outbound links — cite the source you actually looked at")

    named = False
    for e in evidence:
        tokens = _title_tokens(e.title)
        if tokens and any(t in body for t in tokens):
            named = True
            break
        if e.url in urls_in_body:
            named = True
            break
    if not named:
        failures.append(
            "no named work from the evidence — the piece must be ABOUT a real artifact "
            f"(evidence offered: {', '.join(e.title for e in evidence[:4])})"
        )
    return failures


def assert_grounded(artifact: Artifact, evidence: Sequence[Evidence]) -> list[str]:
    return audit_groundedness(artifact.body, evidence)
