import traceback
import asyncio
from typing import Optional, cast

import discord
from discord.ext import tasks

from musicparser import (
	send_to_infobox,
	get_from_infobox,
    validate_song_interaction_data
)

from mockapi import get_credits_resilient

from sunoapi import get_task_results

from post_songs import Songs, url_to_file

class MockButtons(discord.ui.ActionRow):
    def __init__(self, view: 'MockInteraction') -> None:
        self.__view = view
        super().__init__()

    @discord.ui.button(label='Details', style=discord.ButtonStyle.primary, custom_id='strata_mock_buttons:details')
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.send_modal(Details(self.__view))

    @discord.ui.button(label='Submit', style=discord.ButtonStyle.success, disabled=True, custom_id='strata_mock_buttons:submit')
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        # Do the selected channel validation first
        if not self.__view.selected_channel_id:
            await interaction.response.send_message(
                "Please select a channel first.", 
                ephemeral=True,
                delete_after=10
            )
            return
        # Post to the selected channel if available
        channel_id = self.__view.selected_channel_id
        if not channel_id:
            # No channel chosen; done after ephemeral ack
            return
        # Try cache first
        channel = interaction.client.get_channel(channel_id)
        # Fetch from API if not cached
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to access the selected channel.", 
                                                ephemeral=True)
            except Exception:
                await interaction.followup.send("Couldn't access the selected channel.", 
                                                ephemeral=True)
            if not isinstance(channel, discord.TextChannel):
                await interaction.followup.send("Selected channel isn't a text channel.", 
                                                ephemeral=True)
                return
            
        # Acknowledge the click to the user
        await interaction.response.send_message(
            "Submitting your music generation request...", 
            ephemeral=False,
            delete_after=10
        )
        try:
            if isinstance(channel, discord.TextChannel):
                await post_to_channel(
                    channel,
                    interaction.user.id
                )
        except Exception:
            await interaction.followup.send("Failed to post in the selected channel. Posting here.", ephemeral=False)
            traceback.print_exc()
            await post_to_channel(
                interaction.channel,  # type: ignore
                interaction.user.id
            )

    @discord.ui.button(label='Close', style=discord.ButtonStyle.danger, custom_id='strata_mock_buttons:close')
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        # Delete the Song view message
        await interaction.response.edit_message(view=self.__view, delete_after=1)
        self.__view.stop()

class Details(discord.ui.Modal, title='Music Details'):

    name = discord.ui.TextInput(
        label='Song Title',
        placeholder='Your song title here...',
        required=True,
        max_length=80,
        custom_id='strata_details_modal:song_title'
    )

    style = discord.ui.TextInput(
        label='Style',
        style=discord.TextStyle.long,
        placeholder='Type the style here...',  # 100 char limit
        required=True,
        max_length=1000,
        custom_id='strata_details_modal:song_style'
    )

    lyrics = discord.ui.TextInput(
        label='Lyrics',
        style=discord.TextStyle.long,
        placeholder='Type the lyrics here...',
        required=True,
        max_length=4000,
        custom_id='strata_details_modal:song_lyrics'
    )

    def __init__(self, view: 'MockInteraction') -> None:
        self.__view = view
        self.name.default = get_from_infobox(self.__view.info_title.content) if self.__view.info_title.content else ""
        self.style.default = get_from_infobox(self.__view.info_style.content) if self.__view.info_style.content else ""
        self.lyrics.default = get_from_infobox(self.__view.info_lyrics.content) if self.__view.info_lyrics.content else ""
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        self.__view.info_title.content = send_to_infobox(str(self.name.value), "Title:")
        self.__view.info_style.content = send_to_infobox(str(self.style.value), "Style:")
        self.__view.info_lyrics.content = send_to_infobox(str(self.lyrics.value), "Lyrics:")
        await self.__view.validate_submit()
        await interaction.response.edit_message(view=self.__view)
        # Add a validation to enable the Submit button
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)

class ChannelSelector(discord.ui.ActionRow):
	def __init__(self, view: 'MockInteraction') -> None:
		self.__view = view
		super().__init__()

	@discord.ui.select(
		placeholder='Select a channel to post the generated music',
		channel_types=[discord.ChannelType.text],
		min_values=0,
		max_values=1,
		cls=discord.ui.ChannelSelect,
		custom_id='strata_channel_selector:select_channel'
	)
	async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:  # type: ignore[override]
		if select.values:
			channel = select.values[0]
			self.__view.selected_channel_id = channel.id
			select.default_values = [discord.SelectDefaultValue(id=channel.id, type=discord.SelectDefaultValueType.channel)]
		else:
			self.__view.selected_channel_id = None
			select.default_values = []
		await interaction.response.edit_message(view=self.view)

