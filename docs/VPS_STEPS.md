# VPS Deploy Runbook — paper-mode 24/7 on Hostinger

> ✅ **DEPLOYED 2026-06-11 — see `CLAUDE.md` → "Live Ops".** Claude Code runs *on*
> this VPS, so deploy was **local (no SSH)**, running in place from
> `/root/claude/projects/alien-trade`. Steps 1 & 3 below (clone + scp secrets) were
> unnecessary. Live now: `alien-trade.service` (24/7 paper), `alien-cockpit.service`
> (UI :4173), `alien-digest.timer` (hourly Telegram). The SSH-based steps below are
> kept for reference / a from-scratch redeploy on a *different* box.

> Resume point for Task 8 (deploy to VPS). Self-contained: every fact needed is here.
> Goal: run the agent in **paper mode** 24/7 on the VPS, writing to the live Convex
> bus so the cockpit shows decisions/log/👍👎, gathering the 8-day testnet corpus.

## Facts (verified 2026-06-11)

- **VPS:** `root@76.13.243.12` — Ubuntu 24.04.3, 16 GB RAM, 4 CPU, 152 GB free.
- **SSH:** passwordless key auth **already works** (your `~/.ssh/id_ed25519` public key is
  in the VPS `authorized_keys`). Test: `ssh root@76.13.243.12 whoami` → `root`, no prompt.
- **Installed on VPS:** Python 3.12.3, git, docker. **Missing:** `uv`, `bun` (we install `uv`).
- **Repo:** `git@github.com:the-niresh/alien-trade.git` (latest pushed commit includes
  autopilot + registry + event-intel + feedback loop).
- **Convex:** already deployed to `festive-newt-1` (schema clean after clearing the old
  `decisions` rows). The VPS does NOT run Convex — it just writes to the cloud via
  `CONVEX_URL`, and the cockpit reads the same deployment.
- **Run model:** run from the **repo root** with the **`core/.venv`** Python. Core is
  installed editable so `backtest/strategy/risk/...` import; `agent.*` resolves from cwd.
- **Runtime CLI** (`agent/runtime.py`): `--mode paper|testnet|mainnet`, `--symbol ETH`,
  `--cycles N` (run N then stop; omit → `run_forever` at 1h cadence), `--replay`,
  `--dry-run`, `--recover`, `--activity-floor`. Config also via env (below) + live cockpit.

---

## Step 1 — Get the code onto the VPS

The repo is private, so use a **deploy key** (one-time). Run on the VPS:

```bash
ssh root@76.13.243.12
# on the VPS:
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "vps-deploy"
cat ~/.ssh/id_ed25519.pub        # copy this line
```

Then add that public key to GitHub: **repo → Settings → Deploy keys → Add deploy key**
(read-only is fine). Back on the VPS:

```bash
ssh -o StrictHostKeyChecking=accept-new git@github.com   # accept GitHub host key (says "successfully authenticated", then closes — that's fine)
git clone git@github.com:the-niresh/alien-trade.git /root/alien-trade
```

> If the repo is/becomes **public**, skip the deploy key and just:
> `git clone https://github.com/the-niresh/alien-trade.git /root/alien-trade`

