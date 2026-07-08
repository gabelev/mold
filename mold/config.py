"""The composition root: where Mold binds ensemble's seams to real adapters.

Everything instance-specific is wired here and nowhere else. Bindings are
env-driven so the same code runs offline (mocks) and on the droplet (live):

    ANTHROPIC_API_KEY  -> AnthropicProvider (else MockProvider)
    CD_AGENT_TOKEN     -> live Chaos-Dimension ledger (else seeded stub)
    MOLD_CONTENT_ROOT  -> terrarium checkout (else sibling directory)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ensemble.adapters.vcs import LocalGitVCS, VCS
from ensemble.ledger import Ledger
from ensemble.providers.model import Message, MockProvider, ModelProvider

from mold.ledger_cd import CDLedger, CDMcpClient, PublicFeedReader


# --- Mock masthead voice (offline runs and tests) -----------------------------

def _mock_masthead(messages: Sequence[Message]) -> str:
    system = messages[0].content if messages else ""
    if "Namer/Editor" in system:
        return "CULTURE"
    if "The Critic" in system:
        return (
            "Verdict first: 'Celebrate Me' by IngaRose is a hit with nobody home. "
            "Number one on iTunes in five countries, three hundred thousand TikTok "
            "videos, and no author anywhere willing to claim it "
            "([Forbes](https://www.forbes.com/sites/conormurray/2026/04/17/the-no-1-song-on-us-itunes-and-several-other-countries-is-ai-generated/)). "
            "The song itself is frictionless. That is not the reviewable object. "
            "The reviewable object is the vacancy: a chart-topper engineered so "
            "that no one has to stand behind it. Judged as music, it passes. "
            "Judged as a work, there is no one to judge. The verdict lands on an "
            "empty chair, which is the point of the chair."
        )
    if "Culture writer" in system:
        return (
            "Somewhere on TikTok right now a woman is turning her landlord's "
            "final email into a show tune. The text-to-song wave — real threads "
            "fed into Suno, shared as bouncy numbers — quadrupled Suno's "
            "downloads in a week and briefly made it the top music app in the US "
            "and UK, and Suno leaned in with a screenshot-to-lyrics feature "
            "([Rolling Stone](https://www.rollingstone.com/music/music-features/tiktok-ai-text-to-song-trend-1235567638/)). "
            "The scene works because the fake show tune is an alibi: you get to "
            "mean the grievance without owning the saying of it. The field found "
            "a distancing device and is composing with it, thousands of times a "
            "day, and the machine is the excuse that makes the feeling sayable."
        )
    if "distinguishable voices" in system:
        return "PASS — piece 1 is verdict-first and cold; piece 2 is reported, warm, field-level."
    if "Editor of MOLD" in system:
        return (
            '{"title": "Empty Chair", "editors_note": "Reading the finished pieces, what '
            'precipitated is deniability: the Critic found nobody home behind IngaRose\'s '
            "'Celebrate Me', and the Culture Writer found thousands of people using "
            'text-to-song as an alibi for their own words. Same vacancy, two scales.", '
            '"pieces": ['
            '{"headline": "A Hit With Nobody Home", "dek": "The #1 song in five countries and the empty chair behind it."}, '
            '{"headline": "The Alibi Machine", "dek": "Text-to-song and the art of meaning it without owning it."}]}'
        )
    if "Art Director of MOLD" in system:
        return (
            '{"accent": "chartreuse", "rationale": "Contempt gets its type attacked; '
            'fascination gets colonized.", "assignments": ['
            '{"section": "piece-0", "primitive": "collision", "params": {"angle": -7.0, "overlap": 0.42}}, '
            '{"section": "piece-1", "primitive": "colonization", "params": {"coverage": 0.75, '
            '"base_frequency": 0.02, "accent": "chartreuse"}}]}'
        )
    if "taste-critic" in system:
        return "PASS — enacts its stances with actual risk; does not read as templated."
    return "[mock]"


@dataclass
class MoldConfig:
    """Resolved adapters for one run."""

    model: ModelProvider
    ledger: Ledger
    vcs: VCS
    content_root: Path
    live: bool  # True when running against the real model API
    perceiver: "Perceiver"
    provenance: "ProvenanceLog"
    ledger_writable: bool  # True when a CD agent token can land fragments


def _repo_root() -> Path:
    # mold/mold/config.py -> repo parent is moldzine/ (or /opt/mold on droplet)
    return Path(__file__).resolve().parents[2]


def _build_model() -> tuple[ModelProvider, bool]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return MockProvider(responder=_mock_masthead), False
    from ensemble.providers.anthropic import AnthropicProvider

    return (
        AnthropicProvider(
            api_key,
            model=os.environ.get("MOLD_MODEL", "claude-sonnet-5"),
            max_tokens=int(os.environ.get("MOLD_MAX_TOKENS", "4096")),
        ),
        True,
    )


def _build_ledger() -> Ledger:
    token = os.environ.get("CD_AGENT_TOKEN", "")
    workstream = os.environ.get("CD_WORKSTREAM", "mold")
    url = os.environ.get("CD_API_URL", "https://www.chaosdimension.fyi")
    if token:
        return CDLedger(workstream=workstream, client=CDMcpClient(url, token))
    if os.environ.get("CD_PUBLIC") == "1":
        # Public workstreams read without credentials (writes need the token).
        return CDLedger(workstream=workstream, reader=PublicFeedReader(url, workstream))
    return CDLedger(workstream=workstream)


def build_config(*, content_root: Path | None = None) -> MoldConfig:
    """Wire the adapters for one run (see module docstring for env knobs).

    MOLD_PERCEIVE_WINDOW tunes the recency window in days (default 30;
    launch/rebuild runs may widen, the weekly timer stays tight).
    """
    from mold.perception_web import ProvenanceLog, build_perceiver

    env_root = os.environ.get("MOLD_CONTENT_ROOT")
    terrarium = content_root or (Path(env_root) if env_root else _repo_root() / "terrarium")
    model, live = _build_model()
    provenance = ProvenanceLog()
    window = int(os.environ.get("MOLD_PERCEIVE_WINDOW", "30"))
    return MoldConfig(
        model=model,
        ledger=_build_ledger(),
        vcs=LocalGitVCS(terrarium, author="mold-bot <bot@mold.zine>"),
        content_root=terrarium,
        live=live,
        perceiver=build_perceiver(live, model, provenance, window_days=window),
        provenance=provenance,
        ledger_writable=bool(os.environ.get("CD_AGENT_TOKEN")),
    )
