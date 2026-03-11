from __future__ import annotations

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("heidi.tools")


class ToolCallStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        self.register_tool(
            name="get_weather",
            description="Get current weather information for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                    },
                },
                "required": ["location"],
            },
            handler=self._get_weather,
        )

        self.register_tool(
            name="calculate",
            description="Perform mathematical calculations",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                    }
                },
                "required": ["expression"],
            },
            handler=self._calculate,
        )

        self.register_tool(
            name="get_current_time",
            description="Get current date and time for a timezone",
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone (e.g., 'UTC', 'America/New_York')",
                        "default": "UTC",
                    }
                },
            },
            handler=self._get_current_time,
        )

        self.register_tool(
            name="search_web",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=self._search_web,
        )

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable] = None,
    ):
        tool = ToolDefinition(
            name=name, description=description, parameters=parameters, handler=handler
        )
        self.tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self.tools.values()
        ]

    async def execute_tool(self, tool_call: ToolCall) -> ToolCall:
        tool = self.get_tool(tool_call.name)
        if not tool:
            tool_call.status = ToolCallStatus.FAILED
            tool_call.error = f"Tool not found: {tool_call.name}"
            return tool_call

        if not tool.handler:
            tool_call.status = ToolCallStatus.FAILED
            tool_call.error = f"Tool has no handler: {tool_call.name}"
            return tool_call

        tool_call.status = ToolCallStatus.EXECUTING
        start_time = asyncio.get_event_loop().time()

        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**tool_call.arguments)
            else:
                result = tool.handler(**tool_call.arguments)

            tool_call.result = result
            tool_call.status = ToolCallStatus.COMPLETED
        except Exception as e:
            tool_call.error = str(e)
            tool_call.status = ToolCallStatus.FAILED
            logger.error(f"Tool execution error: {e}")

        tool_call.execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return tool_call

    async def execute_tools(self, tool_calls: List[ToolCall]) -> List[ToolCall]:
        results = await asyncio.gather(*[self.execute_tool(tc) for tc in tool_calls])
        return list(results)

    # Built-in tool implementations
    @staticmethod
    def _get_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
        return {
            "location": location,
            "temperature": 22 if unit == "celsius" else 72,
            "condition": "partly cloudy",
            "humidity": 65,
            "wind_speed": 12,
            "unit": unit,
        }

    @staticmethod
    def _calculate(expression: str) -> Dict[str, Any]:
        try:
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return {"error": "Invalid characters in expression"}
            import ast

            tree = ast.parse(expression, mode="eval")
            result = eval(compile(tree, "<string>", "eval"))
            return {"expression": expression, "result": result}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
        from datetime import datetime
        import pytz

        try:
            if timezone != "UTC":
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            else:
                now = datetime.utcnow()

            return {
                "timezone": timezone,
                "datetime": now.isoformat(),
                "timestamp": int(now.timestamp()),
            }
        except Exception as e:
            return {"error": f"Invalid timezone: {e}"}

    @staticmethod
    async def _search_web(query: str, num_results: int = 5) -> Dict[str, Any]:
        # Placeholder - in production, integrate with search API
        return {
            "query": query,
            "results": [
                {"title": f"Result {i + 1} for {query}", "url": f"https://example.com/{i}"}
                for i in range(num_results)
            ],
            "total_results": num_results,
        }


# Global tool registry
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return tool_registry
