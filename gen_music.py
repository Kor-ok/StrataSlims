import traceback
from typing import Optional

import discord

from musicparser import (
	build_music_payload,
	validate_song_interaction_data,
	send_to_infobox,
	get_from_infobox,
)
from sunoapi import get_remaining_credits, generate_music, wait_for_completion


class MusicGenButtons(discord.ui.ActionRow):
	def __init__(self, view: 'MusicGen') -> None:
		self.__view = view
		super().__init__()

	@discord.ui.button(label='Details', style=discord.ButtonStyle.primary, custom_id='strata_song_buttons:details')
	async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
		await interaction.response.send_modal(Details(self.__view))

	@discord.ui.button(label='Extras', style=discord.ButtonStyle.secondary, custom_id='strata_song_buttons:extras')
	async def extras_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
		await interaction.response.send_modal(Extras(self.__view))

	@discord.ui.button(label='Submit', style=discord.ButtonStyle.success, disabled=True, custom_id='strata_song_buttons:submit')
	async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
		credits = await get_remaining_credits()
		self.__view.infobox.content = f'Helpful Information.\n***Credits Remaining:***`{credits}`'
		payload = build_music_payload(self.__view)
		response = await generate_music(payload)
		if 'error' in response:
			await interaction.response.send_message(f"Error: {response['error']['msg']}")
			return
		task_id = response['data']['taskId']
		self.__view.buttons.submit_button.disabled = True
		await interaction.response.send_message(f"Submitted! Task ID: {task_id}.")
		await interaction.response.edit_message(view=self.__view)

	@discord.ui.button(label='Force Check', style=discord.ButtonStyle.success, custom_id='strata_song_buttons:force_check')
	async def force_check_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
		# Read task_ids.log for the last submitted task ID
		# and check its status immediately
		try:
			with open('task_ids.log', 'r') as f:
				lines = f.readlines()
		except FileNotFoundError:
			await interaction.response.send_message("No task IDs found to check.")
			return
		if not lines:
			await interaction.response.send_message("No task IDs found to check.")
			return
		last_task_id = lines[-1].strip()
		result = await wait_for_completion(last_task_id)
		if 'error' not in result:
			self.__view.buttons.submit_button.disabled = False
			await interaction.response.edit_message(view=self.__view)

		song_title = result.get("song_titles", [None])[0]
		durations = result.get("song_durations", [])
		audio_urls = result.get("song_audio_urls", [])
		image_urls = result.get("song_image_urls", [])

		def safe_get(lst, idx) -> Optional[str]:
			try:
				return lst[idx]
			except Exception:
				return None

		msg_lines = []
		if song_title:
			msg_lines.append(f"Song: {song_title}")
		img1 = safe_get(image_urls, 0)
		if img1:
			msg_lines.append(str(img1))
		dur1 = safe_get(durations, 0)
		aud1 = safe_get(audio_urls, 0)
		if dur1:
			msg_lines.append(f"Track 1: {dur1}")
		if aud1:
			msg_lines.append(str(aud1))
		img2 = safe_get(image_urls, 1)
		if img2:
			msg_lines.append(str(img2))
		dur2 = safe_get(durations, 1)
		aud2 = safe_get(audio_urls, 1)
		if dur2:
			msg_lines.append(f"Track 2: {dur2}")
		if aud2:
			msg_lines.append(str(aud2))

		if msg_lines:
			await interaction.response.send_message("\n".join(msg_lines))
		else:
			await interaction.response.send_message("No results yet. Please try again later.")

	@discord.ui.button(label='Close', style=discord.ButtonStyle.danger, custom_id='strata_song_buttons:close')
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

	def __init__(self, view: 'MusicGen') -> None:
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


