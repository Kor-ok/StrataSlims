import discord
from discord import app_commands

from config import get_test_guild_id, get_greenlist, get_bot_token, get_is_localhost
from bot.gen_music import handle_music_command
from bot.booststyle import handle_booststyle_command

"""
sudo supervisorctl restart strataslims
"""

TEST_GUILD = discord.Object(get_test_guild_id())
_greenlist = get_greenlist()
GREENLIST = [discord.Object(id=user_id) for user_id in _greenlist]
STATUS_IDENT = ['remotely', 'locally']

class StrataSlims(discord.Client):
    user: discord.ClientUser # type: ignore

    def __init__(self) -> None:
        _status_ident = STATUS_IDENT[get_is_localhost()]
        activity = discord.Activity(name=_status_ident,
                                    type=discord.ActivityType.watching)
        intents = discord.Intents.default()
        super().__init__(intents=intents, activity=activity)

        self.tree = app_commands.CommandTree(self)

    # async def on_ready(self):
    #     print(f'Logged in as {self.user} (ID: {self.user.id})')
    #     print('------')

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=TEST_GUILD)

client = StrataSlims()

@client.tree.command(guild=TEST_GUILD, description='Music')
async def music(interaction: discord.Interaction):
    await handle_music_command(interaction)
    
# @client.tree.command(guild=TEST_GUILD, description='Boost Style')
# async def booststyle(interaction: discord.Interaction):
#     await handle_booststyle_command(interaction)

client.run(get_bot_token())