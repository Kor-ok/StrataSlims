import io
from typing import Optional

import discord
import aiohttp

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

