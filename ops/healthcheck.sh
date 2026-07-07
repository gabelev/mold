#!/usr/bin/env bash
# Health check for the Mold droplet. Invoked by mold-health.timer (every 30m).
# Checks the failures retries can't see. Exit nonzero -> mold-heal@ fires.
set -uo pipefail

MOLD_ROOT=${MOLD_ROOT:-/opt/mold}
MOLD_STALE_HOURS=${MOLD_STALE_HOURS:-192}
FAILED=0

note() { echo "[health] $*"; }
fail() { echo "[health] FAIL: $*"; FAILED=1; }

# 1. Repos present and readable.
for repo in ensemble mold terrarium; do
  [ -d "$MOLD_ROOT/$repo/.git" ] || fail "missing repo: $repo"
done

# 2. Disk space (fail under 1 GiB free).
avail_kb=$(df --output=avail "$MOLD_ROOT" | tail -1 | tr -d ' ')
if [ "${avail_kb:-0}" -lt 1048576 ]; then
  fail "low disk: ${avail_kb}KB free on $MOLD_ROOT"
fi

# 3. Terrarium tree clean (a dirty tree = a run died mid-publish).
if ! git -C "$MOLD_ROOT/terrarium" diff --quiet 2>/dev/null; then
  fail "terrarium working tree dirty"
fi

# 4. Staleness watchdog: the "all green but nothing shipped" failure.
#    Alert if the newest commit on any branch of terrarium is too old.
last_commit=$(git -C "$MOLD_ROOT/terrarium" log --all --format=%ct -1 2>/dev/null || echo 0)
now=$(date +%s)
age_hours=$(( (now - last_commit) / 3600 ))
if [ "$last_commit" -eq 0 ]; then
  fail "cannot read terrarium history"
elif [ "$age_hours" -gt "$MOLD_STALE_HOURS" ]; then
  fail "terrarium stale: last commit ${age_hours}h ago (threshold ${MOLD_STALE_HOURS}h)"
else
  note "terrarium fresh: last commit ${age_hours}h ago"
fi

# 5. Recent unit failures.
for unit in mold-issue.service mold-ledger.service; do
  if systemctl is-failed --quiet "$unit" 2>/dev/null; then
    fail "unit in failed state: $unit"
  fi
done

if [ "$FAILED" -eq 0 ]; then
  note "all checks passed"
fi
exit "$FAILED"
