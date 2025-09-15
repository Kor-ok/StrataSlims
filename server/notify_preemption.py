#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("notify_preemption")


async def send_via_bot(channel_id: int, message: str) -> int:
    try:
        import discord  # type: ignore
        from discord.abc import Messageable  # type: ignore
    except Exception:
        logger.error("discord.py not available; cannot send via bot token")
        return 2

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not set; cannot send via bot token")
        return 2

    intents = discord.Intents.none()
    client = discord.Client(intents=intents)

    async def _send_and_close():
        try:
            channel = client.get_channel(channel_id)
            if channel is None:
                channel = await client.fetch_channel(channel_id)
            if isinstance(channel, Messageable):
                await channel.send(message)  # type: ignore
            else:
                raise RuntimeError(f"Channel {channel_id} is not messageable")
            logger.info("Preemption message sent to channel %s", channel_id)
        except Exception as e:
            logger.error("Failed sending preemption message: %s", e)
        finally:
            await client.close()

    @client.event
    async def on_ready():
        await _send_and_close()

    try:
        await client.start(token)
        return 0
    except Exception as e:
        logger.error("Error during bot start: %s", e)
        return 1


async def send_via_webhook(webhook_url: str, message: str) -> int:
    try:
        import aiohttp  # type: ignore
    except Exception:
        logger.error("aiohttp not available; cannot send via webhook")
        return 2
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json={"content": message}) as resp:
                if resp.status // 100 == 2:
                    logger.info("Preemption message sent via webhook")
                    return 0
                logger.error("Webhook send failed: HTTP %s", resp.status)
                return 1
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return 1


def main(argv: list[str]) -> int:
    msg = os.getenv("PREEMPTION_MESSAGE", "StrataSlims: VM preemption notice received. Shutting down...")
    webhook = os.getenv("PREEMPTION_WEBHOOK", "")
    channel_raw = os.getenv("PREEMPTION_ALERT_CHANNEL_ID", "")

    if webhook:
        return asyncio.run(send_via_webhook(webhook, msg))

    if channel_raw:
        try:
            channel_id = int(channel_raw)
        except ValueError:
            logger.error("Invalid PREEMPTION_ALERT_CHANNEL_ID: %s", channel_raw)
            return 2
        return asyncio.run(send_via_bot(channel_id, msg))

    logger.warning("No PREEMPTION_WEBHOOK or PREEMPTION_ALERT_CHANNEL_ID set; nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
