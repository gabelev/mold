"""The content mirror: prose AI-tells the discriminator must catch."""

from __future__ import annotations

from ensemble.providers.model import MockProvider

from mold.prose import ProseTellJudge, audit_prose


def test_clean_pan_passes() -> None:
    text = (
        "The track is bad. Not interestingly bad: bad the way a stock photo is "
        "bad, every choice pre-made by someone else. The vocal chop arrives "
        "exactly where you fear it will. Skip it and listen to the b-side."
    )
    assert audit_prose(text) == []


def test_isnt_just_pivot_caught() -> None:
    assert "isn't-just-pivot" in audit_prose("This isn't just a song, it's a movement.")
    assert "isn't-just-pivot" in audit_prose("It is not just noise but a statement.")


def test_hedging_and_gentle_positivity_caught() -> None:
    tells = audit_prose(
        "Perhaps the most delightful thing here is, arguably, a testament to craft."
    )
    assert "hedging" in tells
    assert "gentle-positivity" in tells


def test_rule_of_three_caught_when_repeated() -> None:
    text = (
        "It blooms, spreads, and settles. The mix is warm, wide, and deep. "
        "The ending is slow, sad, and sweet."
    )
    assert "rule-of-three" in audit_prose(text)
    # A single triad is rhythm, not a template.
    assert "rule-of-three" not in audit_prose("It blooms, spreads, and settles.")


def test_judge_combines_model_and_heuristics() -> None:
    passing_model = MockProvider(responder=lambda m: "PASS — real stance.")
    judge = ProseTellJudge(passing_model)
    # Model passes but heuristics find a tell -> overall fail (pass-all anchors).
    v = judge.evaluate({"text": "This isn't just music, it's a mirror."})
    assert not v.passed
    assert "isn't-just-pivot" in v.rationale
    # Clean text + passing model -> pass.
    assert judge.evaluate({"text": "The track is bad. Skip it."}).passed
