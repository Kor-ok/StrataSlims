#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from flask import Flask

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    # It's okay if python-dotenv isn't available; Supervisor/OS env may be enough.
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


# --- Logging setup ---------------------------------------------------------
def setup_logging() -> None:
    level_name = os.getenv("STRATASLIMS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Ensure unbuffered output when under Supervisor
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass


logger = logging.getLogger("strataslims.main")


# --- Preflight checks ------------------------------------------------------
REQUIRED_ENVS = [
    "DISCORD_BOT_TOKEN",
    "TEST_GUILD_ID",
    "GREENLIST",
    "SUNO_API_KEY",
    "WEBHOOK_BOT",
    "WEBHOOK_SEND_TO",
    "PREEMPTION_ALERT_CHANNEL_ID",
    "PREEMPTION_WEBHOOK",
    "LOCALHOST"
]


def load_environment(env_path: Path = Path(".env")) -> None:
    """Load environment variables from .env if present."""
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded environment from %s", env_path)
    else:
        logger.warning("No .env file found; relying on process environment.")


def validate_required_envs() -> List[str]:
    missing = [name for name in REQUIRED_ENVS if not os.getenv(name)]
    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
    else:
        logger.info("All required environment variables present.")
    return missing


def wait_for_network(hosts: Optional[List[Tuple[str, int]]] = None, timeout: float = 5.0, retries: int = 12, delay: float = 5.0) -> bool:
    """Wait for network endpoints to be reachable.

    Tries to connect to each (host, port) with a short timeout. Retries across all hosts
    a number of times. Returns True if at least one host becomes reachable; otherwise False.
    """
    if hosts is None:
        hosts = [("discord.com", 443), ("api.suno.ai", 443)]

    for attempt in range(1, retries + 1):
        for host, port in hosts:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    logger.info("Network reachable: %s:%d", host, port)
                    return True
            except OSError:
                continue
        logger.warning("Network not yet reachable (attempt %d/%d). Retrying in %.1fs...", attempt, retries, delay)
        time.sleep(delay)
    logger.error("Network remained unreachable after %d attempts.", retries)
    return False


# --- Graceful shutdown handling -------------------------------------------
_shutdown_initiated = False


def _graceful_shutdown_handler(signum, _frame):
    global _shutdown_initiated
    if _shutdown_initiated:
        return
    _shutdown_initiated = True
    logger.warning("Received signal %s; initiating graceful shutdown...", signum)

    # Attempt to notify and close the discord client if running (defined in bot.py as `client`).
    try:
        import bot  # type: ignore

        client = getattr(bot, "client", None)
        if client is not None:
            try:
                # Try to send a preemption notice quickly before closing
                try:
                    fut_notify = asyncio.run_coroutine_threadsafe(_send_preemption_notice(client), client.loop)  # type: ignore[attr-defined]
                    fut_notify.result(timeout=5)
                except Exception as ne:  # noqa: BLE001
                    logger.warning("Preemption notify failed or timed out: %s", ne)

                # Schedule close on the client's loop if possible
                fut = asyncio.run_coroutine_threadsafe(client.close(), client.loop)  # type: ignore[attr-defined]
                fut.result(timeout=15)
                logger.info("Discord client closed.")
            except Exception as e:  # noqa: BLE001
                logger.exception("Error closing Discord client: %s", e)
    except Exception:
        # bot may not be imported yet or client not created
        pass

    # Exit process; Supervisor will handle autorestart policy
    raise SystemExit(0)


def register_signal_handlers() -> None:
    try:
        signal.signal(signal.SIGTERM, _graceful_shutdown_handler)
        signal.signal(signal.SIGINT, _graceful_shutdown_handler)
    except Exception:
        # On some platforms signals may not be settable (e.g., Windows); ignore
        pass


async def _send_preemption_notice(client) -> None:
    """Send a preemption/shutdown notice to a configured channel if possible."""
    try:
        channel_id_raw = os.getenv("PREEMPTION_ALERT_CHANNEL_ID", "1414391162474598511")
        channel_id = int(channel_id_raw)
    except Exception:
        logger.debug("No valid PREEMPTION_ALERT_CHANNEL_ID set; skipping notify.")
        return

    try:
        from discord.abc import Messageable  # type: ignore

        channel = getattr(client, "get_channel")(channel_id)
        if channel is None:
            # Fallback to fetch if not in cache
            channel = await client.fetch_channel(channel_id)  # type: ignore[attr-defined]

        if channel is not None and isinstance(channel, Messageable):
            msg = "StrataSlims: VM preemption notice received. Preparing graceful shutdown..."
            await channel.send(msg)  # type: ignore[attr-defined]
            logger.info("Preemption notice sent to channel %s", channel_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to send preemption notice: %s", e)


# --- CLI / Entry point -----------------------------------------------------
def run_bot_module() -> int:
    """Import and run the bot module. bot.py starts the client at import time."""
    try:
        # Importing bot triggers client.run(...) per current implementation.
        from bot import run  # noqa: F401  # type: ignore
        return 0
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (KeyboardInterrupt).")
        return 0
    except ImportError as e:
        logger.error("Import error: %s", e)
        logger.error("Make sure dependencies are installed: pip install -r requirements.txt")
        return 2
    except Exception as e:  # noqa: BLE001
        logger.exception("Unhandled error starting bot: %s", e)
        return 1


def preflight() -> int:
    load_environment()
    missing = validate_required_envs()
    if missing:
        return 2
    if not wait_for_network(
        timeout=float(os.getenv("STRATASLIMS_NET_TIMEOUT", 5)),
        retries=int(os.getenv("STRATASLIMS_NET_RETRIES", 12)),
        delay=float(os.getenv("STRATASLIMS_NET_DELAY", 5)),
    ):
        return 3
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    setup_logging()
    register_signal_handlers()

    parser = argparse.ArgumentParser(description="StrataSlims Discord Bot runner")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "preflight", "healthcheck"], help="Action to perform")
    args = parser.parse_args(argv)

    if args.command in ("preflight", "healthcheck"):
        code = preflight()
        if code == 0:
            logger.info("Preflight OK")
        return code

    # Default: run
    code = preflight()
    if code != 0:
        # Non-zero preflight means don't attempt to run; Supervisor can retry based on policy
        return code

    # Importing runs the bot; this call will block until shutdown
    return run_bot_module()


if __name__ == "__main__":
    raise SystemExit(main())
