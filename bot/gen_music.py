import traceback
import json
from typing import Optional
import asyncio

import discord
from discord.ext import tasks

from bot.musicparser import *
from bot.sunoapi import *
from bot.post_songs import url_to_file
from config import DEV_MODE, get_bot_alerts_routes

_dev_mode = DEV_MODE

_bot_alert_routes = get_bot_alerts_routes()
BOT_LOGS_CHANNEL_ID = _bot_alert_routes.get("BOT_LOGS_CHANNEL_ID", None)
BOT_LOGS_WEBHOOK = _bot_alert_routes.get("BOT_LOGS_WEBHOOK", None)

HELP_TEXT = 'Helpful Info'
MUSIC_GEN_THUMBNAIL = 'https://cdn.discordapp.com/attachments/1415112547484438701/1415112547748544635/logo.png'

class MusicGenButtons(discord.ui.ActionRow):
	def __init__(self, view: 'MusicGen') -> None:
		self.__view = view
		super().__init__()
  
	# region DETAILS BUTTON
	# =================================================== DETAILS BUTTON ========
	@discord.ui.button(
     label='Details', 
     style=discord.ButtonStyle.primary, 
     custom_id='strata_song_buttons:details'
     )
	async def details_button(
     self, 
     interaction: discord.Interaction, 
     button: discord.ui.Button
     ) -> None:  # type: ignore[override]
		await interaction.response.send_modal(Details(self.__view))
	# endregion
	# region BOOST STYLE BUTTON
 	# =================================================== BOOST STYLE BUTTON ====
	@discord.ui.button(
     label='Boost Style', 
     style=discord.ButtonStyle.success, 
     disabled=True, 
     custom_id='strata_song_buttons:booststyle'
     )
	async def boost_style_button(
     self, 
     interaction: discord.Interaction, 
     button: discord.ui.Button
     ) -> None:  # type: ignore[override]
		# First Check that there is content in self.__view.info_style
		style_content = get_from_infobox(self.__view.info_style.content) \
      					if self.__view.info_style.content \
               			else ""
		if not style_content:
			await interaction.response.send_message(
				"Please provide a Style in the Details first.", 
				ephemeral=True,
				delete_after=10
			)
			return
		style_boost_payload = build_booststyle_payload(self.__view)
		
		if _dev_mode:
			print(f"Generated boost style payload:\n {json.dumps(style_boost_payload, indent=4)}")
		else:
			# In production, log the payload to the bot logs channel for auditing
			if BOT_LOGS_CHANNEL_ID and BOT_LOGS_WEBHOOK:
				try:
					log_channel = interaction.client.get_channel(BOT_LOGS_CHANNEL_ID)
					if log_channel is None:
						log_channel = await interaction.client.fetch_channel(BOT_LOGS_CHANNEL_ID)
					if isinstance(log_channel, discord.TextChannel):
						payload_str = json.dumps(style_boost_payload, indent=4)
						if len(payload_str) > 1900:
							payload_str = payload_str[:1900] + "\n... (truncated)"
						await log_channel.send(
							content=f"New style boost request from {interaction.user.mention}:\n```json\n{payload_str}\n```"
						)
				except Exception as e:
					print(f"Failed to log style boost request: {e}")
					traceback.print_exc()		
  
		await toggle_button_states(interaction, self.__view, is_generating=True)
  
		response = await generate_boosted_style(style_boost_payload) # = Uncomment FOR MOCK TESTING =
		# response = {				
		#     "result": "Opening with a crisp snare drum cadence, the song features \
      	# 				a lone fife carrying a soaring Celtic-inspired melody over a \
        # 				stately march tempo. The absurdly patriotic male vocals \
        # 				command with bold phrasing, rising above the sparse arrangement. \
        # 				Dynamic shifts emphasize unison hits, ending with a stirring flute flourish.",
		#     "creditsRemaining": 864.8
		# 	}
		if 'error' in response:
			await toggle_button_states(interaction, self.__view, is_generating=False)
			await interaction.followup.send(
					f"Error boosting style: {response['error']['msg']}", 
					ephemeral=True)
			return
		generated_boosted_style = response['result']
		remaining_credits = response['creditsRemaining']
		self.__view.set_credits(remaining_credits)
		self.__view.info_boosted_style.content = send_to_infobox(generated_boosted_style, "Boosted Style:")
		await toggle_button_states(interaction, self.__view, is_generating=False)
		await interaction.edit_original_response(view=self.__view)
	# endregion
	# region EXTRAS BUTTON
 	# =================================================== EXTRAS BUTTON ========
	@discord.ui.button(
     label='Extras', 
     style=discord.ButtonStyle.secondary, 
     custom_id='strata_song_buttons:extras'
     )
	async def extras_button(
     self, 
     interaction: discord.Interaction,
     button: discord.ui.Button
     ) -> None:  # type: ignore[override]
		await interaction.response.send_modal(Extras(self.__view))
	# endregion
	# region SUBMIT BUTTON
 	# =================================================== SUBMIT BUTTON ========
	@discord.ui.button(
     label='Submit', 
     style=discord.ButtonStyle.success, 
     disabled=True, 
     custom_id='strata_song_buttons:submit'
     )
	async def submit_button(
     self, 
     interaction: discord.Interaction, 
     button: discord.ui.Button
     ) -> None:  # type: ignore[override]
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
		# Build the payload from the view state
		payload = build_music_payload(self.__view)
  
		if _dev_mode:
			print(f"Generated music gen payload:\n {json.dumps(payload, indent=4)}")
		else:
			# In production, log the payload to the bot logs channel for auditing
			if BOT_LOGS_CHANNEL_ID and BOT_LOGS_WEBHOOK:
				try:
					log_channel = interaction.client.get_channel(BOT_LOGS_CHANNEL_ID)
					if log_channel is None:
						log_channel = await interaction.client.fetch_channel(BOT_LOGS_CHANNEL_ID)
					if isinstance(log_channel, discord.TextChannel):
						payload_str = json.dumps(payload, indent=4)
						if len(payload_str) > 1900:
							payload_str = payload_str[:1900] + "\n... (truncated)"
						await log_channel.send(
							content=f"New music generation request from {interaction.user.mention}:\n```json\n{payload_str}\n```"
						)
				except Exception as e:
					print(f"Failed to log music generation request: {e}")
					traceback.print_exc()
		
		await toggle_button_states(interaction, self.__view, is_generating=True)
		
		response = await generate_music(payload) # ===================== Uncomment FOR MOCK TESTING
		# response = {
		# 		"code": 200,
		# 		"msg": "success",
		# 		"data": {
		# 			"taskId": "7c77b4bc3cc8edff4010577a9c6ec74b"
		# 		}
		# 	}
		if 'error' in response:
			await toggle_button_states(interaction, self.__view, is_generating=False)
			await interaction.followup.send(
					f"Error starting music generation: {response['error']['msg']}",
					ephemeral=True)
			return
		task_id = response['data']['taskId']
		if isinstance(channel, discord.TextChannel):
			await channel.send(
				content=f"Music generation started! Task ID: `{task_id}`. \
        				You will be notified here when it's complete.",
				mention_author=True,
				delete_after=300
			)
		# Start background task to poll for results
		try:
			_check_music_gen_results.start(interaction, self.__view, task_id, channel)
		except Exception as e:
			print(f"Error starting music generation task: {e}")
			traceback.print_exc()
			await toggle_button_states(interaction, self.__view, is_generating=False)
			
			if isinstance(channel, discord.TextChannel):
				await channel.send(content="An error occurred while processing your request.")
	# endregion
            
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
		self.name.default = get_from_infobox(self.__view.info_title.content) \
      						if self.__view.info_title.content else ""
		self.style.default = get_from_infobox(self.__view.info_style.content) \
      						if self.__view.info_style.content else ""
		self.lyrics.default = get_from_infobox(self.__view.info_lyrics.content) \
      						if self.__view.info_lyrics.content else ""
		super().__init__()

	async def on_submit(self, interaction: discord.Interaction, /) -> None:
		self.__view.info_title.content = send_to_infobox(str(self.name.value), "Title:")
		# If the new style value is different from the previous one, reset the boosted style
		if self.style.value != get_from_infobox(self.__view.info_style.content):
			self.__view.info_boosted_style.content = "-"
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
		placeholder='0.00 to 1.00 (e.g., 0.65)\n Higher = more faithful to style',
		required=False,
		max_length=10,
		default='0.65',
		custom_id='strata_extras_modal:style_weight'
	)
	weirdness_constraint = discord.ui.TextInput(
		label='Weirdness Constraint',
		style=discord.TextStyle.short,
		placeholder='0.00 to 1.00 (e.g., 0.65)\n Lower = more creative',
		required=False,
		max_length=10,
		default='0.65',
		custom_id='strata_extras_modal:weirdness_constraint'
	)
	audio_weight = discord.ui.TextInput(
		label='Audio Weight',
		style=discord.TextStyle.short,
		placeholder='0.00 to 1.00 (e.g., 0.65)\n Higher = more faithful to audio prompt',
		required=False,
		max_length=10,
		default='0.65',
		custom_id='strata_extras_modal:audio_weight'
	)

	def __init__(self, view: 'MusicGen') -> None:
		self.__view = view
		# if the value is "-" set to empty string
		self.neg_tags.default = "" \
      							if get_from_infobox(self.__view.info_negatives.content) == "-" \
      							else get_from_infobox(self.__view.info_negatives.content)
		self.style_weight.default = "" \
      							if get_from_infobox(self.__view.info_style_weight.content) == "-" \
      							else get_from_infobox(self.__view.info_style_weight.content)
		self.weirdness_constraint.default = "" \
      							if get_from_infobox(self.__view.info_weirdness_weight.content) == "-" \
      							else get_from_infobox(self.__view.info_weirdness_weight.content)
		self.audio_weight.default = "" \
      							if get_from_infobox(self.__view.info_audio_weight.content) == "-" \
      							else get_from_infobox(self.__view.info_audio_weight.content)
		super().__init__()

	async def on_submit(self, interaction: discord.Interaction):
		# Update the infobox content with the new values
		assert isinstance(self.vocal_gender.component, discord.ui.Select)
		self.__view.info_gender.content = send_to_infobox(
			str(self.vocal_gender.component.values[0]),
			"Vocalist Gender:"
		)
		self.__view.info_negatives.content = send_to_infobox(
			str(self.neg_tags.value),
			"Negative Prompt:"
		)
		self.__view.info_style_weight.content = send_to_infobox(
			str(self.style_weight.value),
			"Style Weight:"
		)
		self.__view.info_weirdness_weight.content = send_to_infobox(
			str(self.weirdness_constraint.value),
			"Weirdness Constraint:"
		)
		self.__view.info_audio_weight.content = send_to_infobox(
			str(self.audio_weight.value),
			"Audio Weight:"
		)
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
	async def select_channel(
     self, 
     interaction: discord.Interaction, 
     select: discord.ui.ChannelSelect
     ) -> None:  # type: ignore[override]
		if select.values:
			channel = select.values[0]
			self.__view.selected_channel_id = channel.id
			select.default_values = [discord.SelectDefaultValue(id=channel.id,
                                                       			type=discord.SelectDefaultValueType.channel)]
		else:
			self.__view.selected_channel_id = None
			select.default_values = []
		await interaction.response.edit_message(view=self.view)

