"""
Gemini client helpers.
"""
from __future__ import annotations

import os

DEAD_LOCAL_PROXY = "http://127.0.0.1:9"
GEMINI_TIMEOUT_SECONDS = 12
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip().strip("\"'")


def clear_dead_local_proxy() -> None:
    """
    Some sandboxed shells set proxy variables to 127.0.0.1:9, which makes the
    Gemini SDK wait on an intentionally closed local port. Remove only that
    sentinel value and leave any real user proxy untouched.
    """
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if os.environ.get(name) == DEAD_LOCAL_PROXY:
            os.environ.pop(name, None)


def configure_gemini():
    api_key = get_gemini_api_key()
    if not api_key:
        return None

    clear_dead_local_proxy()

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    return genai.GenerativeModel(model_name)
