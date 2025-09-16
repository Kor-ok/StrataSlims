# StrataSlims Discord Music Bot

StrataSlims is a Python Discord bot that integrates with the Suno AI API to generate music from user prompts. It runs as a lightweight bot remotely on a VM and can dynamically hand off operation to a locally running bot that offers heavier (GPU-based) features. Only one bot instance should be logged in to Discord at a time.

- Remote: Thin, reliable, always-on presence on a small VM (e2-micro). Auto-updates, health checks, and control API.
- Local: Heavier features (e.g., GPU-assisted workflows) on your workstation/laptop when needed. Use the control API to stop the remote bot before starting the local one, then switch back after the task finishes.

The bot presence shows “watching remotely” on the VM and “watching locally” on the workstation to indicate where it’s running.

Key components:
- Runner and preflight checks: [main.py](../main.py)
- Discord bot startup: [bot/run.py](../bot/run.py)
- Music generation flow and UI: [bot/gen_music.py](../bot/gen_music.py), [bot/musicparser.py](../bot/musicparser.py), [bot/sunoapi.py](../bot/sunoapi.py), [bot/post_songs.py](../bot/post_songs.py)
- Control API for start/stop/restart/status: [flaskserver.py](../flaskserver.py)
- System services and scripts: [server/systemd/strataslims.service](../server/systemd/strataslims.service), [server/systemd/strataslims-control.service](../server/systemd/strataslims-control.service), [server/run_with_update.sh](../server/run_with_update.sh), [server/notify_preemption.py](../server/notify_preemption.py), [server/install_systemd.sh](../server/install_systemd.sh)
- MCP server: [mcp/mcp_server.py](../mcp/mcp_server.py), [mcp/mcp.json](../mcp/mcp.json), tests: [mcp/test_setup.py](../mcp/test_setup.py)

Always reference these instructions first and fall back to search/shell only when you encounter unexpected info that does not match here.

## Working Effectively

### Bootstrap and Environment Setup
- Create and activate a venv:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
  - `pip install --upgrade pip`
- Install dependencies:
  - `pip install -r requirements.txt` (takes ~30–60s; NEVER CANCEL)
  - Network issues: `pip install --timeout=300 --retries=3 -r requirements.txt`
  - If persistent timeouts, focus on syntax checks and document that full dependency testing requires network
- Verify:
  - `python -m py_compile *.py bot/*.py mcp/*.py server/*.py`
  - `python main.py healthcheck` should complete preflight (requires network/env)

### Development Tools
- Lint (avoid adding new violations):
  - `pip install flake8`
  - `flake8 --max-line-length=100 --ignore=E501 <changed_files>`

## Running and Handoff

### Environment Variables
Recommended `.env` (minimally for remote run):
```
DISCORD_BOT_TOKEN=...
TEST_GUILD_ID=...
GREENLIST=123,456
SUNO_API_KEY=...
WEBHOOK_BOT=https://discord.com/api/webhooks/...
WEBHOOK_SEND_TO=https://discord.com/api/webhooks/...

# Presence and control
LOCALHOST=your-local-hostname
FLASK_SHUTDOWN_TOKEN=strong-token

# Optional alerting (preemption / logs)
PREEMPTION_ALERT_CHANNEL_ID=...
PREEMPTION_WEBHOOK=https://discord.com/api/webhooks/...
BOT_LOGS_CHANNEL_ID=...
BOT_LOGS_WEBHOOK=https://discord.com/api/webhooks/...

# Control API bind (control service)
FLASK_BIND=127.0.0.1
FLASK_PORT=8787
```

Notes:
- Presence is set by comparing `socket.gethostname()` with `LOCALHOST` in [`config.get_is_localhost`](../config.py). If equal, the status shows “locally”; otherwise “remotely”.
- Main runner validates env and network before starting the bot ([main.py](../main.py)).

### Local Run (workstation, for GPU-heavy workflows)
- Ensure the remote bot is stopped (see “Remote control API” below).
- Activate venv, then:
  - `python main.py` (default command “run”)
- The presence should show “watching locally”.

### Remote VM Run (thin, always-on)
- Use systemd services:
  - Install: `sudo server/install_systemd.sh`
  - Services:
    - Bot: [server/systemd/strataslims.service](../server/systemd/strataslims.service)
    - Control API: [server/systemd/strataslims-control.service](../server/systemd/strataslims-control.service)
