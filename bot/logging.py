"""Utility helpers for sending bot log messages to a Discord channel and/or webhook.

This module intentionally avoids importing Python's standard ``logging`` module
to prevent name shadowing confusion (the file name is ``logging.py``). You may
wish to rename this file (e.g. ``bot_logging.py``) in the future to make that
distinction clearer.

Features:
 - Safe retrieval and normalization of configuration values.
 - Optional sending to both a text channel and a webhook (executed concurrently).
 - Simple helper for Suno "boost style" payload auditing.

Note: A fresh ``aiohttp.ClientSession`` is created per webhook send to avoid
leaking sessions. Will create and manage global, long-lived session to reuse here.
"""
import os
import json
from typing import Optional, List
import asyncio

import aiohttp
import discord

from config import get_bot_alerts_routes, DEV_MODE, get_log_folder, get_greenlist

__all__ = ["log_to_channel", "log_suno_boost", "log_suno_generate"]


# ---------------------------------------------------------------------------
# Configuration normalization
# ---------------------------------------------------------------------------
_bot_alert_routes = get_bot_alerts_routes()
_raw_channel_id = _bot_alert_routes.get("BOT_LOGS_CHANNEL_ID")
_raw_webhook = _bot_alert_routes.get("BOT_LOGS_WEBHOOK")

try:
    BOT_LOGS_CHANNEL_ID: int = int(_raw_channel_id) if _raw_channel_id else -1
except (TypeError, ValueError):  # guard against invalid input
    BOT_LOGS_CHANNEL_ID = -1

BOT_LOGS_WEBHOOK: str = _raw_webhook or ""  # empty string treated as missing

# Owned Long-lived session for all logging webhook sends as a global
_logging_webhook_session: Optional[aiohttp.ClientSession] = None

LOG_FOLDER = get_log_folder()

_greenlist = get_greenlist()
_primary_dev_id = _greenlist[0] if _greenlist else None
_dev_mention = f"<@{_primary_dev_id}>" if _primary_dev_id else "@here"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def log_to_channel(
    client: discord.Client,
    message: str,
    channel_id: int = BOT_LOGS_CHANNEL_ID,
    webhook: str = BOT_LOGS_WEBHOOK,
    is_silent: bool = True,
) -> None:
    """Send a log ``message`` to the configured Discord channel and/or webhook.

    The function attempts both delivery methods (if configured) concurrently.
    Failures are swallowed (printed) so logging issues do not interrupt the
    main bot flow.

    Parameters
    ----------
    client:
        The active Discord client (or subclass) instance.
    message:
        The textual content to send.
    channel_id:
        Target channel ID; pass ``-1`` or any false-y value to skip channel send.
    webhook:
        Webhook URL; pass empty string / ``None`` to skip webhook send.
    """

    if not message:
        return  # nothing to do

    # Resolve channel (if any)
    channel: Optional[discord.TextChannel] = None
    if channel_id and channel_id != -1:
        potential = client.get_channel(channel_id)
        if isinstance(potential, discord.TextChannel):
            channel = potential

    send_coros: List[asyncio.Future] = []
    
    # Schedule channel send Prefer channel if both configured
    if channel:
        async def _send_channel(chan: discord.TextChannel, content: str) -> None:
            try:
                # Final check: ensure content length within Discord limits
                if len(content) > 1800:
                    content = content[:1800] + "\n... (truncated)"
                await chan.send(content, mention_author=False, silent=is_silent)
            except Exception as exc:  # broad for same reason as above
                print(f"[log_to_channel] Channel send failed: {exc}")

        send_coros.append(asyncio.ensure_future(_send_channel(channel, message)))

    # Schedule webhook send
    if webhook and not channel:  # Prefer channel if both configured
        async def _send_webhook(url: str, content: str) -> None:
            try:
                global _logging_webhook_session
                if _logging_webhook_session is None:
                    _logging_webhook_session = aiohttp.ClientSession()
                async with _logging_webhook_session as session:
                    hook = discord.Webhook.from_url(url, session=session, client=client)
                    # Final check: ensure content length within Discord limits
                    if len(content) > 1900:
                        content = content[:1900] + "\n... (truncated)"
                    await hook.send(content, silent=is_silent)
            except Exception as exc:  # broad: want to isolate logging failures
                print(f"[log_to_channel] Webhook send failed: {exc}")

        send_coros.append(asyncio.ensure_future(_send_webhook(webhook, message)))

    if not send_coros:
        return

    # Run concurrently; gather to avoid "Task was destroyed" warnings
    await asyncio.gather(*send_coros, return_exceptions=True)


