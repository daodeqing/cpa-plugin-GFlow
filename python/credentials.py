"""Parse pasted account data without accessing Google or exposing credentials."""
import json
from urllib.parse import unquote

from src.services.browser_cookie_utils import (
    extract_session_token_from_cookie_payload,
    normalize_cookie_header_text,
    normalize_cookie_storage_text,
    parse_browser_cookie_payload,
)


def normalize_account_input(st=None, google_cookies=None):
    """Return (Session Token, complete Cookie) to avoid sending a Cookie string upstream as an ST."""
    explicit_st = str(st or "").strip()
    raw = google_cookies if google_cookies is not None else ""
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith(("{", "[")):
            try:
                raw = json.loads(raw)
            except ValueError:
                raise ValueError("Invalid Cookie JSON format; copy the complete content again") from None
    if isinstance(raw, dict) and any(k in raw for k in ("st", "google_cookies", "cookies")):
        explicit_st = explicit_st or str(raw.get("st") or "").strip()
        raw = raw.get("google_cookies", raw.get("cookies", ""))
    if isinstance(raw, (dict, list)):
        cookie_text = normalize_cookie_storage_text(raw)
    else:
        cookie_text = normalize_cookie_header_text(str(raw or ""))
        if cookie_text and "=" not in cookie_text:
            explicit_st = explicit_st or cookie_text
            cookie_text = ""
    if cookie_text:
        if chr(10) in cookie_text or chr(13) in cookie_text:
            raise ValueError("Copy only the Cookie value, not the entire request")
        parsed = parse_browser_cookie_payload(cookie_text)
        if not parsed:
            raise ValueError("No Cookie recognized; check that you copied the Cookie request header value")
        explicit_st = explicit_st or extract_session_token_from_cookie_payload(cookie_text)
    if not explicit_st and not cookie_text:
        raise ValueError("Paste a Cookie or Session Token")
    return unquote(explicit_st), cookie_text
