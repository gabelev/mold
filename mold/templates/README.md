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

## `issue.html` — the issue page's stage

The weekly Art Director composes primitives ONTO this template; the template
is the stage, not the performance. Placeholders:

- `{{THEME}}` — issue title (escaped text)
- `{{ISSUE_ID}}` — zero-padded number
- `{{EDITORS_NOTE}}` — `<aside class="note"><p>…</p></aside>` or empty
- `{{SECTIONS}}` — the pieces, as `<section id="piece-N" class="piece">` blocks
  containing `.kicker` (byline), `.headline` (h2, with `data-text` duplicate
  for collision effects), optional `.dek`, and `.body` (paragraphs)
- `{{COMPOSED_CSS}}` — the Art Director's per-issue primitive CSS; put it in a
  `<style>` AFTER the template's own styles so composition wins
- `{{ACCENT_HEX}}` — the issue's dominant accent color

MUST keep: the section class names above (primitives target them) and an SVG
`<filter id="bloom">` def (the colonization primitive references `url(#bloom)`).
No template here = the built-in dark shell in `mold/design/artdirector.py`.