async def log_suno_boost(
    client: discord.Client,
    interaction: discord.Interaction,
    payload: str,
    channel_id: int = BOT_LOGS_CHANNEL_ID,
    webhook: str = BOT_LOGS_WEBHOOK,
    is_success: bool = True,
) -> None:
    """Log a Suno style boost request for auditing.

    The ``payload`` string is truncated to ~1900 characters to fit comfortably
    within Discord's 2000 character message limit (allowing for formatting).
    It is wrapped in a JSON code block for readability.
    """

    if not isinstance(payload, str):  # defensive: ensure string
        payload = str(payload)

    if len(payload) > 1900:
        payload = payload[:1900] + "\n... (truncated)"

    message_header_good = f"Successful style boost for {interaction.user.mention}:\n"
    message_header_bad = f"{_dev_mention}! Failed style boost for `{interaction.user.mention}`:\n"
    message_header = [message_header_bad, message_header_good]
    
    message = (
        f"{message_header[is_success]}"
        f"```json\n{payload}\n```"
    )
    
    if not DEV_MODE:
        await log_to_channel(client, message, channel_id, webhook, is_silent=is_success) # Only ping if failure
    else:
        print(message)
        with open(os.path.join(LOG_FOLDER, "suno_booststyle.log"), "a") as f:
            f.write(f"{message}\n")


async def log_suno_generate(
    client: discord.Client,
    interaction: discord.Interaction,
    payload: str,
    channel_id: int = BOT_LOGS_CHANNEL_ID,
    webhook: str = BOT_LOGS_WEBHOOK,
    is_success: bool = True,
) -> None:
    """Log a Suno style generate request for auditing.

    The ``payload`` string is truncated to ~1900 characters to fit comfortably
    within Discord's 2000 character message limit (allowing for formatting).
    It is wrapped in a JSON code block for readability.
    """

    if not isinstance(payload, str):  # defensive: ensure string
        payload = str(payload)
        
    # Convert to json
    try:
        payload = json.loads(payload)
        request_text = str(json.dumps(payload, indent=4))
    except Exception:
        request_text = ""

    if is_success and isinstance(payload, dict):
        # Only truncate the "request" entry from the payload and keep the rest intact
        if len(request_text) > 1900:
            request_text = request_text[:1900] + "\n... (truncated)"
        # Rebuild the payload with truncated request
        payload["request"] = request_text
    else:
        if len(payload) > 1900:
            payload = payload[:1900] + "\n... (truncated)"
    
    message_header_good = f"Initiating Suno Gen for {interaction.user.mention}:\n"
    message_header_bad = f"{_dev_mention}! Failed Suno Gen for `{interaction.user.mention}`:\n"
    message_header = [message_header_bad, message_header_good]

    message = (
        f"{message_header[is_success]}"
        f"```json\n{payload}\n```"
    )

    if not DEV_MODE:
        await log_to_channel(client, message, channel_id, webhook, is_silent=is_success) # Only ping if failure
    else:
        print(message)
        with open(os.path.join(LOG_FOLDER, "suno_generate.log"), "a") as f:
            f.write(f"{message}\n")


async def close_logging_session() -> None:
    """Close the owned logging webhook session, if any."""
    global _logging_webhook_session
    if _logging_webhook_session is not None:
        await _logging_webhook_session.close()
        _logging_webhook_session = None