- The bot is launched through [server/run_with_update.sh](../server/run_with_update.sh), which:
  - `git pull` on startup
  - Installs requirements if changed (best effort with timeouts)
  - Executes `python main.py run`
- Optional preemption notify is called on stop via [server/notify_preemption.py](../server/notify_preemption.py).

### Remote Control API (start/stop/restart/status)
A lightweight Flask server ([flaskserver.py](../flaskserver.py)) runs as a separate service and controls the bot via `systemctl`. It requires `FLASK_SHUTDOWN_TOKEN` if set.

- Status:
  - `curl -s http://127.0.0.1:8787/status -H "Authorization: Bearer <token>"`
- Stop remote (before starting local):
  - `curl -X POST http://127.0.0.1:8787/stopbot -H "Authorization: Bearer <token>"`
- Start remote (after finishing local):
  - `curl -X POST http://127.0.0.1:8787/startbot -H "Authorization: Bearer <token>"`
- Restart:
  - `curl -X POST http://127.0.0.1:8787/restartbot -H "Authorization: Bearer <token>"`

By default, the control API binds to `127.0.0.1`. Expose it cautiously if you need remote access (firewall + strong token).

### Handoff Pattern
- Normal operation: remote VM stays online (“watching remotely”).
- When you need GPU features locally:
  1. Stop the remote bot via `/stopbot`.
  2. Start the local bot (`python main.py`) and verify presence (“watching locally”).
  3. Complete heavy tasks.
  4. Stop local bot.
  5. Start the remote bot via `/startbot`.
- Never run both simultaneously with the same Discord token.

## Validation

### Basic Validation Steps
- `python -m py_compile *.py bot/*.py mcp/*.py server/*.py`
- `python main.py healthcheck` (preflight only)
- `flake8 --max-line-length=100 --ignore=E501 <changed_files>`

### Manual Testing
- With dependencies installed:
  - `python -c "from config import get_bot_token; print('Config OK')"`
  - `python -c "import bot.run; print('Bot import OK')"` (will attempt to start; prefer using main.py)
- Syntax-only (no network):
  - `python -m py_compile *.py bot/*.py mcp/*.py server/*.py`

## Key Files and Responsibilities
- Runner and preflight: [main.py](../main.py)
- Discord client and command tree: [bot/run.py](../bot/run.py)
- Music generation and UI flow: [bot/gen_music.py](../bot/gen_music.py)
- Payload building and validation: [bot/musicparser.py](../bot/musicparser.py)
- Suno API integration: [bot/sunoapi.py](../bot/sunoapi.py)
- Audio upload helper: [bot/post_songs.py](../bot/post_songs.py)
- Control API (systemctl bridge): [flaskserver.py](../flaskserver.py)
- Systemd units: [server/systemd/strataslims.service](../server/systemd/strataslims.service), [server/systemd/strataslims-control.service](../server/systemd/strataslims-control.service)
- Auto-update runner: [server/run_with_update.sh](../server/run_with_update.sh)
- Preemption notification: [server/notify_preemption.py](../server/notify_preemption.py)
- MCP server and config: [mcp/mcp_server.py](../mcp/mcp_server.py), [mcp/mcp.json](../mcp/mcp.json)

## Dependencies (requirements.txt)
Core:
- discord-py==2.6.3, aiohttp==3.12.15, requests==2.32.5
- flask==3.1.2, werkzeug==3.1.3
- python-dotenv==1.1.1
- And supporting libs listed in [requirements.txt](../requirements.txt)

Python ≥ 3.9 (tested up to 3.12). Check with `python3 --version`.

## Hosting Notes
- Target: Google Compute Engine e2-micro (2 vCPU, 1 GB RAM), debian-12
- Keep memory footprint low; avoid heavy processes on VM
- Use swap if needed; prefer systemd; supervisor config is available as an alternative: [server/strataslims.conf](../server/strataslims.conf)
- Pip install on low-RAM VMs may need `--no-cache-dir` and extended timeouts

## Time Expectations
- venv creation: ~3s
- Dependencies: 30–60s (up to 10m with network issues)
- Preflight checks: <5s
- Lint (changed files): ~10s