import io
import json
from typing import Optional

import discord

from config import get_test_guild_id, COMMAND_PREFIX

STATUS_CHANNEL = 1417855340254593176

TEST_GUILD = discord.Object(get_test_guild_id())

async def on_admin_command(client: discord.Client, message: discord.Message):
        """Lightweight developer-only prefix command handler.

        Any message starting with COMMAND_PREFIX will be treated
        as a dev command. Only users whose IDs are in the greenlist are allowed
        to execute these; others are silently ignored to avoid leaking the
        existence of internal commands.

        Supported dev commands (extend as needed):
          *sync            -> re-sync application (slash) commands for TEST_GUILD (or global if not in DEV_MODE)
          *status <msg>    -> sends the message to the STATUS_CHANNEL
          
        """
        # If it's not coming from the TEST_GUILD, ignore
        if message.guild is None or message.guild.id != TEST_GUILD.id:
            return
        
        content = message.content

        # Strip prefix and parse
        raw = content[len(COMMAND_PREFIX):].strip()
        if not raw:
            return
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == 'sync':
            # Re-sync the command tree (guild-restricted in DEV_MODE)
            try:
                # client expected to be StrataSlims instance with tree attribute
                synced = await client.tree.sync(guild=TEST_GUILD)  # type: ignore[attr-defined]
                await message.reply(f'Synced {len(synced)} commands.', mention_author=False)
            except Exception as e:
                await message.reply(f'Sync failed: {type(e).__name__}: {e}', mention_author=False)
            return

        if cmd == 'status':
            if not args:
                await message.reply('Usage: *status <msg>', mention_author=False)
                return
            status_msg = ' '.join(args)
            status_channel = client.get_channel(STATUS_CHANNEL)
            if status_channel and isinstance(status_channel, discord.TextChannel):
                await status_channel.send(status_msg)
            else:
                await message.reply('Status channel not found.', mention_author=False)
            return
        
        if cmd == 'raw':
            # Return the raw JSON payload for a message by ID or a replied-to message.
            # Usage:
            #   *raw 123456789012345678
            #   (reply to a message) then: *raw
            # Note: relies on privileged intent for message content already being enabled.

            target_id: Optional[int] = None

            if args:
                # First argument should be a message ID
                try:
                    target_id = int(args[0])
                except ValueError:
                    await message.reply('Invalid message ID.', mention_author=False)
                    return
            else:
                # Try resolve from reply reference
                if message.reference and message.reference.message_id:
                    target_id = message.reference.message_id

            if target_id is None:
                await message.reply('No message ID provided (or reply to a message and use §raw).', mention_author=False)
                return

            # Strategy: attempt to fetch via high-level API first; fallback to HTTP for raw dict.
            raw_payload: Optional[dict] = None
            try:
                fetched = await message.channel.fetch_message(target_id)  # type: ignore[arg-type]
                # Some attributes (like embeds) are objects; convert to a serialisable structure
                # Use internal to_dict if present; fallback to manual minimal representation
                if hasattr(fetched, 'to_dict'):
                    try:
                        raw_payload = fetched.to_dict()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                if raw_payload is None:
                    raw_payload = {
                        'id': fetched.id,
                        'content': fetched.content,
                        'author': {
                            'id': fetched.author.id,
                            'name': str(fetched.author),
                        },
                        'channel_id': fetched.channel.id,
                        'guild_id': getattr(fetched.guild, 'id', None),
                        'created_at': fetched.created_at.isoformat(),
                        'type': fetched.type.name,
                        'mentions': [u.id for u in fetched.mentions],
                        'attachments': [a.url for a in fetched.attachments],
                        'embeds_count': len(fetched.embeds),
                    }
            except discord.Forbidden:
                await message.reply('Forbidden: cannot fetch that message.', mention_author=False)
                return
            except discord.NotFound:
                await message.reply('Message not found.', mention_author=False)
                return
            except discord.HTTPException as e:
                # Fallback to low-level HTTP call if generic fetch failed differently
                try:
                    raw_payload = await client.http.get_message(message.channel.id, target_id)  # type: ignore[attr-defined]
                except Exception:
                    await message.reply(f'HTTP error: {type(e).__name__}: {e}', mention_author=False)
                    return

            if raw_payload is None:
                await message.reply('Unable to obtain raw payload.', mention_author=False)
                return

            pretty = json.dumps(raw_payload, ensure_ascii=False, indent=2, sort_keys=True)

            if len(pretty) > 1900:  # Slightly under 2000 to allow code fences if desired
                with io.BytesIO(pretty.encode('utf-8')) as fp:
                    await message.reply(file=discord.File(fp, filename='raw_message.json'), mention_author=False)
            else:
                await message.reply(pretty, mention_author=False)
            return

        # Unknown command fallback
        await message.reply(f'Unknown dev command: {cmd}', mention_author=False)