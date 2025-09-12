import traceback
import time

import discord
from discord import app_commands

from config import get_test_guild_id, get_greenlist, get_bot_token
from gen_music import handle_music_command
from post_songs import handle_post_songs_command
from booststyle import handle_booststyle_command
from mockinteraction import handle_mock_command


TEST_GUILD = discord.Object(get_test_guild_id())
_greenlist = get_greenlist()
GREENLIST = [discord.Object(id=user_id) for user_id in _greenlist]

class MyClient(discord.Client):
    # Suppress error on the User attribute being None since it fills up later
    user: discord.ClientUser # type: ignore

    def __init__(self) -> None:
        
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def setup_hook(self) -> None:
        # Sync the application command with Discord.
        await self.tree.sync(guild=TEST_GUILD)

client = MyClient()

@client.tree.command(guild=TEST_GUILD, description='Music')
async def music(interaction: discord.Interaction):
    # Delegate to song.py handler
    await handle_music_command(interaction)

# @client.tree.command(guild=TEST_GUILD, description='Songs')
# async def songs(interaction: discord.Interaction, task_id: str = "348acc677932cc378c4ddb3225ab74e2"):
#     await handle_post_songs_command(interaction, task_id)
    
@client.tree.command(guild=TEST_GUILD, description='Boost Style')
async def booststyle(interaction: discord.Interaction):
    await handle_booststyle_command(interaction)

# @client.tree.command(guild=TEST_GUILD, description='Mock Command')
# async def mock(interaction: discord.Interaction):
#     await handle_mock_command(interaction)

client.run(get_bot_token())