#!/usr/bin/env bash
# Provision a fresh droplet to run Mold unattended.
# Idempotent: safe to re-run for upgrades.
set -euo pipefail

MOLD_ROOT=/opt/mold
MOLD_USER=mold
REPOS=(ensemble mold terrarium)
GITHUB_OWNER=${GITHUB_OWNER:-gabelev}

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }

echo "==> packages"
apt-get update -qq
apt-get install -y -qq git curl python3 >/dev/null

echo "==> user + dirs"
id -u "$MOLD_USER" >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/$MOLD_USER --shell /bin/bash "$MOLD_USER"
mkdir -p "$MOLD_ROOT" /etc/mold /var/lib/mold
chown "$MOLD_USER:$MOLD_USER" "$MOLD_ROOT" /var/lib/mold

echo "==> uv (per-user, as $MOLD_USER)"
sudo -u "$MOLD_USER" bash -c 'command -v ~/.local/bin/uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -q'

echo "==> repos"
for repo in "${REPOS[@]}"; do
  if [ -d "$MOLD_ROOT/$repo/.git" ]; then
    sudo -u "$MOLD_USER" git -C "$MOLD_ROOT/$repo" pull --ff-only
  else
    sudo -u "$MOLD_USER" git clone "git@github.com:$GITHUB_OWNER/$repo.git" "$MOLD_ROOT/$repo"
  fi
done

echo "==> python deps"
sudo -u "$MOLD_USER" bash -c "cd $MOLD_ROOT/mold && ~/.local/bin/uv sync"

echo "==> env file"
if [ ! -f /etc/mold/mold.env ]; then
  install -m 0600 -o "$MOLD_USER" -g "$MOLD_USER" "$MOLD_ROOT/mold/ops/mold.env.example" /etc/mold/mold.env
  echo "    NOTE: edit /etc/mold/mold.env (API keys, notify URL) before enabling timers"
fi

echo "==> systemd units"
install -m 0644 "$MOLD_ROOT"/mold/ops/systemd/*.service "$MOLD_ROOT"/mold/ops/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload

echo "==> done. enable with:"
echo "    systemctl enable --now mold-issue.timer mold-ledger.timer mold-health.timer"
