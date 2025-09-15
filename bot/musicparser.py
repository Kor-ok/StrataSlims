from discord.ui import LayoutView

from config import get_webhook

webhook_bot = get_webhook("WEBHOOK_BOT")
webhook_send_to = get_webhook("WEBHOOK_SEND_TO")

def send_to_infobox(text: str, prefix: str) -> str:
    return f"{prefix} {text}"

def get_from_infobox(text: str) -> str:
    # Remove anything before the first colon and trim whitespace
    if ':' in text:
        return text.split(':', 1)[1].strip()
    return text.strip()

def get_gender_from_infobox(text: str) -> str:
    if 'Male' in text:
        return 'm'
    elif 'Female' in text:
        return 'f'
    elif 'Surprise' in text:
        return ''
    return ''  # Default to nothing

def get_float_from_infobox(text: str) -> str:
    # Extract float value from the text
    # Apply normalization if needed
    # Convert to string for payload
    try:
        value = float(get_from_infobox(text))
        # Normalize to 0.00 - 1.00 range if needed
        # Must be a multiple of 0.01
        value = round(value, 2)
        if value < 0.00:
            value = 0.00
        elif value > 1.00:
            value = 1.00
        return f"{value:.2f}"
    except ValueError:
        return "0.65"

def validate_song_interaction_data(view: LayoutView) -> bool:
    # Check if all required fields are filled
    
    mandatory_fields_filled = all([
        get_from_infobox(view.info_title.content) != '', # type: ignore
        get_from_infobox(view.info_style.content) != '', # type: ignore
        get_from_infobox(view.info_lyrics.content) != '', # type: ignore
    ])

    return mandatory_fields_filled

def  validate_booststyle_interaction_data(view: LayoutView) -> bool:
    # Check if all required fields are filled
    
    mandatory_fields_filled = all([
        get_from_infobox(view.info_userstyle.content) != '', # type: ignore
    ])

    return mandatory_fields_filled

def build_music_payload(view: LayoutView) -> dict:
    # Helper to decide if a field is effectively empty / placeholder
    def _is_empty(raw: str) -> bool:
        return raw == '-' or get_from_infobox(raw) == ''
    
    # Logic for using either info_style or info_boosted_style
    # If info_boosted_style is not '-' and not empty, use it instead of info_style
    style_raw = view.info_style.content  # type: ignore
    boosted_style_raw = view.info_boosted_style.content  # type: ignore
    if not _is_empty(boosted_style_raw):
        style_raw = boosted_style_raw
        
    # Build required payload keys first
    payload: dict = {
        "prompt": get_from_infobox(view.info_lyrics.content),  # type: ignore
        "style": get_from_infobox(style_raw),    # type: ignore
        "title": get_from_infobox(view.info_title.content),    # type: ignore
        "customMode": True,
        "instrumental": False,
        "model": "V4_5PLUS",
        "callBackUrl": webhook_bot,
    }


    # Optional: negativeTags
    neg_raw = view.info_negatives.content  # type: ignore
    if not _is_empty(neg_raw):
        payload["negativeTags"] = get_from_infobox(neg_raw)

    # Optional: vocalGender
    gender_raw = view.info_gender.content  # type: ignore
    if not _is_empty(gender_raw):
        gender_val = get_gender_from_infobox(gender_raw)
        if gender_val:  # only include if maps to m/f
            payload["vocalGender"] = gender_val

    # Optional numeric weights
    style_w_raw = view.info_style_weight.content  # type: ignore
    if not _is_empty(style_w_raw):
        payload["styleWeight"] = float(get_float_from_infobox(style_w_raw))

    weird_w_raw = view.info_weirdness_weight.content  # type: ignore
    if not _is_empty(weird_w_raw):
        payload["weirdnessConstraint"] = float(get_float_from_infobox(weird_w_raw))

    audio_w_raw = view.info_audio_weight.content  # type: ignore
    if not _is_empty(audio_w_raw):
        payload["audioWeight"] = float(get_float_from_infobox(audio_w_raw))

    return payload

def build_booststyle_payload(view: LayoutView) -> dict:
    payload = {
        "content": get_from_infobox(view.info_style.content),  # type: ignore
    }
    return payload

__all__ = ["send_to_infobox", 
           "get_from_infobox",
            "validate_song_interaction_data",
            "build_music_payload",
            "build_booststyle_payload",
           ]