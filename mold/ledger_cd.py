"""Chaos-Dimension ledger adapter (Mold's binding of ensemble's Ledger).

Mold's stigmergic ledger lives in the `mold` workstream of Chaos Dimension:
fragments accrete daily, tagged by beat, and the densest cluster at deadline
becomes the theme.

This adapter lives in the INSTANCE, not in ensemble — per the boundary rule, the
CD binding graduates to `ensemble.adapters` only if a second instance needs it.

STATUS: stub. `CDLedger` implements ensemble's `Ledger` protocol but currently
delegates to an in-memory store seeded with canned fragments so the vertical
slice runs offline. Wiring the real CD MCP/API read+append is a TODO; the
interface it must satisfy is already fixed by `ensemble.ledger.Ledger`.
"""

from __future__ import annotations

from typing import Sequence

from ensemble.ledger import Fragment, InMemoryLedger


# Mold's two beats (instance-defined; ensemble knows nothing about them):
BEAT_VERDICT = "verdict-on-one-thing"        # the Critic
BEAT_FIELD = "the-field-is-moving-this-way"  # the Culture writer / surveyor


# Canned fragments echoing the real ledger cluster behind Issue 000 ("CULTURE" —
# culture-as-petri-dish / contamination / growth). Used only until the live CD
# read is wired.
_SEED: tuple[Fragment, ...] = (
    Fragment(
        id="frag-000",
        content="'Culture' is the same word for a petri dish and a civilization. "
        "Everything worth reviewing is something growing on a substrate it did not "
        "ask for — a scene, a genre, a mold. Same verb.",
        beat=BEAT_VERDICT,
        author="the-critic",
        created_at="2026-07-01T16:18:57Z",
        tags=("culture", "growth", "contamination"),
    ),
    Fragment(
        id="frag-001",
        content="No such thing as contamination, only unwelcome success. "
        "Contamination is just growth you did not authorize; reframe every ruined "
        "thing as a successful colonization by another culture's standards.",
        beat=BEAT_VERDICT,
        author="the-critic",
        created_at="2026-07-01T16:19:02Z",
        tags=("contamination", "culture", "colonization"),
    ),
    Fragment(
        id="frag-002",
        content="The field is moving toward washed-out, over-cultured AI vocal "
        "textures — a spreading sound, thriving in conditions no one curated. The "
        "culture is growing faster than anyone is tending it.",
        beat=BEAT_FIELD,
        author="the-surveyor",
        created_at="2026-07-01T18:02:00Z",
        tags=("culture", "growth", "suno"),
    ),
    Fragment(
        id="frag-003",
        content="A micro-scene precipitates weekly in the AI-music field, then is "
        "colonized by the next. Culture as substrate: what one week calls decay the "
        "next calls a genre.",
        beat=BEAT_FIELD,
        author="the-surveyor",
        created_at="2026-07-02T09:14:00Z",
        tags=("culture", "colonization", "scene"),
    ),
)


class CDLedger:
    """Ledger backed (for now) by a seeded in-memory store.

    Satisfies `ensemble.ledger.Ledger`. Replace the delegate with real
    Chaos-Dimension reads/appends without changing any caller.
    """

    def __init__(self, workstream: str = "mold") -> None:
        self.workstream = workstream
        self._delegate = InMemoryLedger(seed=_SEED)  # TODO: swap for live CD

    def append(self, fragment: Fragment) -> None:
        # TODO: create_task / append fragment in the CD `mold` workstream.
        self._delegate.append(fragment)

    def read(self, *, since: str | None = None, beat: str | None = None) -> Sequence[Fragment]:
        # TODO: list_tasks / read fragments from the CD `mold` workstream.
        return self._delegate.read(since=since, beat=beat)