class MusicGen(discord.ui.LayoutView):
	def __init__(self, credits: str = "Checking...", selected_channel_id: int = 0) -> None:
		super().__init__()
		self.timeout = None
		self._credits: Optional[float] = None
		# Persist the initially provided channel id (may be 0 / falsy if none)
		self.selected_channel_id = selected_channel_id or None
		self.infobox = discord.ui.TextDisplay(
			f'{HELP_TEXT}\n***Credits Remaining:*** `{credits}`'
		)
		self.thumbnail = discord.ui.Thumbnail(
			media=MUSIC_GEN_THUMBNAIL
		)
		self.section = discord.ui.Section(self.infobox, accessory=self.thumbnail)

		self.divider = discord.ui.Separator()
		# ===========
		self.info_title = discord.ui.TextDisplay('Title:')
		self.info_style = discord.ui.TextDisplay('Style:')
		self.info_boosted_style = discord.ui.TextDisplay('-')
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
										 self.info_boosted_style,
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
			channel_select.default_values = [discord.SelectDefaultValue(id=self.selected_channel_id, 
                                                               			type=discord.SelectDefaultValueType.channel)]
		
		self.set_credits(credits)
  
	def set_credits(self, credits_str: str) -> None:
		"""Update credits state and infobox, and re-validate the Submit button.

		Accepts any string; attempts to parse a float to 2 decimal places. If parsing fails, credits
		are considered unknown (None). A value <= 0 disables submission.
		"""
		parsed: Optional[float] = None
		try:
			# Allow strings like "42"; strip whitespace
			stripped = str(credits_str).strip()
			if stripped.replace('.', '', 1).isdigit():
				parsed = float(stripped)
		except Exception:
			parsed = None

		self._credits = parsed
		# Update UI text
		shown = credits_str if credits_str else "unknown"
		self.infobox.content = f'{HELP_TEXT}\n***Credits Remaining:*** `{shown}`'
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
		if valid:
			submit_button.disabled = False
		else:
			submit_button.disabled = True
		# Enable the Boost Style button if style is filled in
		boost_button = self.buttons.boost_style_button
		style_content = get_from_infobox(self.info_style.content) if self.info_style.content else ""
		if style_content:
			boost_button.disabled = False
		else:
			boost_button.disabled = True

