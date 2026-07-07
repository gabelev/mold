#!/usr/bin/env bash
# Daily ledger drop: the surveyor beat. Invoked by mold-ledger.service.
#
# STATUS: placeholder until the Suno surveyor lands. It still exercises the
# full unit/heal path (env, uv, repo access) so the ops machinery is proven
# before the surveyor exists — when `python -m mold.survey` ships, swap it in.
set -euo pipefail

MOLD_ROOT=${MOLD_ROOT:-/opt/mold}
UV=${UV:-$HOME/.local/bin/uv}

cd "$MOLD_ROOT/mold"

# TODO(surveyor): replace with `"$UV" run python -m mold.survey`
"$UV" run python -c "import mold, ensemble; print('ledger heartbeat ok:', mold.__version__, ensemble.__version__)"

echo "ledger run complete"
