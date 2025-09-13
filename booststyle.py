import asyncio
import io
import traceback
from typing import Optional, cast

import discord
from discord.ext import tasks

from sunoapi import boost_style, get_remaining_credits

from musicparser import (
	send_to_infobox,
	get_from_infobox,
    validate_booststyle_interaction_data
)

class BoostStyleButtons(discord.ui.ActionRow):
    def __init__(self, view: 'BoostStyle') -> None:
        self.__view = view
        super().__init__()
    
    @discord.ui.button(label="Input Style", style=discord.ButtonStyle.primary, custom_id='strata_booststyle_buttons:input_style')
    async def button_input_style(self, interaction: discord.Interaction, button: discord.ui.Button) -> None: # type: ignore
        await interaction.response.send_modal(StyleInputModal(self.__view))
        
    @discord.ui.button(label="Boost Style", style=discord.ButtonStyle.success, disabled=True, custom_id='strata_booststyle_buttons:boost_style')
    async def button_boost_style(self, interaction: discord.Interaction, button: discord.ui.Button) -> None: # type: ignore
        if not get_from_infobox(self.__view.info_userstyle.content):
            await interaction.response.send_message("Please input a style text first.", ephemeral=True, delete_after=10)
            return
        
        # Disable the button to prevent multiple clicks
        button.disabled = True
        try:
            # No longer a background task; await directly
            await _get_boost_style_results(interaction, self.__view)
        except Exception as e:
            print(f"Error starting boost style task: {e}")
            traceback.print_exc()
            button.disabled = False
            await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True, delete_after=10)
    
    @discord.ui.button(label='Close', style=discord.ButtonStyle.danger, custom_id='strata_booststyle_buttons:close')
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        await interaction.response.edit_message(view=self.__view, delete_after=1)
        self.__view.stop()

class StyleInputModal(discord.ui.Modal, title="Input Style Text"):
    style_text = discord.ui.TextInput(
        label="Style Text",
        style=discord.TextStyle.long,
        placeholder="Enter the style text you want to boost...",
        required=True,
        max_length=1000,
    )

    def __init__(self, view: 'BoostStyle') -> None:
        self.__view = view
        self.style_text.default = get_from_infobox(self.__view.info_userstyle.content) if self.__view.info_userstyle.content else ""
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        self.__view.info_userstyle.content = send_to_infobox(str(self.style_text.value), "Your Style:\n")
        await self.__view.validate_boost()
        await interaction.response.edit_message(view=self.__view)
        self.stop()

class BoostStyle(discord.ui.LayoutView):
    def __init__(self, credits: str = "Checking..."):
        super().__init__()
        self.timeout = None
        self._credits: Optional[int] = None
        self.infobox = discord.ui.TextDisplay(
        f'Helpful Information.\n***Credits Remaining:*** `{credits}`'
        )
        self.thumbnail = discord.ui.Thumbnail(
			media='https://cdn.discordapp.com/attachments/1415112547484438701/1415112547748544635/logo.png'
		)
        self.section = discord.ui.Section(self.infobox, accessory=self.thumbnail)

        self.info_userstyle = discord.ui.TextDisplay(f"Your Style:")
        self.info_boostedstyle = discord.ui.TextDisplay("-")
        
        self.divider = discord.ui.Separator()
        
        self.buttons = BoostStyleButtons(self)
        
        container = discord.ui.Container(
            self.section,
            self.info_userstyle,
            self.info_boostedstyle,
            self.divider,
            self.buttons
        )
        self.add_item(container)
        
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
                loop.create_task(self.validate_boost())
        except RuntimeError:
            # No running loop; ignore
            pass
        
    async def validate_boost(self) -> None:
        submit_button = self.buttons.button_boost_style
        valid = validate_booststyle_interaction_data(self)
        if valid:
            submit_button.disabled = False
        else:
            submit_button.disabled = True

@tasks.loop(count=1)
async def _update_credits_after_send(interaction: discord.Interaction, view: 'BoostStyle') -> None:
	"""Fetch credits in the background and update the view when ready."""
	credits = await get_remaining_credits()
	# Update the state and UI using the view helper
	view.set_credits(credits)
	try:
		await interaction.response.edit_message(view=view)
	except Exception:
		# The original interaction may no longer be editable; ignore silently.
		pass

async def _get_boost_style_results(interaction: discord.Interaction, view: 'BoostStyle') -> None:
    result = await boost_style(get_from_infobox(view.info_userstyle.content))
    boosted_style_text = result.get("result")
    remaining_credits = result.get("creditsRemaining")
    view.info_boostedstyle.content = send_to_infobox(str(boosted_style_text), "Boosted Style:")
    view.set_credits(str(remaining_credits))
    # reenable the button
    view.buttons.button_boost_style.disabled = False
    try:
        await interaction.response.edit_message(view=view)
    except Exception as e:
        print(f"Error fetching boost style results: {e}")
        return None
        
async def handle_booststyle_command(interaction: discord.Interaction) -> None:
    """Handle the /booststyle command."""
    # credits = await get_remaining_credits()
    view = BoostStyle()
    await interaction.response.send_message(view=view, ephemeral=False)
    try:
        _update_credits_after_send.start(interaction, view)
    except RuntimeError:
        # If already running for some reason, ignore
        pass