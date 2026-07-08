"""Mold's PERCEIVE wiring: web-search adapters, provenance, ledger drops.

Two passes per the PERCEIVE spec:
  broad scan  — cycle start, surveys AI music/video/image/agent-scene surfaces;
                candidates become dated ledger fragments; theme precipitates.
  deep verify — per committed piece, pulls the subject's CURRENT facts right
                before the author writes.

Everything here is instance wiring over ensemble.perceive; the mechanics
(recency contract, date injection, dedup) live in the framework.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Sequence

from ensemble.ledger import Fragment
from ensemble.perceive import Evidence, Perceiver

from mold.ledger_cd import BEAT_FIELD, BEAT_VERDICT

# The broad-scan surfaces. Dates are injected by the framework at runtime.
BROAD_QUERIES = (
    "AI generated song chart news {month_year}",
    "Suno Udio AI music viral trend {month_year}",
    "AI music artist controversy streaming {month_year}",
    "AI generated video film culture {month_year}",
)


@dataclass
class ProvenanceLog:
    """Accumulates the run's evidence trail; publish writes it to terrarium."""

    rows: list[dict] = field(default_factory=list)

    def record(self, cycle_id: str, evidence: Evidence, claim: str | None = None) -> None:
        self.rows.append({
            "cycle": cycle_id,
            "title": evidence.title,
            "url": evidence.url,
            "published": evidence.published,
            "fetched_at": evidence.fetched_at,
            "source": evidence.source,
            "supports": claim,
        })

    def to_json(self, *, render: str = "autonomous") -> str:
        return json.dumps({"render": render, "evidence": self.rows}, indent=1) + "\n"


def evidence_to_fragment(e: Evidence) -> Fragment:
    """A broad-scan candidate becomes a dated ledger fragment. Single works
    read as verdict-beat; trends/scenes read as field-beat (heuristic; the
    surveyor's audio pulls will tag properly in Phase 1)."""
    text = f"{e.title}. {e.summary}"
    looks_like_one_work = any(
        m in e.title.lower() for m in ("song", "track", "album", "'", "‘", "“")
    )
    return Fragment(
        id=f"perceive-{abs(hash(e.url)) % 10**8}",
        content=f"{text} ({e.url})",
        beat=BEAT_VERDICT if looks_like_one_work else BEAT_FIELD,
        author="perceive-broad-scan",
        created_at=e.published,
        metadata={"subject": e.title, "url": e.url, "published": e.published},
    )


class MockSearch:
    """Offline adapter: the three seeded [REAL] stories, dated inside the
    window relative to the injected clock so the whole pipeline runs (and the
    gate can PASS) with no network. Proves plumbing, not perception."""

    name = "mock-search"

    def search(self, query: str, *, now: date) -> Sequence[Evidence]:
        recent = (now - timedelta(days=10)).isoformat()
        older = (now - timedelta(days=20)).isoformat()
        rows = [
            Evidence(
                title="IngaRose 'Celebrate Me'",
                url="https://www.forbes.com/sites/conormurray/2026/04/17/the-no-1-song-on-us-itunes-and-several-other-countries-is-ai-generated/",
                published=recent,
                summary="AI persona IngaRose's 'Celebrate Me' hit #1 on iTunes in "
                "the US, UK, France, Canada and NZ, appears in roughly 300k TikTok "
                "videos, 220k followers; nobody has claimed authorship. Three albums "
                "since February.",
                source=self.name, fetched_at=now.isoformat(),
            ),
            Evidence(
                title="text-to-song TikTok trend",
                url="https://www.rollingstone.com/music/music-features/tiktok-ai-text-to-song-trend-1235567638/",
                published=older,
                summary="People feed real text threads into Suno and share the "
                "songs on TikTok; Suno downloads quadrupled week-over-week and it "
                "was briefly the #1 music app in the US and UK. Suno shipped a "
                "screenshot-to-lyrics feature to fuel it.",
                source=self.name, fetched_at=now.isoformat(),
            ),
            Evidence(
                title="Haven 'I Run' impersonation pull",
                url="https://www.forbes.com/sites/rashishrivastava/2026/04/30/inside-sunos-25-billion-bet-that-ai-made-music-is-here-to-stay/",
                published=recent,
                summary="Haven's 'I Run' went viral at 13M streams, was pulled "
                "because its Suno-generated voice sounded too much like Jorja "
                "Smith, then re-recorded with a human voice and passed 160M "
                "streams. The impersonation line drawn live.",
                source=self.name, fetched_at=now.isoformat(),
            ),
        ]
        if "latest" in query.lower():
            # Deep verify: prefer the story whose title overlaps the subject
            # query; a real adapter searches, the mock approximates.
            matched = [
                r for r in rows
                if any(tok.lower() in query.lower() for tok in r.title.replace("'", " ").split() if len(tok) > 3)
            ]
            return matched or rows
        return rows


def build_perceiver(model_live: bool, provider, sink: ProvenanceLog,
                    *, window_days: int) -> Perceiver:
    """Live -> Anthropic web_search; offline -> canned mock. Swappable seam."""
    if model_live:
        from ensemble.adapters.search import AnthropicWebSearch
        adapters = [AnthropicWebSearch(provider)]
    else:
        adapters = [MockSearch()]
    return Perceiver(adapters, window_days=window_days, sink=sink)
