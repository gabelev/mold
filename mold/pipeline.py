"""Assemble Mold's authoring pipeline from ensemble Stages + Mold agents.

The full deterministic DAG:

    planning -> authors (parallel fan-out) -> editor -> design -> verify -> publish

Verify is a hard gate: a failed audit raises and nothing is committed. Publish
writes the issue + regenerated archive + bumped drift-state to terrarium on the
qa branch; promotion to prod is the caller's move (see mold.publish).
"""

from __future__ import annotations

from typing import Any, MutableMapping

from ensemble.agent import Artifact
from ensemble.pipeline import Pipeline, Stage, fan_out
from ensemble.state.taboo import Move, TabooMemory

from mold.config import MoldConfig
from mold.design import ArtDirectorAgent
from mold.personas import CriticAgent, EditorAgent, PlanningAgent
from mold.publish import issue_files, load_taboo_signatures
from mold.verify import VerificationAgent


class VerificationFailed(RuntimeError):
    """The rendered issue failed the correctness audit; nothing was committed."""


def build_pipeline(cfg: MoldConfig) -> Pipeline:
    planner = PlanningAgent(cfg.model, cfg.ledger)
    critic = CriticAgent(cfg.model)
    editor = EditorAgent(cfg.model)
    # Last issue's design moves are this issue's forbidden list.
    taboo = TabooMemory(
        forbidden=[Move(kind="design", signature=s) for s in load_taboo_signatures(cfg.content_root)]
    )
    art_director = ArtDirectorAgent(cfg.model, taboo=taboo)
    verifier = VerificationAgent(cfg.model)

    def planning_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return planner.run(ctx)

    def authors_stage(ctx: MutableMapping[str, Any]) -> list[Artifact]:
        # The masthead fans out in parallel; one author today, more soon.
        stages = [Stage(name="the-critic", fn=lambda c: critic.run(c))]
        results = fan_out(stages, ctx)
        return list(results.values())

    def editor_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return editor.run(ctx)

    def design_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return art_director.run(ctx)

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
