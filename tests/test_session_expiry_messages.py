"""GFlow's own English login-expiry messages must still classify as session expiry."""
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python/flow2api"))
from generation_errors import generation_error
from src.services.load_balancer import LoadBalancer

PERSONAL_BROWSER_EXPIRY = "Flow login expired; sync Google Cookies again"


class SessionExpiryMessageTests(unittest.TestCase):
    def test_personal_browser_still_raises_the_matched_message(self):
        source = (ROOT / "python/flow2api/src/services/browser_captcha_personal.py").read_text(encoding="utf-8")
        self.assertIn(f'raise RuntimeError("{PERSONAL_BROWSER_EXPIRY}")', source)

    def test_english_expiry_messages_are_session_expired(self):
        balancer = LoadBalancer.__new__(LoadBalancer)
        balancer.token_manager = SimpleNamespace(get_active_tokens=AsyncMock(return_value=[]),
            get_all_tokens=AsyncMock(return_value=[SimpleNamespace(ban_reason="session_expired")]))
        pool_reason = asyncio.run(balancer.get_unavailable_reason())
        for message in (pool_reason, "RuntimeError: " + PERSONAL_BROWSER_EXPIRY):
            self.assertEqual(generation_error({"error": {"message": message}})["code"], "gflow_session_expired", message)


if __name__ == "__main__":
    unittest.main()
