"""Hardening behaviors: the failure modes live runs actually produced."""

from __future__ import annotations

import pytest

from ensemble.ledger import Fragment, InMemoryLedger

from mold.config import build_config
from mold.design.artdirector import _inline
from mold.personas.base import strip_scaffolding
from mold.personas.planner import _ensure_both_beats
from mold.pipeline import EmptyField, build_pipeline
from mold.verify import audit_html


def test_strip_scaffolding_drops_self_titles() -> None:
    body = "# Verdict: Carryover\n**The Lift**\n\nThe actual prose starts here.\n\nAnd continues."
    out = strip_scaffolding(body)
    assert "# Verdict" not in out and "**The Lift**" not in out
    assert out.startswith("The actual prose")


def test_strip_scaffolding_keeps_clean_copy() -> None:
    body = "The track is bad.\n\nSkip it."
    assert strip_scaffolding(body) == body


def test_inline_markdown_renders_safely() -> None:
    html = _inline('Hear it at [the track](https://suno.com/s/x) — **loud** and *wrong* <script>')
    assert '<a href="https://suno.com/s/x" rel="noopener">the track</a>' in html
    assert "<strong>loud</strong>" in html and "<em>wrong</em>" in html
    assert "<script>" not in html  # escaped, not executed


def test_inline_rejects_non_https_links() -> None:
    assert "<a " not in _inline("[x](javascript:alert(1))")
    assert "<a " not in _inline("[x](http://insecure.example)")


def test_markdown_leak_fails_verification() -> None:
    page = ('<!doctype html><html><head><title>t</title></head><body>'
            '<h1>H</h1><p>**The Lift** arrives</p>'
            '<a href="https://x.example">x</a></body></html>')
    errors, _ = audit_html(page)
    assert any("markdown leaked" in e for e in errors)


def test_every_voice_gets_a_story() -> None:
    stories = [{"beat": "the-field-is-moving-this-way", "seed": "s1", "assigned_to": "the-surveyor"}]
    out = _ensure_both_beats(stories)
    critic = [s for s in out if s["assigned_to"] == "the-critic"]
    assert len(critic) == 1
    assert critic[0]["seed"] == "s1" and critic[0].get("reassigned")


def test_groundedness_gate_rejects_abstraction() -> None:
    """The exact Issue-000 failure mode: a polished essay about a slogan."""
    from datetime import date, timedelta

    from ensemble.perceive import Evidence

    from mold.grounded import audit_groundedness

    evidence = [Evidence(
        title="IngaRose 'Celebrate Me'",
        url="https://www.forbes.com/example", published=(date.today() - timedelta(days=5)).isoformat(),
        summary="#1 on iTunes in five countries.", source="test",
    )]
    ungrounded = (
        "The seed handed me a slogan and the slogan is wrong. Contamination is "
        "just growth you did not authorize; every ruined thing is a successful "
        "colonization by another culture's standards. The verdict is on the "
        "idea itself, which curdles under inspection."
    )
    failures = audit_groundedness(ungrounded, evidence)
    assert any("zero outbound links" in f for f in failures)
    assert any("no named work" in f for f in failures)

    grounded = (
        "Verdict first: 'Celebrate Me' by IngaRose is a hit with nobody home "
        "([Forbes](https://www.forbes.com/example)). Number one in five countries "
        "and no author willing to claim it."
    )
    assert audit_groundedness(grounded, evidence) == []


def test_empty_field_aborts_instead_of_publishing(tmp_path) -> None:
    from ensemble.perceive import Perceiver

    class _Blind:
        name = "blind"

        def search(self, query, *, now):
            return []

    cfg = build_config(content_root=tmp_path)
    cfg.ledger = InMemoryLedger(seed=())          # nothing accreted this week
    cfg.perceiver = Perceiver([_Blind()])          # and the scan sees nothing
    with pytest.raises(EmptyField):
        build_pipeline(cfg).run({"issue_id": "000"})