@tasks.loop(count=1)
async def _update_credits_after_send(interaction: discord.Interaction, view: 'MusicGen') -> None:
	"""Fetch credits in the background and update the view when ready."""
	credits = await get_remaining_credits()
	# Update the state and UI using the view helper
	view.set_credits(credits)
	try:
		await interaction.edit_original_response(view=view)
	except Exception:
		# The original interaction may no longer be editable; ignore silently.
		pass

@tasks.loop(seconds=10, count=60)
async def _check_music_gen_results(interaction: discord.Interaction,
                                   view: 'MusicGen', 
                                   task_id: str,
                                   channel: discord.TextChannel) -> None:
	task_results = await get_task_results(task_id)
	if 'error' in task_results:
		try:
			await interaction.followup.send(f"Error retrieving task results: {task_results['error']['msg']}", ephemeral=True)
		except Exception:
			pass
		await toggle_button_states(interaction, view, is_generating=False)
  
		_check_music_gen_results.stop()
		return
	status = (task_results.get('data', {}).get('status') or '').strip().upper()
	if _dev_mode:
		print(f'Status: {status}')
	else:
		# In production, log the whole task result to the bot logs channel for auditing
		if BOT_LOGS_CHANNEL_ID and BOT_LOGS_WEBHOOK and status in {'SUCCESS'}:
			try:
				log_channel = interaction.client.get_channel(BOT_LOGS_CHANNEL_ID)
				if log_channel is None:
					log_channel = await interaction.client.fetch_channel(BOT_LOGS_CHANNEL_ID)
				if isinstance(log_channel, discord.TextChannel):
					task_results_str = json.dumps(task_results, indent=4)
					if len(task_results_str) > 1900:
						task_results_str = task_results_str[:1900] + "\n... (truncated)"
					await log_channel.send(
						content=f"Music generation task update for {interaction.user.mention} (Task ID: `{task_id}`):\n```json\n{task_results_str}\n```"
					)
			except Exception as e:
				print(f"Failed to log music generation task update: {e}")
				traceback.print_exc()
	if status in {'SUCCESS'}:
		# Stop the loop
		_check_music_gen_results.stop()
		await toggle_button_states(interaction, view, is_generating=False)
		results = {
		"task_id": task_results["data"]["taskId"],
		"song_title_1": task_results["data"]["response"]["sunoData"][0]["title"],
		"song_title_2": task_results["data"]["response"]["sunoData"][1]["title"],
		"song_image_url_1": task_results["data"]["response"]["sunoData"][0]["imageUrl"],
		"song_image_url_2": task_results["data"]["response"]["sunoData"][1]["imageUrl"],
		"song_audio_url_1": task_results["data"]["response"]["sunoData"][0]["audioUrl"],
		"song_audio_url_2": task_results["data"]["response"]["sunoData"][1]["audioUrl"]
		}
		await post_music_results(channel, results, interaction)

 	# Else if not pending or first success, something went wrong
	elif status not in ["PENDING", "FIRST_SUCCESS", "TEXT_SUCCESS"]:
		try:
			await interaction.followup.send(f"Music generation failed with status: {status}", ephemeral=True)
		except Exception:
			pass
		try:
			await toggle_button_states(interaction, view, is_generating=False)
		except Exception:
			pass

		_check_music_gen_results.stop()
		return

	# Otherwise, still pending; continue the loop
 	# If we time out, then tell the user what the task ID was so they can check manually
	if _check_music_gen_results.current_loop == 59:
		try:
			await interaction.followup.send(f"Music generation is taking longer than expected. \
       										You can check the status of your task with ID `{task_id}` later.",
                 							ephemeral=False)
		except Exception:
			pass
		await toggle_button_states(interaction, view, is_generating=False)
		
		_check_music_gen_results.stop()
		return

