# The fixed shell (human territory)

Per the design-engine spec, the page chrome — home/archive, wordmark — is
authored by a human (Claude Design is the intended canvas), NOT composed by
the weekly Art Director. Drop the designed page here as `archive.html`; the
publisher substitutes:

- `{{ISSUE_LIST}}` — `<li><a href="issues/NNN/index.html">…</a></li>` rows,
  newest first (style the `<li>`/`<a>`/`.num` however the design wants)
- `{{ISSUE_COUNT}}` — optional, total issue count

Everything else in the file ships verbatim. No template here = the built-in
fallback page in `mold/publish.py` is used.
