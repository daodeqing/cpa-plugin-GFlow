"""Show only known account health evidence; enabled status and cached balance do not prove availability."""
from collections.abc import Mapping
from datetime import datetime, timezone
import time


def _value(token, name, default=None):
    return token.get(name, default) if isinstance(token, Mapping) else getattr(token, name, default)


def _as_utc(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def account_health(token, *, now=None, recent_validation_expires=0.0,
                   monotonic_now=None, validation_failure=None):
    """Build credential-free display status from the account snapshot and this process's successful verification TTL.

    at_expires is the next verification time, not confirmed Google Cookie expiration.
    Only an explicit persisted session_expired reason indicates an expired login session; network, browser,
    risk checks and ordinary refresh failures still require verification, never an inferred account expiration.
    """
    now = _as_utc(now) or datetime.now(timezone.utc)
    tick = time.monotonic() if monotonic_now is None else monotonic_now
    ban = str(_value(token, "ban_reason", "") or "").strip()
    enabled = bool(_value(token, "is_active", False)) and not ban
    checked = _as_utc(_value(token, "last_st_refresh_at"))

    def state(code, label, level, detail, verified=False):
        return {
            "code": code, "label": label, "level": level, "detail": detail,
            "enabled": enabled, "verified": verified,
            "checked_at": checked.isoformat() if checked else None,
        }

    if ban == "session_expired":
        return state("session_expired", "Login session expired", "danger",
                     "Google explicitly rejected the saved login session. Sync again through the login helper.")
    if ban:
        label = "Rate limited" if ban == "429_rate_limit" else "Account banned"
        return state("rate_limited" if ban == "429_rate_limit" else "blocked",
                     label, "danger", "The backend banned this account. Check request errors and the ban reason.")
    if not enabled:
        return state("disabled", "Manually disabled", "warning", "The account switch is off.")

    # The caller's latest verification failure overrides the old TTL without exposing Cookie/URL details from the raw error.
    if validation_failure:
        return state("refresh_failed", "Verification required", "warning",
                     "The latest login verification or refresh failed. Retry and check request errors; this does not establish account expiration.")
    try:
        recently_verified = float(recent_validation_expires or 0) > float(tick)
    except (TypeError, ValueError):
        recently_verified = False
    if recently_verified:
        return state("verified", "Login verified", "success",
                     "Google login was verified recently; generation still depends on credits, captcha, and upstream responses.", True)

    refresh_result = str(_value(token, "last_st_refresh_result", "") or "").strip()
    if refresh_result and refresh_result.lower() not in {"success", "ok", "成功"}:  # zh-compat: legacy persisted last_st_refresh_result
        return state("refresh_failed", "Verification required", "warning",
                     "The latest login verification or refresh failed. Retry and check request errors; this does not establish account expiration.")
    expires = _as_utc(_value(token, "at_expires"))
    if expires and expires <= now:
        return state("verification_due", "Verification due", "warning",
                     "Login session verification is due. Expiration is not confirmed; cached credits do not prove availability.")
    return state("unverified", "Enabled - Unverified", "warning",
                 "The account is enabled but has no recent successful verification; cached credits do not prove availability.")


def summarize_account_health(tokens, health_by_id=None):
    """Summarize enabled accounts, recently verified accounts, and cached credits with clear legacy field semantics."""
    health_by_id = health_by_id or {}
    tokens = list(tokens)
    enabled = verified = cached_credits = 0
    for token in tokens:
        health = health_by_id.get(_value(token, "id")) or account_health(token)
        enabled += int(bool(health["enabled"]))
        verified += int(bool(health["verified"]))
        if health["enabled"]:
            try:
                cached_credits += max(0, int(_value(token, "credits", 0) or 0))
            except (TypeError, ValueError):
                pass
    return {
        "total_tokens": len(tokens), "enabled_tokens": enabled,
        "verified_tokens": verified, "active_tokens": verified,
        "cached_credits": cached_credits, "total_credits": cached_credits,
        "credits_are_cached": True,
    }
