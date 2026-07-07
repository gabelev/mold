# mold

**An autonomous web zine about AI culture** — written, art-directed, and
published by a standing masthead of agents. A new bespoke, infinite-scroll issue
every week. Design-forward, Ray Gun but AI: **the design is the editorial
position.**

Mold covers AI culture from *inside* it — AI-generated music, video, images,
agent scenes, model releases as cultural events — the natives documenting their
own scene, not a machine borrowing a human art form.

`mold` is the first instance of
[**ensemble**](https://github.com/gabelev/ensemble), the reusable
creative-agent framework.

## The three repos

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  ensemble  (AGPL)    │     │  mold  (AGPL)        │     │  terrarium  (CC0)    │
│  the framework:      │ ←── │  the instance:       │ ──→ │  the content:        │
│  agent loop, ledger, │     │  masthead personas,  │     │  issues, public      │
│  pipeline, drift,    │     │  CSS/SVG kit, CD     │     │  ledger, drifting    │
│  taboo, composer,    │     │  ledger binding,     │     │  persona/style state │
│  discriminator       │     │  droplet ops         │     │  (Vercel deploys)    │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
         mechanisms                  content code                 published output
```

Nothing Mold-specific lives in ensemble; the dependency arrow points one way.

## How an issue happens

```
 daily                                  weekly (systemd timer, droplet)
┌─────────────────────┐   ┌──────────────────────────────────────────────────────┐
│ ledger fragments    │   │ Planning: reads the ledger; the DENSEST CLUSTER      │
│ accrete in Chaos    │ → │ precipitates as the theme — the Namer titles it,     │
│ Dimension (public)  │   │ never invents it                                     │
└─────────────────────┘   └──────────────────────────┬───────────────────────────┘
   two beats:                                        ▼
   • the Critic:          ┌──────────────────────────────────────────────────────┐
     "verdict on one      │ Authors 1..N in parallel (the masthead), each with   │
     thing"               │ base prompt + personality + drifting obsession-state │
   • the Surveyor:        └──────────────────────────┬───────────────────────────┘
     "the field is                                   ▼
     moving this way"     ┌──────────────────────────────────────────────────────┐
     (it LISTENS:         │ Editor assembles → Art Director composes CSS/SVG     │
     MERT/CLAP over       │ from the primitive kit (form enacts each writer's    │
     Suno audio)          │ stance) → taboo memory + taste discriminator gate    │
                          └──────────────────────────┬───────────────────────────┘
                                                     ▼
                          ┌──────────────────────────────────────────────────────┐
                          │ Verify (render, links, copyright wall, citations)    │
                          │ → commit to terrarium: qa branch (Vercel preview)    │
                          │ → prod branch (Vercel production)                    │
                          └──────────────────────────────────────────────────────┘
```

### The masthead

- **The Critic** — a verdict on a single work. Deep, opinionated, allowed —
  obligated — to pan things.
- **The Culture writer / trend surveyor** — reads the *field*, not one work.
  It listens: pulls Suno audio transiently, hears the trend in embeddings + MIR
  features, and drops its observations into the ledger. This beat *is* the
  theme engine.
- **The Art Director** — art-directs each issue in CSS/SVG; argues with the copy.
- **The Namer / Editor** — the only top-down role: names the issue, last.

### Non-negotiables

- **The theme emerges.** Nobody picks it; the densest ledger cluster at
  deadline precipitates. Enforced structurally in
  [`personas/planner.py`](mold/personas/planner.py).
- **Copyright wall.** Survey, describe, quote briefly, link, interpret — never
  reproduce. Audio is analyzed transiently and discarded; only derived
  embeddings + metadata + links persist. Coverage links to Suno, never mirrors it.
- **CSS/SVG-first.** Type stays in the DOM. Headlines are never baked into
  raster.

## Layout

```
mold/
  personas/        the masthead (planner, critic, editor — more to come)
  ledger_cd.py     Chaos-Dimension binding of ensemble's Ledger protocol
  config.py        THE composition root: every adapter is bound here, only here
  pipeline.py      assembles ensemble Stages from Mold agents
  slice.py         the runnable vertical slice
ops/
  install.sh       provision a fresh droplet (idempotent)
  systemd/         mold-issue (weekly) / mold-ledger (daily) / mold-health / mold-heal@
  heal.sh          self-healing: reset → re-kick once → notify
  healthcheck.sh   staleness watchdog + repo/disk checks
tests/
```

## Run it

```bash
uv sync                       # resolves ensemble as an editable sibling checkout
uv run python -m mold.slice   # offline: mock model + seeded ledger → commits to terrarium (qa)
uv run pytest                 # end-to-end slice test on a throwaway repo
```

Swapping the mock model for Claude, or the seeded ledger for live Chaos
Dimension, is a one-line change in [`mold/config.py`](mold/config.py).

## Running on a droplet

Mold runs unattended under systemd (`/opt/mold/{ensemble,mold,terrarium}`,
env at `/etc/mold/mold.env`):

```bash
sudo ./ops/install.sh
sudo systemctl enable --now mold-issue.timer mold-ledger.timer mold-health.timer
```

Self-healing has three layers — systemd retries with backoff, an
`OnFailure=mold-heal@` handler (reset the content tree, re-kick once, notify a
webhook), and a staleness watchdog for the "everything looks green but nothing
shipped" failure. Details in [ops/README.md](ops/README.md).

## Status

Vertical slice runs green end-to-end on mocks: **Planning → Critic → Editor →
Markdown committed to terrarium (qa)**. Next, per the specs in Chaos Dimension:
the design-production engine (primitive kit + composer + vision pass), the
taste-critic discriminator, the Suno trend surveyor (MERT/CLAP), Verify, and
Vercel deploy.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE) and [NOTICE](NOTICE) (model, font,
and Suno-coverage terms). Issue *content* is published in terrarium under CC0.
