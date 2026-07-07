"""The Verification agent: correctness, not taste.

Checks the rendered issue BEFORE anything is committed:
  - structure: doctype, title, headline type present in the DOM
  - copyright wall: no rehosted media (<audio>/<video>), no data:audio URIs
  - visual doctrine: no raster in headlines (type stays in the DOM)
  - links: every href is http(s), mailto, or relative — no javascript:
(Taste is the discriminator's job; this gate only removes actual mistakes.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Mapping

from ensemble.agent import Agent, Artifact, Decision, Perception, Persona

BASE_PROMPT = "You verify MOLD issues for correctness: rendering, links, the copyright wall."

_FORBIDDEN_TAGS = {"audio", "video", "embed", "object"}
_HEADLINE_TAGS = {"h1", "h2", "h3"}


@dataclass
class _Audit(HTMLParser):
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _open: list[str] = field(default_factory=list)
    has_title: bool = False
    headline_count: int = 0
    external_links: int = 0

    def __post_init__(self) -> None:
        super().__init__(convert_charrefs=True)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in _FORBIDDEN_TAGS:
            self.errors.append(f"copyright wall: <{tag}> is rehosted media; describe and link instead")
        if tag == "title":
            self.has_title = True
        if tag in _HEADLINE_TAGS:
            self.headline_count += 1
            self._open.append(tag)
        if tag == "img":
            if any(h in self._open for h in _HEADLINE_TAGS):
                self.errors.append("doctrine: raster inside a headline; type stays in the DOM")
            src = a.get("src", "") or ""
            if src.startswith("data:audio"):
                self.errors.append("copyright wall: data:audio URI")
        if tag in ("a", "link"):
            href = (a.get("href") or "").strip()
            if href.startswith("javascript:"):
                self.errors.append(f"link: javascript: href ({href[:40]})")
            elif href.startswith(("http://", "https://")):
                self.external_links += 1
                if href.startswith("http://"):
                    self.warnings.append(f"link not https: {href[:60]}")

    def handle_endtag(self, tag: str) -> None:
        if self._open and self._open[-1] == tag:
            self._open.pop()


_MD_LEAK = re.compile(r"<p>[^<]{0,40}(\*\*|^#{1,3} |\[[^\]]+\]\(https?://)", re.M)


def audit_html(page: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one rendered issue page."""
    auditor = _Audit()
    auditor.feed(page)
    errors, warnings = list(auditor.errors), list(auditor.warnings)
    if _MD_LEAK.search(page):
        errors.append("render: raw markdown leaked into the DOM (** / # / [](...) visible as text)")
    if not page.lstrip().lower().startswith("<!doctype html"):
        errors.append("structure: missing doctype")
    if not auditor.has_title:
        errors.append("structure: missing <title>")
    if auditor.headline_count == 0:
        errors.append("structure: no headline type in the DOM")
    if auditor.external_links == 0:
        # Coverage should link out to what it covers. Warning (not failure)
        # while the masthead runs on stub content.
        warnings.append("coverage has no external links — every subject should be linked")
    return errors, warnings


class VerificationAgent(Agent):
    """Wraps the audit in the standard agent loop so it slots into the pipeline."""

    def __init__(self, model, **kw: Any) -> None:
        super().__init__(Persona(name="verifier", base_prompt=BASE_PROMPT), model, **kw)

    def perceive(self, context: Mapping[str, Any]) -> Perception:
        return Perception(data={"design": context["design"]})

    def decide(self, perception: Perception) -> Decision:
        return Decision(data=perception.data)

    def execute(self, decision: Decision) -> Artifact:
        design: Artifact = decision.data["design"]
        errors, warnings = audit_html(design.body)
        report = "\n".join(
            [f"ERROR: {e}" for e in errors] + [f"warn: {w}" for w in warnings]
        ) or "clean"
        return Artifact(
            kind="verification",
            body=report,
            metadata={"ok": not errors, "errors": errors, "warnings": warnings},
        )
