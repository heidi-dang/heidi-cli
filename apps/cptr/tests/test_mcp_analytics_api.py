import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cptr.routers import mcp_analytics as analytics
from cptr.services.mcp_usage_models import McpUsageDiagnostic


def request():
    return SimpleNamespace(
        headers={"Authorization": "Bearer token"}, cookies={}, client=None, state=SimpleNamespace()
    )


def usage(event_id: str = "usage-1") -> McpUsageDiagnostic:
    return McpUsageDiagnostic(
        event_id=event_id,
        timestamp_ms=1_788_000_000_000,
        request_id="request-1",
        correlation_id="correlation-1",
        session_id="session-1",
        client_id="chatgpt",
        model_reported="GPT-5.6 Sol",
        model_canonical="gpt-5.6-sol",
        model_source="self_reported",
        tool_name="cptr_code_read",
        input_tokens_estimated=100,
        output_tokens_estimated=20,
        cached_input_tokens_estimated=None,
        estimator_method="utf8-byte-estimate",
        estimator_exact_for_model=False,
        status="complete",
    )


class McpAnalyticsApiTests(unittest.IsolatedAsyncioTestCase):
    def test_routes_are_versioned_control_api(self):
        paths = {route.path for route in analytics.router.routes if hasattr(route, "path")}
        self.assertIn("/api/control/v1/mcp/analytics/usage/events", paths)
        self.assertIn("/api/control/v1/mcp/analytics/usage/summary", paths)
        self.assertIn("/api/control/v1/mcp/analytics/engineering/sessions", paths)

    async def test_ingest_is_owner_scoped_and_reports_duplicate(self):
        event = usage()
        store = SimpleNamespace(ingest=AsyncMock(return_value=set()))
        with (
            patch.object(analytics, "_user", new=AsyncMock(return_value="user-1")),
            patch.object(analytics, "mcp_usage_store", store),
        ):
            result = await analytics.ingest_usage_event(request(), event)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["duplicate"])
        store.ingest.assert_awaited_once_with("user-1", [event])

    async def test_summary_and_engineering_are_read_scoped(self):
        summary = {"week": {"requests": 2}, "month": {"requests": 3}}
        sessions = {"comparable": False, "sessions": []}
        store = SimpleNamespace(
            summary=AsyncMock(return_value=summary),
            engineering_sessions=AsyncMock(return_value=sessions),
        )
        auth = AsyncMock(return_value="user-1")
        with (
            patch.object(analytics, "_user", new=auth),
            patch.object(analytics, "mcp_usage_store", store),
        ):
            self.assertEqual(await analytics.get_usage_summary(request()), summary)
            self.assertEqual(await analytics.get_engineering_sessions(request(), limit=25), sessions)
        self.assertEqual(auth.await_args_list[0].args[1], "task:read")
        self.assertEqual(auth.await_args_list[1].args[1], "task:read")
        store.engineering_sessions.assert_awaited_once_with("user-1", limit=25)


if __name__ == "__main__":
    unittest.main()