async def post_music_results(channel: discord.TextChannel, 
                             results: dict, 
                             interaction: discord.Interaction) -> None:
	# User to ping
	user_mention = interaction.user.mention

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
		await channel.send(
			content=f"{user_mention} Task ID: {results['task_id']}\n### [{results['song_title_1']}]({results['song_image_url_1']})",
			file=files[0],
			mention_author=True
		)
		await channel.send(
			content=f"### [{results['song_title_2']}]({results['song_image_url_2']})",
			file=files[1],
		)
	except Exception as e:
		# Log but ignore
		traceback.print_exc()

async def toggle_button_states(interaction: discord.Interaction, 
                               view: 'MusicGen', 
                               is_generating: bool) -> None:
    """Deterministically set button states based on is_generating.

    - While generating: disable Details, Extras, Submit, Close; set submit label to 'Generating...'
    - Otherwise: enable Details, Extras, Close; enable Submit only if form is valid; label 'Submit'
    """
    details_button = view.buttons.details_button
    extras_button = view.buttons.extras_button
    submit_button = view.buttons.submit_button
    boost_style_button = view.buttons.boost_style_button
    # close_button = view.buttons.close_button
    
    channel_selector = view.channel_selector.select_channel

    if is_generating:
        details_button.disabled = True
        extras_button.disabled = True
        submit_button.disabled = True
        boost_style_button.disabled = True
        # close_button.disabled = True
        channel_selector.disabled = True
        submit_button.label = "Generating..."
    else:
        # Recompute validity for submit enablement
        is_valid = validate_song_interaction_data(view)
        details_button.disabled = False
        extras_button.disabled = False
        # close_button.disabled = False
        channel_selector.disabled = False
        submit_button.disabled = not is_valid
        submit_button.label = "Submit"

    # Update the message safely depending on response state
    try:
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=view)
        else:
            await interaction.edit_original_response(view=view)
    except Exception:
        # Ignore edit failures (message may be gone or not editable)
        pass

async def handle_music_command(interaction: discord.Interaction) -> None:
	"""Entry point used by bot.py to service the /music command."""
	channel = interaction.channel_id if interaction.channel_id else 0
	view = MusicGen(selected_channel_id=channel)
	await interaction.response.send_message(view=view, ephemeral=False)
	try:
		_update_credits_after_send.start(interaction, view)
	except RuntimeError:
        # If already running for some reason, ignore
		pass
