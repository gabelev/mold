"""The taste discriminator: the bar-keeper's rules."""

from __future__ import annotations

from ensemble.providers.model import MockProvider

from mold.taste import RiskFloorJudge, TabooComplianceJudge, build_discriminator


def _tame_candidate() -> dict:
    """Everything balanced and readable — competent-generic."""
    return {
        "moves": ["agar:reverence"],
        "assignments": [
            {"section": "piece-0", "stance": "reverence", "primitive": "agar",
             "params": {"section": "piece-0", "tilt": 0.0}},
        ],
        "constraint": "house",
    }


def _risky_candidate() -> dict:
    return {
        "moves": ["collision:contempt"],
        "assignments": [
            {"section": "piece-0", "stance": "contempt", "primitive": "collision",
             "params": {"section": "piece-0", "angle": -6.0, "overlap": 0.4}},
        ],
        "constraint": "house",
    }


def test_risk_floor_rejects_the_absence_of_mistakes() -> None:
    judge = RiskFloorJudge()
    assert not judge.evaluate(_tame_candidate()).passed
    assert judge.evaluate(_risky_candidate()).passed


def test_taboo_judge_rejects_reused_moves() -> None:
    judge = TabooComplianceJudge(forbidden=["collision:contempt"])
    assert not judge.evaluate(_risky_candidate()).passed
    assert judge.evaluate(_tame_candidate()).passed


def test_panel_is_pass_all_and_choose_signals_regeneration() -> None:
    model = MockProvider(responder=lambda msgs: "PASS — not templated.")
    disc = build_discriminator(model, forbidden=[])

    # A tame candidate fails the panel even though the model judge passes it:
    # anchors stay separate; one dissenting grounding kills it.
    assert not disc.evaluate(_tame_candidate()).accepted
    assert disc.evaluate(_risky_candidate()).accepted

    # All-safe batch -> -1: regenerate riskier, don't polish.
    assert disc.choose([_tame_candidate(), _tame_candidate()]) == -1
    assert disc.choose([_tame_candidate(), _risky_candidate()]) == 1
