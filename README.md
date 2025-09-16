# StrataSlims Discord Music Bot

StrataSlims is a Python Discord bot that integrates with the Suno AI API to generate music from user prompts. It runs as a lightweight bot remotely on a VM and can dynamically hand off operation to a locally running bot that offers heavier (GPU‑based) features. Only one bot instance should be logged in to Discord at a time.

- Remote: Thin, reliable, always‑on presence on a small VM (e2‑micro). Auto‑updates, health checks, and a control API.
- Local: Heavier features (e.g., GPU‑assisted workflows) on your workstation/laptop when needed. Use the control API to stop the remote bot before starting the local one, then switch back after the task finishes.

The bot presence shows “watching remotely” on the VM and “watching locally” on your workstation to indicate where it’s running.

## Features

- 🎵 Music generation via Suno AI
- 🤖 Discord slash command with rich UI (details modal, extras modal, channel selector, buttons)
- ✨ Style Boost flow (refines a provided style before generation)
- 💰 Credit display and background polling for status
- 🔧 Control API to start/stop/restart the bot service on the VM
- � Safe remote/local handoff pattern with presence indicator
- 🔌 Optional MCP server for integrations

## Prerequisites

- Python 3.9 or higher
- Discord bot token and permissions in your server (Send Messages, Use Slash Commands, Embed Links, Attach Files)
- Suno AI API access and key
- For remote hosting: a small Linux VM (e.g., Debian 12 on GCE e2‑micro)

## Quick Start

Create a virtual environment and install dependencies.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` in the repo root (see Environment Variables below), then validate:

```powershell
python -m py_compile *.py bot/*.py mcp/*.py server/*.py
python .\main.py healthcheck
```

Run locally:

```powershell
python .\main.py
```

You should see the bot presence as “watching locally”. Use the `/music` command in Discord.

## Environment Variables

Recommended `.env` (minimally for remote run):

```env
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

- Presence is set by comparing `socket.gethostname()` with `LOCALHOST` in `config.get_is_localhost`. If equal, the status shows “locally”; otherwise “remotely”.
- The main runner performs preflight checks (env + basic network) before starting the bot.

## Running (Remote VM)

On the VM, use the provided systemd units and auto‑update runner.

1. Install systemd services (as root):

```bash
sudo server/install_systemd.sh
```

2. Services:

- Bot: `server/systemd/strataslims.service` → launches `server/run_with_update.sh`, which performs `git pull`, installs updated requirements (best‑effort), then runs `python main.py run`.
- Control API: `server/systemd/strataslims-control.service` → serves the control HTTP API from `flaskserver.py`.

The VM bot presence will show “watching remotely”.

## Remote Control API (start/stop/restart/status)

The lightweight Flask server (`flaskserver.py`) runs separately and controls the bot via `systemctl`. If `FLASK_SHUTDOWN_TOKEN` is set, include it as a Bearer token.

Examples (Linux/macOS):

```bash
curl -s http://127.0.0.1:8787/status -H "Authorization: Bearer <token>"
curl -X POST http://127.0.0.1:8787/stopbot -H "Authorization: Bearer <token>"
curl -X POST http://127.0.0.1:8787/startbot -H "Authorization: Bearer <token>"
curl -X POST http://127.0.0.1:8787/restartbot -H "Authorization: Bearer <token>"
```

Windows PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8787/status" -Headers @{ Authorization = "Bearer <token>" }
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8787/stopbot" -Headers @{ Authorization = "Bearer <token>" }
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8787/startbot" -Headers @{ Authorization = "Bearer <token>" }
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8787/restartbot" -Headers @{ Authorization = "Bearer <token>" }
```

By default the control API binds to `127.0.0.1`. Expose carefully if needed (firewall + strong token).

## Handoff Pattern (Remote ↔ Local)

- Normal operation: keep the remote VM online (“watching remotely”).
- When you need GPU‑heavy features locally:
   1. Stop the remote bot via the control API `/stopbot`.
   2. Start the local bot (`python main.py`) and verify presence (“watching locally”).
   3. Complete heavy tasks.
   4. Stop the local bot.
   5. Start the remote bot via `/startbot`.
- Never run both simultaneously with the same Discord token.

## Using the Bot

- Command: `/music`
Flow:

- Open Details to provide Title, Style, and Lyrics.
- Optionally open Extras to set Vocalist Gender, Negative Tags, and numeric weights.
- Optionally use Boost Style to refine your style text.
- Choose a channel to post results to (defaults to the invoking channel).
- Submit to begin generation. The bot posts progress and final audio files to the selected channel.

## MCP (Optional)

The MCP server and config live under `mcp/`.

Run the server:

```powershell
python .\mcp\mcp_server.py
```

Client configuration example (`mcp/mcp.json`):

```json
{
   "mcpServers": {
      "strataslims": {
         "command": "python",
         "args": ["mcp_server.py"],
         "env": { "PYTHONPATH": "." }
      }
   }
}
```

## Project Structure (key files)

```text
StrataSlims/
├── main.py                     # Runner, preflight, graceful shutdown hooks
├── config.py                   # Env loader, presence detection, routes
├── flaskserver.py              # Control API (systemctl bridge)
├── bot/
│   ├── run.py                  # Discord client and command tree (/music)
│   ├── gen_music.py            # UI flow, buttons, background tasks
│   ├── musicparser.py          # Payload building & validation helpers
│   ├── sunoapi.py              # Suno API integration
│   └── post_songs.py           # Download and attach audio files
├── mcp/
│   ├── mcp_server.py           # MCP server
│   └── mcp.json                # MCP client configuration example
└── server/
      ├── run_with_update.sh      # Auto‑update then run main.py
      ├── notify_preemption.py    # Optional shutdown/preemption notify
      ├── install_systemd.sh      # Install systemd units
      └── systemd/
            ├── strataslims.service
            └── strataslims-control.service
```

## Validation & Development

Basic validation:

```powershell
python -m py_compile *.py bot/*.py mcp/*.py server/*.py
python .\main.py healthcheck
```

Lint changed files (optional):

```powershell
pip install flake8
flake8 --max-line-length=100 --ignore=E501 <changed_files>
```

## Hosting Notes

- Target: Google Compute Engine e2‑micro (2 vCPU, 1 GB RAM), Debian 12
- Keep memory footprint low on the VM; avoid heavy processes there
- Pip installs on low‑RAM VMs may need longer timeouts or `--no-cache-dir`

## Troubleshooting

### Bot not responding

- Verify `DISCORD_BOT_TOKEN` and permissions
- Check that only one bot instance is running (remote vs local)
- Run `python main.py healthcheck` to validate env/network

### Music generation errors

- Verify `SUNO_API_KEY` and remaining credits
- Check the style/lyrics length thresholds

### Control API errors

- Ensure the control service is running and token matches
- Confirm it binds to the expected interface/port

## License

MIT — see `LICENSE`.

## Support

- Open an issue: <https://github.com/Kor-ok/StrataSlims/issues>
- Review this README and comments in the source files