## Step 2 — Install `uv` and build the venv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env          # puts uv on PATH for this shell
cd /root/alien-trade/core
uv venv                              # creates core/.venv (Python 3.12)
uv pip install -e .                  # installs core + runtime deps (numpy/polars/httpx/fastapi/...)
```

Smoke-test the imports (must print OK):

```bash
cd /root/alien-trade
core/.venv/bin/python -c "import backtest.engine, strategy.registry, risk.autopilot, risk.feedback; import agent.loop, agent.intel; print('imports OK')"
```

## Step 3 — Secrets: copy your local `.env.local` to the VPS  *(you run this)*

The agent reads `/root/alien-trade/.env.local` (CONVEX_URL, BRAVE_API_KEY, ANTHROPIC, etc.).
From your **Windows PowerShell**, copy your existing local secrets file up:

```powershell
scp "E:\Hackathon\cmc-bnb-twac\alien-trade\.env.local" root@76.13.243.12:/root/alien-trade/.env.local
```

Verify on the VPS that `CONVEX_URL` is set to the festive-newt deployment:

```bash
grep -E "CONVEX_URL|BRAVE_API_KEY" /root/alien-trade/.env.local
```

> Runtime *config* (strategy / autopilot) does NOT go in `.env.local` — it's set in the
> systemd unit (Step 5) and overridable live from the cockpit. `.env.local` stays secrets-only.

## Step 4 — One-shot verification (2 cycles, paper)

```bash
cd /root/alien-trade
SECOND_BRAIN=0 STRATEGY_NAME=contrarian core/.venv/bin/python -m agent.runtime --mode paper --symbol ETH --cycles 2
```

Expect a `run summary` (cycles/fills/equity/drawdown). Then open the **cockpit** and confirm a
couple of **decisions** rows + **log console** lines appeared (same Convex deployment).
`SECOND_BRAIN=0` avoids needing langgraph/anthropic/upstash for the first deploy.

## Step 5 — Install the 24/7 systemd service

Create `/etc/systemd/system/alien-trade.service` on the VPS:

```ini
[Unit]
Description=Alien-Trade paper runtime
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/root/alien-trade
Environment=SECOND_BRAIN=0
Environment=STRATEGY_NAME=contrarian
Environment=AUTOPILOT=1
Environment=AUTOPILOT_PROFIT_TARGET_PCT=0.05
Environment=AUTOPILOT_PROTECT_PRINCIPAL=1
Environment=AUTOPILOT_TRAIL_GIVEBACK_PCT=0.04
Environment=AUTOPILOT_BLOCK_REGIMES=crash,high_vol
ExecStart=/root/alien-trade/core/.venv/bin/python -m agent.runtime --mode paper --symbol ETH
Restart=always
RestartSec=10
StandardOutput=append:/var/log/alien-trade.log
StandardError=append:/var/log/alien-trade.log

[Install]
WantedBy=multi-user.target
```

Enable + start + watch:

```bash
systemctl daemon-reload
systemctl enable --now alien-trade
systemctl status alien-trade --no-pager
tail -f /var/log/alien-trade.log        # live logs; Ctrl-C to stop tailing
```

Cadence is 1 h (`cfg.cycle_seconds=3600`), aligned to the 1 h bars. A new decision row lands
each hour; the cockpit log console + decisions feed update live.

## Step 6 — Drive it from the cockpit

- **Strategy** picker + **Autopilot** panel: confirm `contrarian` + autopilot ON (or change live).
- **Risk caps** sliders: set conservative caps for the paper run.
- **👍/👎** on decisions: this is the human-feedback loop — a 👎 makes the agent avoid that
  setup next time (`core/risk/feedback.py`, blocks at net-2-bad, halves at net-1).
- **Live log console**: watch every cycle's audit line.

---

## Follow-ups (after it's running — not blockers)

1. **Event Intelligence is built + tested but not yet auto-invoked.** `agent/intel/EventIntel.scan()`
   needs a scheduled caller (a cron via Trigger.dev `jobs/`, or a `POST /intel/scan` endpoint on
   `agent/server.py` hit every ~30 min, or a thread in the loop). Wire one so Brave news risk-off
   actually fires during the run. Needs `BRAVE_API_KEY` in `.env.local` (you have a Brave key).
2. **Second Brain (Hermes reflections / co-pilot):** to enable, on the VPS
   `cd /root/alien-trade/core && uv pip install langgraph anthropic upstash-redis upstash-vector`
   then drop `SECOND_BRAIN=0` from the unit (set `=1`) and `systemctl restart alien-trade`.
   Needs ANTHROPIC + Upstash keys in `.env.local`.
3. **Updating the deploy after new commits:** `ssh root@76.13.243.12 'cd /root/alien-trade && git pull && systemctl restart alien-trade'`.
   If `core/pyproject.toml` changed: also `core/.venv/bin/python -m pip --version` … actually
   `cd core && uv pip install -e .` again.
4. **Telegram alerts:** set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env.local` to get
   equity-floor / kill-switch / daily-summary / autopilot-bank pings.
5. **Mainnet later:** only after paper looks good — switch the cockpit mode toggle to mainnet
   (double-confirm) once the wallet is funded + `twak compete register` is done (see STEPS.md
   COMPETITION COMPLIANCE). Paper proves the loop with zero capital first.

## Quick reference

```bash
ssh root@76.13.243.12                              # connect (passwordless)
systemctl status alien-trade --no-pager            # is it running?
tail -n 100 /var/log/alien-trade.log               # recent logs
systemctl restart alien-trade                      # restart after a git pull
journalctl -u alien-trade -n 50 --no-pager         # systemd-level logs if it won't start
```