class MockInteraction(discord.ui.LayoutView):
    def __init__(self, credits: str = "Checking...", selected_channel_id: int = 0) -> None:
        super().__init__()
        self.timeout = None
        # Persist the initially provided channel id (may be 0 / falsy if none)
        self.selected_channel_id = selected_channel_id or None
        # Track numeric credits for validation; None when unknown
        self._credits: Optional[int] = None
        self.infobox = discord.ui.TextDisplay(
            f'Helpful Information.\n***Credits Remaining:*** `{credits}`'
        )
        self.thumbnail = discord.ui.Thumbnail(
            media='https://cdn.discordapp.com/attachments/1415112547484438701/1415112547748544635/logo.png'
        )
        self.section = discord.ui.Section(self.infobox, accessory=self.thumbnail)

        self.divider = discord.ui.Separator()
        # ===========
        self.info_title = discord.ui.TextDisplay('Title:')
        self.info_style = discord.ui.TextDisplay('Style:')
        self.info_lyrics = discord.ui.TextDisplay('Lyrics:')
        
        self.channel_selector_header = discord.ui.TextDisplay(
            'Select Channel to Post Generated Music:'
        )
        self.channel_selector = ChannelSelector(self)

        self.buttons = MockButtons(self)

        container = discord.ui.Container(
            self.section,
            self.divider,
            self.info_title,
            self.info_style,
            self.info_lyrics,
            self.divider,
            self.channel_selector_header,
            self.channel_selector,
            self.buttons,
        )

        self.add_item(container)

        if self.selected_channel_id:
            # access the underlying ChannelSelect component created by decorator
            channel_select: discord.ui.ChannelSelect = self.channel_selector.select_channel  # type: ignore
            channel_select.default_values = [discord.SelectDefaultValue(id=self.selected_channel_id, type=discord.SelectDefaultValueType.channel)]

        # Initialize credits state from provided string
        self.set_credits(credits)

    def set_credits(self, credits_str: str) -> None:
        """Update credits state and infobox, and re-validate the Submit button.

        Accepts any string; attempts to parse an int. If parsing fails, credits
        are considered unknown (None). A value <= 0 disables submission.
        """
        parsed: Optional[int] = None
        try:
            # Allow strings like "42"; strip whitespace
            stripped = str(credits_str).strip()
            if stripped.isdigit():
                parsed = int(stripped)
        except Exception:
            parsed = None

        self._credits = parsed
        # Update UI text
        shown = credits_str if credits_str else "unknown"
        self.infobox.content = f'Helpful Information.\n***Credits Remaining:*** `{shown}`'
        # Re-validate submit enablement
        # Note: validate_submit is async; schedule best-effort if running in loop
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_closed():
                loop.create_task(self.validate_submit())
        except RuntimeError:
            # No running loop; ignore
            pass
        
    async def validate_submit(self) -> None:
        # Enable the Submit button if title, style, and lyrics are filled in
        submit_button = self.buttons.submit_button
        valid = validate_song_interaction_data(self)
        # Also require that credits are known and > 0
        if valid and (self._credits is not None and self._credits > 0):
            submit_button.disabled = False
        else:
            submit_button.disabled = True

@tasks.loop(count=1)
async def _update_credits_after_send(interaction: discord.Interaction, view: 'MockInteraction') -> None:
	"""Fetch credits in the background and update the view when ready."""
	credits = await get_credits_resilient()
	# Update the state and UI using the view helper
	view.set_credits(credits)
	try:
		await interaction.edit_original_response(view=view)
	except Exception:
		# The original interaction may no longer be editable; ignore silently.
		pass

async def post_to_channel(channel: discord.TextChannel, user_id: int) -> None:
    try:
        task_results = await get_task_results("0e73135101e9d288396e24b42cf22946")
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        return
    results = {
    "task_id": task_results["data"]["taskId"],
    "song_title_1": task_results["data"]["response"]["sunoData"][0]["title"],
    "song_title_2": task_results["data"]["response"]["sunoData"][1]["title"],
    "song_image_url_1": task_results["data"]["response"]["sunoData"][0]["imageUrl"],
    "song_image_url_2": task_results["data"]["response"]["sunoData"][1]["imageUrl"],
    "song_audio_url_1": task_results["data"]["response"]["sunoData"][0]["audioUrl"],
    "song_audio_url_2": task_results["data"]["response"]["sunoData"][1]["audioUrl"]
    }
    # Prepare audio attachments for Discord's inline player
    fn_spaces_to_dashes = lambda s: s.replace(' ', '_')
    fn1 = f"{fn_spaces_to_dashes(results['song_title_1'])}_1.mp3"
    fn2 = f"{fn_spaces_to_dashes(results['song_title_2'])}_2.mp3"
    file1 = await url_to_file(results["song_audio_url_1"], fn1)
    file2 = await url_to_file(results["song_audio_url_2"], fn2)
    file_refs = []
    files = []
    if file1 is not None:
        files.append(file1)
        file_refs.append(f"attachment://{file1.filename}")
    
    if file2 is not None:
        files.append(file2)
        file_refs.append(f"attachment://{file2.filename}")
    
    try:
        # await channel.send(
        #     view=Songs(
        #         task_id=results["task_id"],
        #         results=dict(results),
        #         user_id=user_id,
        #         audio1_ref=file_refs[0],
        #         audio2_ref=file_refs[1],
        #     ),
        #     files=files,
        # )
        await channel.send(
            file=files[0],
            mention_author=True
        )
        await channel.send(
            file=files[1],
        )
    except Exception:
        # Log but ignore
        traceback.print_exc()

async def handle_mock_command(interaction: discord.Interaction) -> None:
    """Entry point used by bot.py to service the /music command."""
    # Send immediately with a placeholder credits value
    channel = interaction.channel_id if interaction.channel_id else 0
    view = MockInteraction(selected_channel_id=channel)
    await interaction.response.send_message(view=view, ephemeral=False)
    # Kick off a one-shot background refresh of credits and button state
    try:
        _update_credits_after_send.start(interaction, view)
    except RuntimeError:
        # If already running for some reason, ignore
        pass