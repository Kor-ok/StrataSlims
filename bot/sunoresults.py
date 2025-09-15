"""Utility script to extract fields from the mock Suno API result log.

The existing log file is NOT valid JSON (single quotes, Python literals, extra
duplicated / truncated garbage after the first full dict). We therefore:
 1. Read the file as text.
 2. Slice out the first complete top-level brace-balanced dictionary.
 3. Safely parse it with ast.literal_eval (handles Python literals + None).
 4. Extract useful fields and print them in a concise, structured way.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

LOG_FILE = Path("mockresult.log")

@dataclass
class Track:
    id: str
    title: str
    model: str
    duration: float | None
    audio_url: str | None
    source_audio_url: str | None
    stream_audio_url: str | None
    image_url: str | None
    prompt_snippet: str | None
    tags: str | None


def _extract_first_brace_block(text: str) -> str:
    """Return the substring containing the first complete top-level { } block.

    We walk the text, tracking brace depth while respecting simple string spans.
    This is a lightweight tolerant parser; if it fails we fall back to the full text.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_str = False
    str_char = ''
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == str_char:
                in_str = False
        else:
            if ch in ('"', "'"):
                in_str = True
                str_char = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    # Include this closing brace
                    return text[start : i + 1]
    # If we never balanced, return whole text (will likely fail to parse)
    return text


def parse_log_dict(text: str) -> Dict[str, Any]:
    block = _extract_first_brace_block(text)
    try:
        return ast.literal_eval(block)  # type: ignore[no-any-return]
    except Exception as e:
        raise ValueError(f"Failed to parse log content as Python literal: {e}")


def build_tracks(data: Dict[str, Any]) -> List[Track]:
    tracks: List[Track] = []
    try:
        suno_list = data["data"]["response"].get("sunoData") or []
    except Exception:
        return tracks
    for item in suno_list:
        if not isinstance(item, dict):
            continue
        prompt = item.get("prompt")
        if isinstance(prompt, str):
            # Keep only first 80 chars for readability
            prompt_snippet = (prompt[:77] + "...") if len(prompt) > 80 else prompt
        else:
            prompt_snippet = None
        tracks.append(
            Track(
                id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                model=str(item.get("modelName", "")),
                # Extract duration with an intermediate variable to satisfy type checkers
                duration=(
                    float(dur)  # type: ignore[arg-type]
                    if isinstance((dur := item.get("duration")), (int, float))
                    else None
                ),
                audio_url=item.get("audioUrl"),
                source_audio_url=item.get("sourceAudioUrl"),
                stream_audio_url=item.get("streamAudioUrl"),
                image_url=item.get("imageUrl"),
                prompt_snippet=prompt_snippet,
                tags=item.get("tags"),
            )
        )
    return tracks


def summarize(parsed: Dict[str, Any]) -> None:
    data = parsed.get("data", {})
    response = data.get("response", {})
    print("=== Summary ===")
    print(f"Code: {parsed.get('code')} | Msg: {parsed.get('msg')}")
    print(f"Top Task ID: {data.get('taskId')}")
    print(f"Response Task ID: {response.get('taskId')}")
    print(f"Status: {response.get('status') or parsed.get('status')}")
    print(f"Type: {parsed.get('type')} | Operation: {parsed.get('operationType')}")
    # Param field may itself be JSON string; attempt a lightweight detection
    raw_param = data.get('param')
    if isinstance(raw_param, str) and raw_param.startswith('{') and raw_param.endswith('}'):
        # Try JSON parse; if fails just show length
        import json
        try:
            param_obj = json.loads(raw_param)
            print("Param keys:", ', '.join(param_obj.keys()))
        except Exception:
            print(f"Param: <embedded JSON-like string length={len(raw_param)}> (parse failed)")
    tracks = build_tracks(parsed)
    print(f"Tracks found: {len(tracks)}")
    for idx, t in enumerate(tracks, start=1):
        print(f"  [{idx}] {t.title} ({t.model}) {t.duration or '?'}s")
        print(f"       id={t.id}")
        print(f"       audio={t.audio_url}")
        print(f"       stream={t.stream_audio_url}")
        print(f"       image={t.image_url}")
        if t.prompt_snippet:
            print(f"       prompt='{t.prompt_snippet}'")
        if t.tags:
            print(f"       tags='{t.tags}'")
            
def extract(parsed: Dict[str, Any]) -> None:
        status = parsed.get("data", {}).get("status")
        print(status)
        code = parsed.get("code")
        print(code)
        message = parsed.get("msg")
        print(message)
        taskId = parsed.get("data", {}).get("taskId")
        print(taskId)
        song_ids = []
        tracks = build_tracks(parsed)
        for track in tracks:
            song_ids.append(track.id)
        print("Song IDs:", song_ids)
        song_titles = []
        for track in tracks:
            song_titles.append(track.title)
        print("Song Titles:", song_titles)
        song_audio_urls = []
        for track in tracks:
            song_audio_urls.append(track.audio_url)
        print("Song Audio URLs:", song_audio_urls)
        song_image_urls = []
        for track in tracks:
            song_image_urls.append(track.image_url)
        print("Song Image URLs:", song_image_urls)
        song_durations = []
        for track in tracks:
            song_durations.append(track.duration)
        # Duration in Minutes and Seconds
        song_durations = [f"{int(d // 60)}m {int(d % 60)}s" if d is not None else "Unknown" for d in song_durations]    
        print("Song Durations:", song_durations)


def main() -> None:
        # Clear terminal
        print("\033c", end="")
        if not LOG_FILE.exists():
                raise SystemExit(f"Log file not found: {LOG_FILE}")
        text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
        try:
                parsed = parse_log_dict(text)
        except ValueError as e:
                print(e)
                return
        #     summarize(parsed)
        extract(parsed)

if __name__ == "__main__":
    main()