"""Public generation failures shared by JSON and streaming worker responses."""
import json


def generation_error(payload):
    """Return a worker error envelope without treating failed SSE as success."""
    if isinstance(payload, str):
        text = payload.strip()
        if text.startswith("data:"):
            text = text[5:].strip()
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            return None
    if not isinstance(payload, dict) or not payload.get("error"):
        return None
    raw = payload["error"]
    error = dict(raw) if isinstance(raw, dict) else {"message": str(raw)}
    message = str(error.get("message") or "Google Flow generation failed")
    status = error.get("status_code", 502)
    try:
        status = int(status)
    except (ValueError, TypeError):
        status = 502
    if not 400 <= status <= 599:
        status = 502
    code = error.get("code") or "gflow_generation_failed"
    if "PUBLIC_ERROR_UNUSUAL_ACTIVITY" in message:
        code, status = "gflow_unusual_activity", 403
        message = ("Google Flow rejected this request (unusual activity, PUBLIC_ERROR_UNUSUAL_ACTIVITY). "
                   "Check the account status on a logged-in Flow page; no automatic retry was made.")
    elif any(marker in message for marker in ("Google Cookie 已失效", "Flow 登录已失效", "Google Cookie expired", "Flow login expired", "gflow_session_expired")):  # zh-compat: pinned flow_frontend.py and browser_captcha.py; English from load_balancer.py and browser_captcha_personal.py
        code, status = "gflow_session_expired", 401
        message = "The GFlow Google login session expired. Sync Cookies again through the login helper in a logged-in Flow browser; changing only the EasyCPA address or key cannot restore it."
    return {"message": message, "status_code": status,
            "type": error.get("type") or "generation_error", "code": code}


def account_pool_error(tokens):
    """Keep an empty pool separate from a disabled or expired account."""
    if not tokens:
        return {"message": "No GFlow accounts. Add or sync a Google Flow account in the GFlow plugin console first",
                "type": "no_active_tokens", "code": "gflow_empty_account_pool", "status_code": 503}
    if any(getattr(t, "ban_reason", None) == "session_expired" for t in tokens):
        return generation_error({"error": {"message": "gflow_session_expired"}})
    return {"message": "The GFlow account is disabled. Check its status in the plugin console; sync Google Cookies again if the login expired, or enable the account if it was manually disabled.",
            "type": "no_active_tokens", "code": "gflow_accounts_disabled", "status_code": 503}
