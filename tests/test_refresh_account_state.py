"""Refresh failure must not silently disable a healthy account."""
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python/flow2api"))
from src.services.token_manager import TokenManager


class RefreshStateTests(unittest.IsolatedAsyncioTestCase):
    async def run_failure(self, reason, protocol_error=None):
        token = SimpleNamespace(id=1, st="fake", google_cookies="fake",
                                last_st_refresh_result="RuntimeError: Account browser tab unavailable")
        manager = TokenManager.__new__(TokenManager)
        manager._refresh_locks = {}
        manager._refresh_lock_guard = asyncio.Lock()
        manager._get_token_lock = AsyncMock(return_value=asyncio.Lock())
        manager.db = SimpleNamespace(get_token=AsyncMock(return_value=token),
                                     update_token=AsyncMock())
        manager._do_refresh_at = AsyncMock(return_value=False)
        manager._try_refresh_st = AsyncMock(return_value=None)
        manager._last_at_refresh_error = {1: reason}
        manager._clear_at_validation_cache = Mock()
        manager.flow_client = SimpleNamespace()
        if protocol_error is None:
            self.assertFalse(await manager._refresh_at_inner(1))
            return manager

        del manager._try_refresh_st
        token.proxy_url = None
        token.login_account = token.email = "account@example.com"
        token.current_project_id = "project"
        token.is_active = True
        token.ban_reason = None
        token.last_st_refresh_result = None

        async def update_token(token_id, **changes):
            self.assertEqual(token_id, token.id)
            for key, value in changes.items():
                setattr(token, key, value)

        async def update_if_cookie_matches(token_id, cookies, **changes):
            self.assertEqual(cookies, token.google_cookies)
            await update_token(token_id, **changes)
            return True

        manager.db.update_token.side_effect = update_token
        manager.db.update_token_if_cookie_matches = AsyncMock(
            side_effect=update_if_cookie_matches)
        browser = SimpleNamespace(refresh_google_cookies=AsyncMock(
            side_effect=RuntimeError("The account browser tab is unavailable")))
        with patch("src.services.token_manager.config", captcha_method="personal"), \
             patch("src.services.protocol_login.protocol_loginer.login",
                   new=AsyncMock(side_effect=RuntimeError(protocol_error))) as login, \
             patch("src.services.browser_captcha_personal.BrowserCaptchaService.get_instance",
                   new=AsyncMock(return_value=browser)):
            self.assertFalse(await manager._refresh_at_inner(1))
        login.assert_awaited_once_with(
            "fake", proxy=None, email="account@example.com")
        browser.refresh_google_cookies.assert_awaited_once_with("project", token_id=1)
        return manager

    async def test_logged_out_protocol_verdict_survives_browser_failure(self):
        protocol_error = "Flow 页面未返回已登录账号，请重新同步 Google Cookies"  # zh-compat: pinned protocol_login.py logged-out verdict
        manager = await self.run_failure(
            "Flow frontend RPC rejected: PUBLIC_ERROR_UNUSUAL_ACTIVITY", protocol_error)
        token = await manager.db.get_token(1)
        self.assertFalse(token.is_active)
        self.assertEqual(token.ban_reason, "session_expired")
        self.assertIn("未返回已登录账号", token.last_st_refresh_result)  # zh-compat: pinned protocol_login.py logged-out verdict
        self.assertIn("browser fallback: RuntimeError: The account browser tab is unavailable",
                      token.last_st_refresh_result)

    async def test_non_auth_protocol_and_browser_failures_keep_account_enabled(self):
        protocol_error = "Flow frontend RPC rejected: PUBLIC_ERROR_UNUSUAL_ACTIVITY"
        manager = await self.run_failure(protocol_error, protocol_error)
        token = await manager.db.get_token(1)
        self.assertTrue(token.is_active)
        self.assertIsNone(token.ban_reason)
        manager.db.update_token.assert_not_awaited()

    async def test_browser_failure_keeps_account_enabled(self):
        manager = await self.run_failure("Flow frontend RPC rejected: PUBLIC_ERROR_UNUSUAL_ACTIVITY")
        manager.db.update_token.assert_not_awaited()

    async def test_expired_session_records_precise_reason(self):
        manager = await self.run_failure("FlowBootstrapError: Flow 登录认证失败：Google Cookie 已失效")  # zh-compat: simulates pinned flow_frontend.py text
        change = manager.db.update_token.await_args.kwargs
        self.assertFalse(change["is_active"])
        self.assertEqual(change["ban_reason"], "session_expired")

    async def test_personal_browser_login_expiry_records_session_expired(self):
        manager = await self.run_failure("RuntimeError: Flow login expired; sync Google Cookies again")
        self.assertEqual(manager.db.update_token.await_args.kwargs["ban_reason"], "session_expired")
