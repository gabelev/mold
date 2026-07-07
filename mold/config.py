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

from mold.ledger_cd import CDLedger, CDMcpClient


# --- Mock masthead voice (offline runs and tests) -----------------------------

def _mock_masthead(messages: Sequence[Message]) -> str:
    system = messages[0].content if messages else ""
    if "Namer/Editor" in system:
        return "CULTURE"
    if "The Critic" in system:
        return (
            "The track calls itself ambient but it is a colony. Three minutes of "
            "washed-out vocal texture that nobody cultured on purpose and that is "
            "exactly the point: it thrives in conditions no one tended. Described, "
            "not reproduced — go hear it at the link and notice how the reverb "
            "spreads like something growing on a surface it was never offered. "
            "Verdict: unwelcome success. It is good the way mold is good."
        )
    return "[mock]"


@dataclass
class MoldConfig:
    """Resolved adapters for one run."""

    model: ModelProvider
    ledger: Ledger
    vcs: VCS
    content_root: Path
    live: bool  # True when running against the real model API


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
    if not token:
        return CDLedger(workstream=workstream)
    client = CDMcpClient(os.environ.get("CD_API_URL", "https://www.chaosdimension.fyi"), token)
    return CDLedger(workstream=workstream, client=client)


def build_config(*, content_root: Path | None = None) -> MoldConfig:
    """Wire the adapters for one run (see module docstring for env knobs)."""
    env_root = os.environ.get("MOLD_CONTENT_ROOT")
    terrarium = content_root or (Path(env_root) if env_root else _repo_root() / "terrarium")
    model, live = _build_model()
    return MoldConfig(
        model=model,
        ledger=_build_ledger(),
        vcs=LocalGitVCS(terrarium, author="mold-bot <bot@mold.zine>"),
        content_root=terrarium,
        live=live,
    )
