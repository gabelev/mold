"""Assemble Mold's authoring pipeline from ensemble Stages + Mold agents.

The full deterministic DAG (PERCEIVE per the design spec — mandatory, dated,
sourced; an optional tool is a skipped tool):

    perceive (broad scan) -> planning (theme precipitates)
      -> authors (each: deep-verify PERCEIVE -> write -> prose + groundedness gates)
      -> voice-differentiation gate
      -> editor (reads finished pieces; Namer names LAST; attributed note)
      -> design (N candidates -> taste discriminator)
      -> verify -> publish (+ provenance record + Claude Design brief)

Teeth: groundedness failure after one regeneration ABORTS the run (unsourced
= rejected; a missed week beats an ungrounded issue). Prose/voice failures
regenerate once then ship with dissent logged. Verification stays a hard gate.
"""

from __future__ import annotations

from typing import Any, MutableMapping

from ensemble.agent import Artifact
from ensemble.pipeline import Pipeline, Stage, fan_out
from ensemble.state.taboo import Move, TabooMemory

from mold.config import MoldConfig
from mold.design import ArtDirectorAgent
from mold.design.brief import design_brief
from mold.design.constraints import pick_constraints
from mold.grounded import GroundednessFailed, audit_groundedness
from mold.perception_web import BROAD_QUERIES, evidence_to_fragment
from mold.personas import CriticAgent, EditorAgent, PlanningAgent, SurveyorAgent
from mold.prose import ProseTellJudge
from mold.publish import issue_files, load_taboo_signatures
from mold.taste import build_discriminator, candidate_view
from mold.verify import VerificationAgent
from mold.voices import check_voices

N_CANDIDATES = 3


class VerificationFailed(RuntimeError):
    """The rendered issue failed the correctness audit; nothing was committed."""


class EmptyField(RuntimeError):
    """The ledger precipitated nothing; there is no issue to make this week."""


