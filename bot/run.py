import discord
from discord import app_commands

from config import (get_test_guild_id, 
                    get_greenlist, 
                    get_bot_token, 
                    get_is_localhost,
                    COMMAND_PREFIX,
                    DEV_MODE)
from bot.gen_music import handle_music_command
from bot.bug_report import on_bug_report_emote, BUG_REPORT_EMOTE
from bot.admin import on_admin_command

if DEV_MODE:
    TEST_GUILD = discord.Object(get_test_guild_id())
else:
    TEST_GUILD = None

_greenlist = get_greenlist()

STATUS_IDENT = ['remotely', 'locally']

class StrataSlims(discord.Client):
    user: discord.ClientUser # type: ignore

    def __init__(self) -> None:
        _status_ident = STATUS_IDENT[get_is_localhost()]
        activity = discord.Activity(name=_status_ident,
                                    type=discord.ActivityType.watching)
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, activity=activity)

        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        if DEV_MODE:
            print(f'Logged in as {self.user} (ID: {self.user.id})')
            print('------')
        else:
            pass

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=TEST_GUILD)

client = StrataSlims()

@client.tree.command(guild=TEST_GUILD, description='Music')
async def music(interaction: discord.Interaction):
    if interaction.user.id not in _greenlist:
        await interaction.response.send_message(
            "You are not authorized to use this command.",
            ephemeral=True,
            delete_after=60)
        return
    await handle_music_command(interaction)
    
@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if str(payload.emoji) == BUG_REPORT_EMOTE:
        await on_bug_report_emote(client, payload)
        
@client.event
async def on_message(message):
    # Ensure client ready & ignore bots / webhooks
    if client.user is None:
        return
    if message.author.id == client.user.id or message.author.bot:
        return

    # Authorization: only allow greenlisted user IDs (silent ignore)
    if message.author.id not in _greenlist:
        return
    
    if not message.content.startswith(COMMAND_PREFIX):
        return

    # Hand off to admin command dispatcher
    await on_admin_command(client, message)

client.run(get_bot_token())