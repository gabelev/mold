# mold ops — running the zine on its own droplet

Mold runs unattended on a single droplet under systemd. The brief's shape:

```
systemd timer → orchestrator → ledger/theme → masthead → publish → GitHub → Vercel
```

## Layout on the droplet

```
/opt/mold/
  ensemble/     framework checkout
  mold/         instance checkout (this repo)
  terrarium/    content checkout (agents commit + push here)
/etc/mold/mold.env    environment (secrets, paths) — mode 0600
```

## Units

| unit | what | when |
|---|---|---|
| `mold-issue.service` + `.timer` | the weekly issue pipeline (oneshot) | Mon 06:00 UTC |
| `mold-ledger.service` + `.timer` | the daily ledger drop (surveyor beat) | daily 09:00 UTC |
| `mold-health.service` + `.timer` | health check: repos, disk, staleness | every 30 min |
| `mold-heal@.service` | on-failure handler for any of the above | on failure |

## Healing model

Three layers, cheapest first:

1. **systemd retries.** Oneshot pipeline runs get `Restart=on-failure` +
   `RestartSec` backoff via the service unit; transient failures (network,
   model API blips) heal themselves.
2. **`OnFailure=` escalation.** If a unit still fails after retries, systemd
   triggers `mold-heal@<unit>.service`, which runs `heal.sh`: reset the working
   trees to a clean state (git is our transaction log — a half-finished issue
   is just an uncommitted tree or an unpushed qa branch, both safely
   resettable), then re-kicks the failed unit once. A marker file prevents
   heal-loops; if the re-kick also fails, it stops and notifies.
3. **Staleness watchdog.** `healthcheck.sh` (on the half-hour timer) alerts if
   terrarium's last issue commit is older than 8 days — the "everything looks
   green but nothing shipped" failure that retries can't see.

Notifications go to `MOLD_NOTIFY_URL` (any webhook — ntfy, Slack, etc.) if set;
otherwise they land in the journal (`journalctl -u 'mold-*'`).

## Install (fresh droplet)

```bash
curl -fsSL https://raw.githubusercontent.com/gabelev/mold/main/ops/install.sh | sudo bash
# then: edit /etc/mold/mold.env, then:
sudo systemctl enable --now mold-issue.timer mold-ledger.timer mold-health.timer
```

Or from a checkout: `sudo ./ops/install.sh`.

Dry-run the pipeline manually any time:

```bash
sudo systemctl start mold-issue.service   # or: sudo -u mold /opt/mold/mold/ops/run-issue.sh
```
