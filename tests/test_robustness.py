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


def test_empty_field_aborts_instead_of_publishing(tmp_path) -> None:
    cfg = build_config(content_root=tmp_path)
    cfg.ledger = InMemoryLedger(seed=())  # nothing accreted this week
    with pytest.raises(EmptyField):
        build_pipeline(cfg).run({"issue_id": "000"})
