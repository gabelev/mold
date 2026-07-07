"""Assemble Mold's authoring pipeline from ensemble Stages + Mold agents.

The full deterministic DAG:

    planning -> authors (parallel fan-out) -> editor
             -> design (N candidates -> taste discriminator) -> verify -> publish

Design emits N candidate treatments (different constraint injections + variant
jitter); the taste discriminator kills the safe ones. If EVERY candidate is too
safe, one riskier regeneration round runs; if the panel still passes nothing,
the least-dissented candidate ships with the dissent logged (a weekly zine must
ship — the dissent is the training signal).

Verify stays a hard gate: a failed audit raises and nothing is committed.
"""

from __future__ import annotations

from typing import Any, MutableMapping

from ensemble.agent import Artifact
from ensemble.pipeline import Pipeline, Stage, fan_out
from ensemble.state.taboo import Move, TabooMemory

from mold.config import MoldConfig
from mold.design import ArtDirectorAgent
from mold.design.constraints import pick_constraints
from mold.personas import CriticAgent, EditorAgent, PlanningAgent, SurveyorAgent
from mold.prose import ProseTellJudge
from mold.publish import issue_files, load_taboo_signatures
from mold.taste import build_discriminator, candidate_view
from mold.verify import VerificationAgent

N_CANDIDATES = 3


class VerificationFailed(RuntimeError):
    """The rendered issue failed the correctness audit; nothing was committed."""


class EmptyField(RuntimeError):
    """The ledger precipitated nothing; there is no issue to make this week."""


def _fresh_taboo(cfg: MoldConfig) -> TabooMemory:
    # Each candidate composes under its own copy so candidates don't pollute
    # each other's this-cycle log; all share the same forbidden set.
    return TabooMemory(
        forbidden=[Move(kind="design", signature=s) for s in load_taboo_signatures(cfg.content_root)]
    )


def build_pipeline(cfg: MoldConfig) -> Pipeline:
    planner = PlanningAgent(cfg.model, cfg.ledger)
    critic = CriticAgent(cfg.model)
    surveyor = SurveyorAgent(cfg.model)
    editor = EditorAgent(cfg.model)
    verifier = VerificationAgent(cfg.model)
    forbidden = load_taboo_signatures(cfg.content_root)
    discriminator = build_discriminator(cfg.model, forbidden)

    def planning_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        planning = planner.run(ctx)
        if not planning.metadata.get("stories"):
            raise EmptyField("no cluster precipitated from the ledger — feed the field")
        return planning

    prose_judge = ProseTellJudge(cfg.model)

    def _copy_problem(artifact: Artifact) -> str | None:
        """One combined gate: taste tells + degenerate length."""
        words = len(artifact.body.split())
        if words < 60:
            return f"draft is {words} words — too thin to be a piece; write a full one"
        if words > 1600:
            return f"draft is {words} words — an essay, not a zine piece; cut it hard"
        verdict = prose_judge.evaluate({"text": artifact.body})
        return None if verdict.passed else verdict.rationale

    def _gated(agent) -> Any:
        """The content mirror: copy gets one regeneration with its problems
        named; a second failure ships with the dissent logged (the zine must
        ship — dissent is signal, not a blocker)."""
        def run(c: MutableMapping[str, Any]) -> Artifact:
            artifact = agent.run(c)
            problem = _copy_problem(artifact)
            if problem:
                artifact = agent.run({**c, "revision_note": problem})
                problem = _copy_problem(artifact)
                if problem:
                    artifact.metadata = dict(artifact.metadata)
                    artifact.metadata["prose_dissent"] = problem
            return artifact
        return run

    def authors_stage(ctx: MutableMapping[str, Any]) -> list[Artifact]:
        stages = [
            Stage(name="the-critic", fn=_gated(critic)),
            Stage(name="the-surveyor", fn=_gated(surveyor)),
        ]
        results = fan_out(stages, ctx)
        return list(results.values())

    def editor_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return editor.run(ctx)

    def _compose_candidates(ctx: MutableMapping[str, Any], *, risk_boost: int = 0) -> list[Artifact]:
        issue_id = ctx.get("issue_id", "000")
        constraints = pick_constraints(issue_id, N_CANDIDATES)
        candidates = []
        for i, constraint in enumerate(constraints):
            agent = ArtDirectorAgent(
                cfg.model,
                taboo=_fresh_taboo(cfg),
                constraint=constraint,
                variant=i + risk_boost,
            )
            candidates.append(agent.run(ctx))
        return candidates

    def design_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        candidates = _compose_candidates(ctx)
        idx = discriminator.choose([candidate_view(a) for a in candidates])
        dissent_note = ""
        if idx < 0:
            # Everything was too well-behaved: regenerate RISKIER, once.
            candidates = _compose_candidates(ctx, risk_boost=2)
            idx = discriminator.choose([candidate_view(a) for a in candidates])
        if idx < 0:
            # Ship the least-dissented candidate; log the dissent as signal.
            results = [discriminator.evaluate(candidate_view(a)) for a in candidates]
            idx = min(range(len(results)), key=lambda i: len(results[i].dissenters))
            dissent_note = "; ".join(
                f"{v.grounding}: {v.rationale}" for v in results[idx].dissenters
            )
        chosen = candidates[idx]
        chosen.metadata = dict(chosen.metadata)
        chosen.metadata["dissent"] = dissent_note
        # Keep every candidate page for the warm-start human pick.
        chosen.metadata["candidate_pages"] = {
            chr(ord("a") + i): a.body for i, a in enumerate(candidates)
        }
        chosen.metadata["chosen_candidate"] = chr(ord("a") + idx)
        return chosen

    def verify_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        report = verifier.run(ctx)
        if not report.metadata["ok"]:
            raise VerificationFailed(report.body)
        return report

    def publish_stage(ctx: MutableMapping[str, Any]):
        issue: Artifact = ctx["editor"]
        files = issue_files(issue, ctx["design"], cfg.content_root)
        return cfg.vcs.write_and_commit(
            files,
            message=f"issue {issue.metadata['issue_id']}: {issue.metadata['theme']}",
            branch="qa",
        )

    return (
        Pipeline()
        .then("planning", planning_stage)
        .then("authors", authors_stage)
        .then("editor", editor_stage)
        .then("design", design_stage)
        .then("verify", verify_stage)
        .then("publish", publish_stage)
    )
