"""Voice-differentiation gate: reject same-register personas.

Issue 000's two authors collapsed into one indistinguishable dense-essayist
voice. The content mirror catches sentence-level tells; this gate catches
cross-piece register collapse: strip the bylines — can you still tell who
wrote which? If not, the later piece regenerates with differentiation notes.
"""

from __future__ import annotations

from typing import Sequence

from ensemble.agent import Artifact
from ensemble.providers.model import Message, ModelProvider

# The register contract, per persona. Also consumed by the personas' prompts.
VOICES = {
    "The Critic": (
        "sharp, cold, verdict-first. Short declarative sentences. Opens ON the "
        "verdict, never builds to it. Zero warmth; contempt is allowed to show. "
        "Judges ONE thing."
    ),
    "The Culture Writer": (
        "wide, warm, field-level. Longer arcs, reported texture, moves through "
        "scenes and actors. Curious before judgmental; connects three dots the "
        "reader hadn't linked. Reads a FIELD, not a work."
    ),
    "The Editor": (
        "meta and framing. Speaks about the issue, not the subjects; brief, "
        "plain, retrospective. Notices what grew; never performs criticism."
    ),
}

_GATE_PROMPT = """You are the voice-differentiation gate of MOLD. Two pieces follow, bylines stripped.

House registers:
- Voice A should be: {voice_a}
- Voice B should be: {voice_b}

PIECE 1:
{piece_1}

PIECE 2:
{piece_2}

Blind test: do these read as two DIFFERENT writers in their assigned registers,
or as one writer twice? Reply exactly PASS or FAIL, then one sentence. FAIL if
the registers are swappable — same rhythm, same rhetorical moves, same
aphoristic cadence — even if the topics differ."""


def check_voices(model: ModelProvider, pieces: Sequence[Artifact]) -> tuple[bool, str]:
    """True = distinguishable blind. Judges the first two pieces (the masthead
    pair); expand to pairwise when the masthead grows."""
    if len(pieces) < 2:
        return True, "single voice"
    a, b = pieces[0], pieces[1]
    reply = model.complete([
        Message(role="system", content="You judge whether two texts are by distinguishable voices."),
        Message(role="user", content=_GATE_PROMPT.format(
            voice_a=VOICES.get(a.metadata.get("byline", ""), "distinct"),
            voice_b=VOICES.get(b.metadata.get("byline", ""), "distinct"),
            piece_1=a.body.strip()[:3000],
            piece_2=b.body.strip()[:3000],
        )),
    ]).strip()
    return reply.upper().startswith("PASS"), reply[:200]
