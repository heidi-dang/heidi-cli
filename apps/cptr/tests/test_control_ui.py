import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cptr.routers.control_ui import _safe_mcp_servers, get_ui_overview


class ControlUiTests(unittest.IsolatedAsyncioTestCase):
    def test_safe_mcp_servers_excludes_credentials_and_non_mcp_servers(self):
        value = [
            {
                "id": "remote",
                "name": "Remote MCP",
                "type": "mcp",
                "enabled": True,
                "url": "https://secret.example.test/mcp",
                "key": "do-not-return",
                "headers": {"Authorization": "Bearer do-not-return"},
            },
            {
                "id": "stdio",
                "name": "Local MCP",
                "type": "mcp_stdio",
                "command": "secret-command --token value",
                "enabled": False,
            },
            {"id": "openapi", "name": "Other", "type": "openapi"},
        ]

        result = _safe_mcp_servers(value)

        self.assertEqual(
            result,
            [
                {"id": "remote", "name": "Remote MCP", "type": "mcp", "enabled": True},
                {"id": "stdio", "name": "Local MCP", "type": "mcp_stdio", "enabled": False},
            ],
        )
        serialized = repr(result)
        self.assertNotIn("do-not-return", serialized)
        self.assertNotIn("secret-command", serialized)
        self.assertNotIn("secret.example.test", serialized)

    async def test_overview_reuses_scoped_control_readers_and_returns_bounded_summary(self):
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
        metrics = {
            "uptime_seconds": 123,
            "requests": {"count": 5},
            "database": {"query_count": 9},
            "event_loop": {"last_lag_ms": 1.5},
            "process": {"rss_bytes": 1000, "open_fds": 10},
        }
        with (
            patch(
                "cptr.routers.control_ui.list_workspaces",
                new=AsyncMock(
                    return_value={
                        "workspaces": [
                            {"workspace_id": "ws_1", "name": "one", "available": True, "last_used_at": 1},
                            {"workspace_id": "ws_2", "name": "two", "available": False, "last_used_at": 2},
                        ]
                    }
                ),
            ) as list_workspaces,
            patch(
                "cptr.routers.control_ui.list_models",
                new=AsyncMock(
                    return_value={
                        "models": [
                            {"model_id": "provider/default", "name": "Default", "default": True},
                            {"model_id": "provider/other", "name": "Other", "default": False},
                        ]
                    }
                ),
            ) as list_models,
            patch("cptr.routers.control_ui.database_ready", new=AsyncMock(return_value=True)),
            patch("cptr.routers.control_ui.authenticate_control_request", new=AsyncMock(return_value="user-1")),
            patch(
                "cptr.routers.control_ui.mcp_usage_store.summary",
                new=AsyncMock(
                    return_value={
                        "week": {"requests": 4, "total_tokens_estimated": 1200, "simulated_cost_usd": "0.012"},
                        "month": {"requests": 9, "total_tokens_estimated": 3600, "simulated_cost_usd": "0.036"},
                    }
                ),
            ),
            patch(
                "cptr.routers.control_ui.mcp_usage_store.engineering_sessions",
                new=AsyncMock(return_value={"comparable": False, "sessions": []}),
            ),
            patch(
                "cptr.routers.control_ui.coding_benchmark_store.leaderboard",
                new=AsyncMock(return_value={"comparable": True, "suite_id": "cptr-python-core", "models": []}),
            ),
            patch("cptr.routers.control_ui.runtime_metrics.snapshot", return_value=metrics),
            patch(
                "cptr.routers.control_ui.Config.get",
                new=AsyncMock(
                    return_value=[
                        {
                            "id": "server_1",
                            "name": "Tools",
                            "type": "mcp",
                            "enabled": True,
                            "url": "https://private.example.test/mcp",
                            "key": "private-key",
                        }
                    ]
                ),
            ),
        ):
            result = await get_ui_overview(request)

        list_workspaces.assert_awaited_once_with(request, include_unavailable=True)
        list_models.assert_awaited_once_with(request)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["workspaces"]["count"], 2)
        self.assertEqual(result["workspaces"]["available"], 1)
        self.assertEqual(result["models"]["default_model"], "provider/default")
        self.assertEqual(result["mcp_servers"]["count"], 1)
        self.assertEqual(result["mcp_usage"]["week"]["requests"], 4)
        self.assertEqual(result["mcp_usage"]["month"]["requests"], 9)
        self.assertFalse(result["engineering"]["comparable"])
        self.assertTrue(result["coding_benchmark"]["comparable"])
        self.assertEqual(result["system"]["uptime_seconds"], 123)
        serialized = repr(result)
        self.assertNotIn("private-key", serialized)
        self.assertNotIn("private.example.test", serialized)
        self.assertIn("a4a3a02251312e5f5c04b910d1e11857323b0ab5", serialized)
