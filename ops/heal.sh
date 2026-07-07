#!/usr/bin/env bash
# Healing handler. Invoked by mold-heal@<failed-unit>.service.
#
# Strategy: git is the transaction log. A half-finished issue is an uncommitted
# working tree or an unpushed branch — both safely resettable. So healing is:
#   1. notify (if MOLD_NOTIFY_URL set)
#   2. reset the terrarium working tree to a clean state
#   3. re-kick the failed unit ONCE (marker file prevents heal-loops)
set -uo pipefail

FAILED_UNIT=${1:-unknown}
MOLD_ROOT=${MOLD_ROOT:-/opt/mold}
STATE_DIR=${MOLD_STATE_DIR:-/var/lib/mold}
MARKER="$STATE_DIR/heal-$FAILED_UNIT.marker"

log() { echo "[heal:$FAILED_UNIT] $*"; }

notify() {
  local msg="$1"
  log "$msg"
  if [ -n "${MOLD_NOTIFY_URL:-}" ]; then
    curl -fsS -m 10 -d "mold: $msg" "$MOLD_NOTIFY_URL" >/dev/null 2>&1 || log "notify failed (webhook unreachable)"
  fi
}

mkdir -p "$STATE_DIR"

# --- 1. Reset content repo to a clean state -----------------------------------
# Uncommitted changes are a dead run's debris; committed-but-unpushed work on qa
# is preserved (push is retried by the re-kicked run).
if [ -d "$MOLD_ROOT/terrarium/.git" ]; then
  if ! git -C "$MOLD_ROOT/terrarium" diff --quiet 2>/dev/null; then
    log "resetting dirty terrarium tree"
    git -C "$MOLD_ROOT/terrarium" reset --hard --quiet
    git -C "$MOLD_ROOT/terrarium" clean -fdq
  fi
fi

# --- 2. Re-kick once, with a loop guard ---------------------------------------
# Marker expires after 6h so tomorrow's genuine failure can heal again.
if [ -f "$MARKER" ] && [ $(( $(date +%s) - $(stat -c %Y "$MARKER") )) -lt 21600 ]; then
  notify "unit $FAILED_UNIT failed AGAIN after a heal re-kick — human needed. journalctl -u $FAILED_UNIT"
  exit 0   # do not loop; the notification is the output
fi

case "$FAILED_UNIT" in
  mold-issue.service|mold-ledger.service)
    touch "$MARKER"
    notify "unit $FAILED_UNIT failed; tree reset, re-kicking once"
    systemctl start "$FAILED_UNIT" --no-block
    ;;
  mold-health.service)
    # Health failures are diagnostics, not crashes: notify, don't re-kick.
    notify "health check failed — see journalctl -u mold-health.service"
    ;;
  *)
    notify "unknown unit failed: $FAILED_UNIT"
    ;;
esac
