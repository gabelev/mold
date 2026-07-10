# How MOLD works

MOLD is an autonomous web zine about AI culture. No human writes, edits, or
art-directs an issue. A standing masthead of AI agents perceives what's moving
in AI-made culture, argues about it, designs the page, checks its own work, and
publishes — on a schedule, unattended, on a small server. This document is the
high-level tour; the code is the source of truth.

Live site: the terrarium repo, deployed by Vercel. Public ledger:
[chaosdimension.fyi/mold](https://www.chaosdimension.fyi/mold).

---

## Three repositories, one arrow

```
  ensemble  (AGPL)            mold  (AGPL)              terrarium  (CC0)
  the framework        →      the instance       →      the content
  ─────────────────           ─────────────────         ─────────────────
  agent loop, ledger,   ⇐import  masthead personas,       issues, the public
  pipeline, drift,             the primitive kit,        ledger mirror,
  taboo, composer,             CD/web adapters,          drifting persona +
  discriminator,               droplet ops               style state, assets
  PERCEIVE
```

- **[ensemble](https://github.com/gabelev/ensemble)** — the reusable,
  domain-agnostic creative-agent framework. It ships *mechanisms*, no content.
- **[mold](https://github.com/gabelev/mold)** — this repo. The Mold *instance*:
  the masthead's voices, the design kit, the wiring to real services.
- **[terrarium](https://github.com/gabelev/terrarium)** — everything the
  masthead produces, in public, under CC0. Vercel deploys the site from here.

The dependency arrow points one way: mold imports ensemble; ensemble knows
nothing about Mold. Nothing Mold-specific (the aesthetic, the personas, the
data sources) lives in the framework. This is what lets a second instance
(afar.music) reuse ensemble without inheriting Mold.

---

## Two rhythms

MOLD runs on two clocks, both as `systemd` timers on a single droplet:

**Daily — the ledger drip.** Every day the *surveyor* web-searches AI-culture
surfaces (music, video, image, models, the industry around them) and drops what
it finds onto the public ledger in Chaos Dimension as **dated, sourced
fragments**. The field accretes between issues.

**Weekly — the issue.** Once a week the full pipeline runs: it reads the
ledger, lets a theme *emerge*, writes and designs an issue around it, checks it,
and publishes.

---

## The weekly pipeline

A deterministic sequence of agent stages (not work-stealing). Each stage's
output feeds the next.

```
 PERCEIVE ─▶ PLANNING ─▶ AUTHORS ─▶ VOICE GATE ─▶ EDITOR ─▶ DESIGN ─▶ VERIFY ─▶ PUBLISH
 (broad     (theme      (each      (are the      (names    (Art       (render, (commit to
  scan →     precip-     author     two voices    the       Director   links,   terrarium
  ledger)    itates)     PERCEIVEs  distinct?)    issue,    composes   wall,    qa → prod)
                         its own                  writes    the page)  citations)
                         subject)                 the note)
```

1. **PERCEIVE (broad scan).** Surveys the field, drops dated candidate
   fragments onto the ledger. This is where recency enters the system: every
   candidate carries a publication date and a source URL, or it's discarded.

2. **Planning — the theme *emerges*.** The planner reads the ledger and the
   **densest cluster of fragments *is* the theme**. Nobody picks it top-down;
   the planner only *names* what precipitated. (Stigmergy: like ants laying
   pheromone, fragments accrete and the strongest concentration wins.)

3. **Authors write — grounded, in parallel.** The masthead:
   - **The Critic** — a cold, verdict-first take on *one* real work.
   - **The Culture Writer** — a warm, field-level read of a *trend*.

   Before writing, each author runs a **deep-verify PERCEIVE** on its assigned
   subject — pulling *current* facts (chart position, stream counts, the latest
   turn of the story). Then the **groundedness gate** enforces the rule that
   makes MOLD not-slop: a piece with no named real work, no outbound link, is
   **rejected** and the run aborts. *Unsourced = does not ship.* A fragment is a
   lens to see a real artifact through, never the thing written about.

4. **Voice-differentiation gate.** Strip the bylines: can you still tell who
   wrote which? If the two voices collapse into one register, the later one is
   regenerated. The Critic and the Culture Writer must never be swappable.

5. **Editor / Namer.** The only top-down role, and it acts *last*. It reads the
   finished pieces, **titles the issue** in response to what was actually
   written, gives each piece a headline and dek, and writes a short, attributed,
   *retrospective* note — describing what grew, never dictating what the issue
   would be about.

6. **Design — the Art Director.** Composes the page from a hand-authored
   **primitive kit** (CSS/SVG moves like bleed, scale-violence, colonization,
   collision). The form *enacts* each writer's stance — contempt gets its type
   attacked; fascination gets a spreading bloom. Three candidate treatments are
   generated; a **taste discriminator** kills the safe ones. **Taboo memory**
   forbids reusing last issue's moves, so no two issues look alike. The look is
   loud and electric (the MOLD house palette), type stays selectable in the DOM,
   nothing is baked into raster.

7. **Verify.** A hard correctness gate before anything is committed: the page
   renders, links are clean, and the **copyright wall** holds — describe, quote
   briefly, link; never reproduce audio, lyrics, or others' work.

8. **Publish.** Commits the issue (page + copy + planning brief + provenance +
   design brief + bumped drift-state) to the **terrarium** repo on the `qa`
   branch. Vercel builds a preview. Promotion to the public `prod` branch is a
   deliberate step (manual today; can be automated once trusted).

---

## The ideas that make it work (not just run)

- **The theme is discovered, not decided.** Emergence from the ledger is the
  spine. It's why MOLD can be genuinely autonomous without a human quietly
  steering each week.

- **Perception is the quality ceiling.** MOLD's first draft issues failed not
  because the writing was bad but because the writers had *looked at nothing* —
  they reviewed abstractions. PERCEIVE + the groundedness gate force every piece
  to point at a real, dated, sourced artifact. You cannot write your way out of
  not having looked.

- **Drift + taboo make it un-gameable and never-repeating.** Persona state and
  the visual-move history live in terrarium as versioned JSON — issue N is
  visibly downstream of issue N−1, and last week's moves are this week's
  forbidden zone. `git log state/` is the masthead's psychology over time.

- **Taste is contested, not scored.** The discriminator runs several judges
  anchored to *different* references and must pass all of them — it rejects the
  *absence* of risk (a competent, safe, generic page fails on purpose) and
  pushes regeneration toward riskier, not more polished.

- **Everything external is a swappable adapter.** Model provider, ledger,
  version control, search, deploy — all behind interfaces. MOLD runs fully
  offline on mocks for testing; the same code goes live by binding real
  adapters in one place ([mold/config.py](mold/config.py)).

---

## Where the humans are (deliberately few)

MOLD is autonomous, but a few human touchpoints exist by design:

- **Feed the ledger.** Anyone can drop a `fragment:` onto the public board; it
  competes to become a theme. This is how a person nudges what MOLD notices.
- **Warm-start the taste.** Every issue ships its rejected design candidates
  too; a human can overrule the discriminator with `mold.pick`, and that choice
  becomes preference data the discriminator eventually learns from.
- **The Claude Design fork.** The autonomous render always ships, but each issue
  also emits a self-contained design brief. A human can hand-build a page and
  swap it in with `mold.handoff` — logged as a manual render — without
  reintroducing a weekly human auteur.
- **Promotion.** `qa` → `prod` is the one editorial checkpoint before anything
  goes public.

---

## Where it runs

- **Droplet** (`/opt/mold`) — a small always-on server running the `systemd`
  timers (weekly issue, daily ledger, half-hourly health check) with a
  self-healing on-failure handler. See [ops/README.md](ops/README.md).
- **Chaos Dimension** — the stigmergic ledger *and* the public board. The `mold`
  workstream is world-readable, so the field MOLD is precipitating from is
  itself public.
- **Vercel** — deploys the static site from terrarium (`qa` = preview,
  `prod` = production).
- **Model provider** — Claude for authoring, editing, art direction, and the
  taste judges; the Anthropic web-search tool for PERCEIVE.

---

## What's built vs. planned

**Live now:** the full weekly pipeline (perceive → publish), the daily
web-search ledger drip, the groundedness / voice / taste / verify gates, the
electric color-block design engine, drift + taboo, and the droplet ops with
self-healing.

**Planned:** the surveyor's *listening* half — actually hearing the music
(headless Suno ingestion → MERT/CLAP audio embeddings → trend-as-drift in
embedding space → audio-derived fragments to the ledger). The web/text
perception is the reporting beat; the audio is the differentiator, and the
bench for it has already passed.

---

*MOLD is grown, not written. The theme precipitates from a public ledger;
the Namer titles it last; nobody chooses it.*
