"""The composition root: where Mold binds ensemble's seams to real adapters.

Everything instance-specific is wired here and nowhere else — the model
provider, the ledger, and the VCS target. Swapping the mock model for Claude, or
the seeded CDLedger for live Chaos Dimension, is a one-line change here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ensemble.adapters.vcs import LocalGitVCS, VCS
from ensemble.ledger import Ledger
from ensemble.providers.model import Message, MockProvider, ModelProvider

from mold.ledger_cd import CDLedger


# --- Mock masthead voice (vertical-slice only) -------------------------------
# Deterministic, offline responses keyed to which persona is asking. Replaced by
# a real ModelProvider (Claude) once the slice is proven.

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


def _repo_root() -> Path:
    # mold/mold/config.py -> repo parent is moldzine/
    return Path(__file__).resolve().parents[2]


def build_config(*, content_root: Path | None = None) -> MoldConfig:
    """Wire the slice's adapters. Mock model, seeded CD ledger, terrarium VCS.

    Resolution order for the content repo: explicit arg > MOLD_CONTENT_ROOT env
    (set by the droplet units via /etc/mold/mold.env) > sibling checkout.
    """
    import os

    env_root = os.environ.get("MOLD_CONTENT_ROOT")
    terrarium = content_root or (Path(env_root) if env_root else _repo_root() / "terrarium")
    return MoldConfig(
        model=MockProvider(responder=_mock_masthead),
        ledger=CDLedger(workstream="mold"),
        vcs=LocalGitVCS(terrarium, author="mold-bot <bot@mold.zine>"),
        content_root=terrarium,
    )
