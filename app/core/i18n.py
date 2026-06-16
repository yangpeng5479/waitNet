"""Language detection and application naming helpers."""

from __future__ import annotations

import locale
def detect_app_language() -> str:
    """Return one of: zh, en, ar. Default to zh."""
    loc = locale.getdefaultlocale()[0] if locale.getdefaultlocale() else ""
    lowered = (loc or "").lower()
    if lowered.startswith("zh"):
        return "zh"
    if lowered.startswith("en"):
        return "en"
    if lowered.startswith("ar"):
        return "ar"
    return "zh"


def app_display_name(lang: str) -> str:
    return {
        "zh": "音频压缩",
        "en": "Audio Compressor",
        "ar": "ضاغط الصوت",
    }.get(lang, "Audio Compressor")