def _fresh_taboo(cfg: MoldConfig) -> TabooMemory:
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
    prose_judge = ProseTellJudge(cfg.model)

    # -- PERCEIVE pass 1: broad scan ------------------------------------------

    def perceive_stage(ctx: MutableMapping[str, Any]) -> list:
        issue_id = ctx.get("issue_id", "000")
        evidence = cfg.perceiver.broad_scan(BROAD_QUERIES, cycle_id=issue_id)
        fragments = [evidence_to_fragment(e) for e in evidence]
        if cfg.ledger_writable:
            for f in fragments:
                cfg.ledger.append(f)  # lands in CD; planning reads it back
        else:
            ctx["scan_fragments"] = fragments  # merge in-memory for this run
        return evidence

    def planning_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        planning = planner.run(ctx)
        if not planning.metadata.get("stories"):
            raise EmptyField("no cluster precipitated from the ledger — feed the field")
        return planning

    # -- authors: deep-verify PERCEIVE + write + gates -------------------------

    def _story_for(ctx: MutableMapping[str, Any], role: str) -> dict | None:
        stories = ctx["planning"].metadata.get("stories", [])
        return next((s for s in stories if s["assigned_to"] == role), None)

    def _copy_problem(artifact: Artifact, evidence: list) -> tuple[str | None, bool]:
        """(problem, is_groundedness). Groundedness failures are fatal on repeat."""
        grounding = audit_groundedness(artifact.body, evidence)
        if grounding:
            return "; ".join(grounding), True
        words = len(artifact.body.split())
        if words < 60:
            return f"draft is {words} words — too thin to be a piece; write a full one", False
        if words > 1600:
            return f"draft is {words} words — an essay, not a zine piece; cut it hard", False
        verdict = prose_judge.evaluate({"text": artifact.body})
        return (None, False) if verdict.passed else (verdict.rationale, False)

    def _subject_evidence_fallback(c: MutableMapping[str, Any], subject: str) -> list:
        """Deep-verify can come back empty (search hiccup, undatable results).
        The broad scan already passed the recency window — reuse its rows for
        this subject before letting the gate abort the run."""
        broad = c.get("perceive", [])
        tokens = {t.lower() for t in subject.replace("'", " ").split() if len(t) > 3}
        return [e for e in broad if tokens & {t.lower() for t in e.title.replace("'", " ").split()}]

    def _gated(agent, role: str) -> Any:
        def run(c: MutableMapping[str, Any]) -> Artifact:
            story = _story_for(c, role)
            subject = story.get("subject", "") if story else ""
            evidence = cfg.perceiver.deep_verify(
                subject, cycle_id=c.get("issue_id", "")
            ) if subject else []
            if not evidence and subject:
                evidence = _subject_evidence_fallback(c, subject)
            ctx = {**c, "evidence": evidence}

            artifact = agent.run(ctx)
            artifact.metadata = dict(artifact.metadata)
            artifact.metadata["evidence_urls"] = [e.url for e in evidence]

            problem, fatal = _copy_problem(artifact, evidence)
            if problem:
                artifact = agent.run({**ctx, "revision_note": problem})
                artifact.metadata = dict(artifact.metadata)
                artifact.metadata["evidence_urls"] = [e.url for e in evidence]
                problem, fatal = _copy_problem(artifact, evidence)
                if problem and fatal:
                    raise GroundednessFailed(
                        f"{role}: {problem} — unsourced pieces do not ship"
                    )
                if problem:
                    artifact.metadata["prose_dissent"] = problem
            return artifact
        return run

    def authors_stage(ctx: MutableMapping[str, Any]) -> list[Artifact]:
        stages = [
            Stage(name="the-critic", fn=_gated(critic, "the-critic")),
            Stage(name="the-surveyor", fn=_gated(surveyor, "the-surveyor")),
        ]
        results = fan_out(stages, ctx)
        return list(results.values())

    # -- voice-differentiation gate --------------------------------------------

    def voices_stage(ctx: MutableMapping[str, Any]) -> str:
        authors: list[Artifact] = ctx["authors"]
        ok, rationale = check_voices(cfg.model, authors)
        if not ok:
            # Regenerate the later voice with the collapse named; recheck once.
            redo = _gated(surveyor, "the-surveyor")
            authors[1] = redo({**ctx, "revision_note": f"voice collapse with the Critic: {rationale}. "
                              "Write in YOUR register — wide, warm, field-level, no verdict-opening."})
            ok, rationale = check_voices(cfg.model, authors)
            if not ok:
                authors[1].metadata = dict(authors[1].metadata)
                authors[1].metadata["voice_dissent"] = rationale
        return rationale

    def editor_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        return editor.run(ctx)

    # -- design -----------------------------------------------------------------

    def _compose_candidates(ctx: MutableMapping[str, Any], *, risk_boost: int = 0) -> list[Artifact]:
        issue_id = ctx.get("issue_id", "000")
        constraints = pick_constraints(issue_id, N_CANDIDATES)
        return [
            ArtDirectorAgent(
                cfg.model, taboo=_fresh_taboo(cfg), constraint=constraint, variant=i + risk_boost
            ).run(ctx)
            for i, constraint in enumerate(constraints)
        ]

    def design_stage(ctx: MutableMapping[str, Any]) -> Artifact:
        candidates = _compose_candidates(ctx)
        idx = discriminator.choose([candidate_view(a) for a in candidates])
        dissent_note = ""
        if idx < 0:
            candidates = _compose_candidates(ctx, risk_boost=2)
            idx = discriminator.choose([candidate_view(a) for a in candidates])
        if idx < 0:
            results = [discriminator.evaluate(candidate_view(a)) for a in candidates]
            idx = min(range(len(results)), key=lambda i: len(results[i].dissenters))
            dissent_note = "; ".join(
                f"{v.grounding}: {v.rationale}" for v in results[idx].dissenters
            )
        chosen = candidates[idx]
        chosen.metadata = dict(chosen.metadata)
        chosen.metadata["dissent"] = dissent_note
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
        issue_id = issue.metadata["issue_id"]
        files = issue_files(issue, ctx["design"], cfg.content_root)
        # PERCEIVE provenance + the Claude Design manual-fork brief.
        files[f"issues/{issue_id}/provenance.json"] = cfg.provenance.to_json()
        files[f"issues/{issue_id}/claude-design-brief.md"] = design_brief(
            issue, ctx["design"], ctx["authors"], load_taboo_signatures(cfg.content_root)
        )
        return cfg.vcs.write_and_commit(
            files,
            message=f"issue {issue_id}: {issue.metadata['theme']}",
            branch="qa",
        )

    return (
        Pipeline()
        .then("perceive", perceive_stage)
        .then("planning", planning_stage)
        .then("authors", authors_stage)
        .then("voices", voices_stage)
        .then("editor", editor_stage)
        .then("design", design_stage)
        .then("verify", verify_stage)
        .then("publish", publish_stage)
    )
