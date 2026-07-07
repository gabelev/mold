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

# Full pipeline: planning -> authors -> editor -> design -> verify -> publish.
# MOLD_PROMOTE=1 (in /etc/mold/mold.env) also fast-forwards prod.
"$UV" run python -m mold.run_issue

# Push so Vercel deploys: qa = preview, prod = production.
git -C "$MOLD_ROOT/terrarium" push --quiet origin qa || { echo "qa push failed"; exit 1; }
if [ "${MOLD_PROMOTE:-0}" = "1" ]; then
  git -C "$MOLD_ROOT/terrarium" push --quiet origin prod || { echo "prod push failed"; exit 1; }
fi

echo "issue run complete"
