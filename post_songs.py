import io
import traceback
from typing import Optional, cast

import discord
import aiohttp

from sunoapi import get_task_results

class Songs(discord.ui.LayoutView):
    def __init__(self, task_id: str, results: dict, user_id: int,
                 audio1_ref: str,
                 audio2_ref: str):
        super().__init__()
        self.timeout = None
        self.task_id = task_id
        self.results = results
        self.user_id = user_id

        # === Section: SONG 1 =================
        self.infobox1 = discord.ui.TextDisplay(f"## {self.results['song_title_1']}")
        self.thumbnail1 = discord.ui.Thumbnail(
            media=f'{self.results["song_image_url_1"]}'
        )
        self.section1 = discord.ui.Section(
            self.infobox1,
            accessory=self.thumbnail1
        )
        self.audio_1 = discord.ui.File(media=audio1_ref)
        # ====================================
        
        self.divider = discord.ui.Separator()
        
        # === Section: SONG 2 ================
        self.infobox2 = discord.ui.TextDisplay(f"## {self.results['song_title_2']}")
        self.thumbnail2 = discord.ui.Thumbnail(
            media=f'{self.results["song_image_url_2"]}'
        )
        self.section2 = discord.ui.Section(
            self.infobox2,
            accessory=self.thumbnail2
        )
        self.audio_2 = discord.ui.File(media=audio2_ref)
        # ====================================

        container = discord.ui.Container(
            self.section1,
            self.audio_1,
            self.divider,
            self.section2,
            self.audio_2
        )
        self.add_item(container)


async def url_to_file(url: str, filename: str, *, max_bytes: int = 8 * 1024 * 1024) -> Optional[discord.File]:
    """Download URL and return a discord.File if within size; else None.
    Streams the body and enforces the limit without trusting Content-Length.
    """
    # Ensure filename has an audio extension for Discord's player
    if '.' not in filename:
        filename = filename + '.mp3'
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            # Adjust extension based on content type when possible
            ctype = (resp.headers.get('Content-Type') or '').split(';', 1)[0].strip().lower()
            if ctype and (filename.endswith('.mp3') or '.' not in filename):
                if ctype == 'audio/mpeg':
                    if not filename.endswith('.mp3'):
                        filename = filename.rsplit('.', 1)[0] + '.mp3'
                elif ctype == 'audio/wav' or ctype == 'audio/x-wav':
                    filename = filename.rsplit('.', 1)[0] + '.wav'
                elif ctype == 'audio/ogg' or ctype == 'application/ogg':
                    filename = filename.rsplit('.', 1)[0] + '.ogg'
                elif ctype == 'audio/mp4' or ctype == 'video/mp4':
                    filename = filename.rsplit('.', 1)[0] + '.mp4'
            buf = io.BytesIO()
            async for chunk in resp.content.iter_chunked(128 * 1024):
                buf.write(chunk)
                if buf.tell() > max_bytes:
                    return None
    buf.seek(0)
    return discord.File(buf, filename=filename)

async def handle_post_songs_command(
    interaction: discord.Interaction,
    task_id: str) -> None:

    # Defer immediately to avoid 3s timeout while fetching/downloading
    try:
        await interaction.response.defer(thinking=True, ephemeral=False)
    except Exception:
        # If already deferred or responded, continue
        pass

    try:
        task_results = await get_task_results(task_id)
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        await interaction.followup.send("Failed to fetch task results.", ephemeral=True)
        return
    if not task_results:
        await interaction.followup.send("No results found.", ephemeral=True)
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
    else:
        file_refs.append(None)
    if file2 is not None:
        files.append(file2)
        file_refs.append(f"attachment://{file2.filename}")
    else:
        file_refs.append(None)

    view = Songs(
        task_id=results["task_id"],
        results=dict(results),
        user_id=interaction.user.id,
        audio1_ref=file_refs[0],
        audio2_ref=file_refs[1],
    )

    if files:
        await interaction.followup.send(view=cast(discord.ui.View, view), files=files, ephemeral=False)
    else:
        # Fallback to links embedded in the view's TextDisplays
        await interaction.followup.send(view=cast(discord.ui.View, view), ephemeral=False)