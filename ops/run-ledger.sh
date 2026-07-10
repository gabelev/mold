#!/usr/bin/env bash
# Daily ledger drop: the surveyor's web-search beat. Invoked by mold-ledger.service.
#
# Runs PERCEIVE's broad scan and appends fresh dated/sourced fragments to the
# Chaos Dimension ledger (needs CD_AGENT_TOKEN; a no-op without one). The audio
# surveyor (Suno/MERT, Phase 1) becomes a second adapter feeding the same drop.
set -euo pipefail

MOLD_ROOT=${MOLD_ROOT:-/opt/mold}
UV=${UV:-$HOME/.local/bin/uv}

cd "$MOLD_ROOT/mold"

"$UV" run python -m mold.survey

echo "ledger run complete"
