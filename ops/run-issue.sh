#!/usr/bin/env bash
# Run the weekly issue pipeline. Invoked by mold-issue.service.
# Exit nonzero on any failure so systemd's Restart/OnFailure machinery engages.
set -euo pipefail

MOLD_ROOT=${MOLD_ROOT:-/opt/mold}
UV=${UV:-$HOME/.local/bin/uv}

cd "$MOLD_ROOT/mold"

# Fresh code + clean content tree before a run. The content repo must be clean:
# a dirty tree means a previous run died mid-publish — heal.sh handles that.
git -C "$MOLD_ROOT/terrarium" diff --quiet || { echo "terrarium tree dirty; refusing to run (heal first)"; exit 75; }
git -C "$MOLD_ROOT/terrarium" fetch --quiet origin || true

# The pipeline entrypoint. For now this is the vertical slice; it becomes
# `python -m mold.run_issue` as stages (design/verify/deploy) land.
"$UV" run python -m mold.slice

# Push the qa branch so Vercel builds the preview.
git -C "$MOLD_ROOT/terrarium" push --quiet origin qa || { echo "push failed"; exit 1; }

echo "issue run complete"
