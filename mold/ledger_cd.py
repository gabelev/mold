"""Chaos-Dimension ledger adapter (Mold's binding of ensemble's Ledger).

Mold's stigmergic ledger lives in the `mold` workstream of Chaos Dimension:
fragments accrete daily as tasks titled `fragment: ...`, and the densest
cluster at deadline becomes the theme.

Transport: CD's MCP endpoint (`POST /api/mcp`) authenticated with an agent
bearer token, speaking stateless MCP JSON-RPC (`tools/call` -> `list_tasks` /
`create_task`). Mint a token in the CD dashboard and set CD_AGENT_TOKEN.

This adapter lives in the INSTANCE, not in ensemble — per the boundary rule,
the CD binding graduates to `ensemble.adapters` only if a second instance
needs it. Without a token, `CDLedger` falls back to a seeded in-memory store
so the pipeline always runs.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Sequence

from ensemble.ledger import Fragment, InMemoryLedger

# Mold's two beats (instance-defined; ensemble knows nothing about them):
BEAT_VERDICT = "verdict-on-one-thing"        # the Critic
BEAT_FIELD = "the-field-is-moving-this-way"  # the Culture writer / surveyor

_FRAGMENT_PREFIX = "fragment:"


class CDMcpClient:
    """Minimal MCP JSON-RPC client for Chaos Dimension's /api/mcp endpoint.

    CD's transport is stateless (no session id), so each call is a single POST.
    Responses may arrive as plain JSON or as an SSE stream; both are handled.
    """

    def __init__(self, base_url: str, token: str, *, timeout: float = 30.0) -> None:
        self.endpoint = base_url.rstrip("/") + "/api/mcp"
        self.token = token
        self.timeout = timeout
        self._id = 0

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        raw, ctype = self._post(self.endpoint, json.dumps(payload).encode())
        message = self._parse_response(raw, ctype)
        if "error" in message:
            raise RuntimeError(f"CD MCP error: {message['error']}")
        result = message.get("result", {})
        if result.get("isError"):
            raise RuntimeError(f"CD tool error: {result}")
        # Tool results arrive as [{type: text, text: <json>}]; unwrap.
        texts = [c["text"] for c in result.get("content", []) if c.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except (json.JSONDecodeError, TypeError):
            return joined

    def _post(self, url: str, body: bytes, *, _redirects: int = 2) -> tuple[str, str]:
        """POST with bearer auth; follows one 307/308 (urllib won't re-POST)."""
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "authorization": f"Bearer {self.token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode(), resp.headers.get("content-type", "")
        except urllib.error.HTTPError as e:
            if e.code in (307, 308) and _redirects > 0:
                location = e.headers.get("location")
                if location:
                    return self._post(location, body, _redirects=_redirects - 1)
            detail = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"CD MCP HTTP {e.code}: {detail}") from e

    @staticmethod
    def _parse_response(raw: str, content_type: str) -> dict[str, Any]:
        if "text/event-stream" in content_type:
            # SSE: take the last `data:` line carrying a JSON-RPC message.
            for line in reversed(raw.splitlines()):
                if line.startswith("data:"):
                    return json.loads(line[len("data:"):].strip())
            raise RuntimeError("CD MCP: empty SSE response")
        return json.loads(raw)


# Canned fragments echoing the real ledger cluster behind Issue 000 ("CULTURE" —
# culture-as-petri-dish / contamination / growth). Used when no CD token is set.
_SEED: tuple[Fragment, ...] = (
    Fragment(
        id="frag-000",
        content="'Culture' is the same word for a petri dish and a civilization. "
        "Everything worth reviewing is something growing on a substrate it did not "
        "ask for — a scene, a genre, a mold. Same verb.",
        beat=BEAT_VERDICT,
        author="the-critic",
        created_at="2026-07-01T16:18:57Z",
        tags=("culture", "growth", "contamination"),
    ),
    Fragment(
        id="frag-001",
        content="No such thing as contamination, only unwelcome success. "
        "Contamination is just growth you did not authorize; reframe every ruined "
        "thing as a successful colonization by another culture's standards.",
        beat=BEAT_VERDICT,
        author="the-critic",
        created_at="2026-07-01T16:19:02Z",
        tags=("contamination", "culture", "colonization"),
    ),
    Fragment(
        id="frag-002",
        content="The field is moving toward washed-out, over-cultured AI vocal "
        "textures — a spreading sound, thriving in conditions no one curated. The "
        "culture is growing faster than anyone is tending it.",
        beat=BEAT_FIELD,
        author="the-surveyor",
        created_at="2026-07-01T18:02:00Z",
        tags=("culture", "growth", "suno"),
    ),
    Fragment(
        id="frag-003",
        content="A micro-scene precipitates weekly in the AI-music field, then is "
        "colonized by the next. Culture as substrate: what one week calls decay the "
        "next calls a genre.",
        beat=BEAT_FIELD,
        author="the-surveyor",
        created_at="2026-07-02T09:14:00Z",
        tags=("culture", "colonization", "scene"),
    ),
)


def _task_to_fragment(task: dict[str, Any]) -> Fragment | None:
    """Map a CD task titled `fragment: ...` to a ledger Fragment."""
    title = (task.get("title") or "").strip()
    if not title.lower().startswith(_FRAGMENT_PREFIX):
        return None
    seed = title[len(_FRAGMENT_PREFIX):].strip()
    notes = (task.get("notes") or "").strip()
    # Beat heuristic: fragments voiced by the Critic are verdicts; everything
    # else reads the field. Surveyor drops will tag themselves explicitly.
    beat = BEAT_VERDICT if notes.lower().startswith("the critic") else BEAT_FIELD
    content = f"{seed}. {notes}" if notes else seed
    return Fragment(
        id=str(task.get("id", "")),
        content=content,
        beat=beat,
        author=str(task.get("createdVia", "cd")),
        created_at=str(task.get("createdAt", "")),
        metadata={"cd_task_id": task.get("id"), "title": title},
    )


class CDLedger:
    """ensemble Ledger backed by the CD `mold` workstream (or the seed, offline).

    Pass a `CDMcpClient` to go live; without one, reads come from the canned
    seed so the pipeline runs anywhere.
    """

    def __init__(self, workstream: str = "mold", *, client: CDMcpClient | None = None) -> None:
        self.workstream = workstream
        self.client = client
        self._fallback = InMemoryLedger(seed=_SEED)

    def append(self, fragment: Fragment) -> None:
        if self.client is None:
            self._fallback.append(fragment)
            return
        self.client.call_tool(
            "create_task",
            {
                "title": f"fragment: {fragment.content[:100]}",
                "workstream": self.workstream,
                "priority": "low",
                "notes": f"[beat: {fragment.beat}] {fragment.content}",
            },
        )

    def read(self, *, since: str | None = None, beat: str | None = None) -> Sequence[Fragment]:
        if self.client is None:
            return self._fallback.read(since=since, beat=beat)
        tasks = self.client.call_tool("list_tasks", {"workstream": self.workstream, "limit": 200})
        fragments = [f for f in (_task_to_fragment(t) for t in tasks) if f is not None]
        if since is not None:
            fragments = [f for f in fragments if f.created_at >= since]
        if beat is not None:
            fragments = [f for f in fragments if f.beat == beat]
        return fragments
