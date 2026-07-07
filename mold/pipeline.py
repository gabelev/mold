"""Assemble Mold's authoring pipeline from ensemble Stages + Mold agents.

The slice covers the first four stages of the full pipeline:

    planning -> authors (parallel fan-out) -> editor -> publish

Design, verify, and deploy are deliberately omitted here (stubs/protocols
elsewhere). The shape matches the full pipeline so those stages drop in later
without re-plumbing.
"""

from __future__ import annotations

from typing import Any, MutableMapping

from ensemble.agent import Artifact
from ensemble.pipeline import Pipeline, Stage, fan_out

from mold.config import MoldConfig
from mold.personas import CriticAgent, EditorAgent, PlanningAgent


def build_pipeline(cfg: MoldConfig) -> Pipeline:
    planner = PlanningAgent(cfg.model, cfg.ledger)
    critic = CriticAgent(cfg.model)
    editor = EditorAgent(cfg.model)

    def planning_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return planner.run(ctx)

    def authors_stage(ctx: MutableMapping[str, Any]) -> list[Artifact]:
        # One author in the slice, but routed through the parallel fan-out seam
        # so adding masthead members later is just a longer list.
        stages = [Stage(name="the-critic", fn=lambda c: critic.run(c))]
        results = fan_out(stages, ctx)
        return list(results.values())

    def editor_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return editor.run(ctx)

    def publish_stage(ctx: MutableMapping[str, Any]):
        issue: Artifact = ctx["editor"]
        issue_id = issue.metadata["issue_id"]
        files = {
            f"issues/{issue_id}/index.md": issue.body,
            f"issues/{issue_id}/planning.md": issue.metadata["planning_body"],
        }
        return cfg.vcs.write_and_commit(
            files,
            message=f"issue {issue_id}: {issue.metadata['theme']} (autonomous slice)",
            branch="qa",
        )

    return (
        Pipeline()
        .then("planning", planning_stage)
        .then("authors", authors_stage)
        .then("editor", editor_stage)
        .then("publish", publish_stage)
    )
