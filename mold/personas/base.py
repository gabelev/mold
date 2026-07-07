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