class Extras(discord.ui.Modal, title='Music Extras'):

	neg_tags = discord.ui.TextInput(
		label='Negative Tags',
		style=discord.TextStyle.long,
		placeholder='Use to avoid specific styles.\nExample: "Heavy Metal, Upbeat Drums"',
		required=False,
		max_length=1000,
		custom_id='strata_extras_modal:negative_tags'
	)

	vocal_gender = discord.ui.Label(
		text='Gender',
		component=discord.ui.Select(
			options=[
				discord.SelectOption(label='Male', value='Male'),
				discord.SelectOption(label='Female', value='Female'),
				discord.SelectOption(label='Surprise', value='Surprise Me'),
			],
			custom_id='strata_extras_modal:vocal_gender'
		)
	)

	style_weight = discord.ui.TextInput(
		label='Style Weight',
		style=discord.TextStyle.short,
		placeholder='e.g., 0.65',
		required=False,
		max_length=10,
		default='0.65',
		custom_id='strata_extras_modal:style_weight'
	)
	weirdness_constraint = discord.ui.TextInput(
		label='Weirdness Constraint',
		style=discord.TextStyle.short,
		placeholder='e.g., 0.65',
		required=False,
		max_length=10,
		default='0.65',
		custom_id='strata_extras_modal:weirdness_constraint'
	)
	audio_weight = discord.ui.TextInput(
		label='Audio Weight',
		style=discord.TextStyle.short,
		placeholder='e.g., 0.65',
		required=False,
		max_length=10,
		default='0.65',
		custom_id='strata_extras_modal:audio_weight'
	)

	def __init__(self, view: 'MusicGen') -> None:
		self.__view = view
		# Will figure out Gender dropdown later
		self.neg_tags.default = get_from_infobox(self.__view.info_negatives.content) if self.__view.info_negatives.content else ""
		self.style_weight.default = get_from_infobox(self.__view.info_style_weight.content) if self.__view.info_style_weight.content else ""
		self.weirdness_constraint.default = get_from_infobox(self.__view.info_weirdness_weight.content) if self.__view.info_weirdness_weight.content else ""
		self.audio_weight.default = get_from_infobox(self.__view.info_audio_weight.content) if self.__view.info_audio_weight.content else ""
		super().__init__()

	async def on_submit(self, interaction: discord.Interaction):
		# Update the infobox content with the new values
		assert isinstance(self.vocal_gender.component, discord.ui.Select)
		self.__view.info_gender.content = send_to_infobox(str(self.vocal_gender.component.values[0]), "Vocalist Gender:")
		self.__view.info_negatives.content = send_to_infobox(str(self.neg_tags.value), "Negative Prompt:")
		self.__view.info_style_weight.content = send_to_infobox(str(self.style_weight.value), "Style Weight:")
		self.__view.info_weirdness_weight.content = send_to_infobox(str(self.weirdness_constraint.value), "Weirdness Constraint:")
		self.__view.info_audio_weight.content = send_to_infobox(str(self.audio_weight.value), "Audio Weight:")
		await self.__view.validate_submit()
		await interaction.response.edit_message(view=self.__view)
		self.stop()

	async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
		await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

		# Make sure we know what the error actually is
		traceback.print_exception(type(error), error, error.__traceback__)


class ChannelSelector(discord.ui.ActionRow):
	def __init__(self, view: 'MusicGen') -> None:
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


class MusicGen(discord.ui.LayoutView):
	def __init__(self, credits: str, selected_channel_id: int) -> None:
		super().__init__()
		self.timeout = None
		# Persist the initially provided channel id (may be 0 / falsy if none)
		self.selected_channel_id = selected_channel_id or None
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
		# ===========
		self.extras_header = discord.ui.TextDisplay('Optional Extras:')
		self.info_gender = discord.ui.TextDisplay('-')
		self.info_negatives = discord.ui.TextDisplay('-')
		self.info_style_weight = discord.ui.TextDisplay('-')
		self.info_weirdness_weight = discord.ui.TextDisplay('-')
		self.info_audio_weight = discord.ui.TextDisplay('-')
		# ===========

		self.channel_selector_header = discord.ui.TextDisplay(
			'Select Channel to Post Generated Music:'
		)
		self.channel_selector = ChannelSelector(self)

		self.buttons = MusicGenButtons(self)

		container = discord.ui.Container(self.section,
										 self.divider,
										 self.info_title,
										 self.info_style,
										 self.info_lyrics,
										 self.divider,
										 self.extras_header,
										 self.info_gender,
										 self.info_negatives,
										 self.info_style_weight,
										 self.info_weirdness_weight,
										 self.info_audio_weight,
										 self.divider,
										 self.channel_selector_header,
										 self.channel_selector,
										 self.buttons)
		self.add_item(container)
		# If an initial channel id was supplied, reflect it in the selector defaults
		if self.selected_channel_id:
			# access the underlying ChannelSelect component created by decorator
			channel_select: discord.ui.ChannelSelect = self.channel_selector.select_channel  # type: ignore
			channel_select.default_values = [discord.SelectDefaultValue(id=self.selected_channel_id, type=discord.SelectDefaultValueType.channel)]

	async def validate_submit(self) -> None:
		# Enable the Submit button if title, style, and lyrics are filled in
		submit_button = self.buttons.submit_button
		valid = validate_song_interaction_data(self)
		if valid:
			submit_button.disabled = False
		else:
			submit_button.disabled = True


async def handle_music_command(interaction: discord.Interaction) -> None:
	"""Entry point used by bot.py to service the /music command."""
	credits = await get_remaining_credits()
	channel = interaction.channel_id if interaction.channel_id else 0
	view = MusicGen(credits=str(credits), selected_channel_id=channel)
	await interaction.response.send_message(view=view, ephemeral=False)
