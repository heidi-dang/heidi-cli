from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger("heidi.structured")


class OutputFormat(Enum):
    JSON = "json"
    JSON_OBJECT = "json_object"
    XML = "xml"
    MARKDOWN = "markdown"


@dataclass
class ResponseFormat:
    type: str
    schema: Optional[Dict[str, Any]] = None
    strict: bool = True


class StructuredOutputGenerator:
    def __init__(self):
        self.json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
        self.json_object_pattern = re.compile(r"\{[^{}]*\}")

    def parse_json_response(
        self, text: str, schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            text = text.strip()

            if text.startswith("```json"):
                match = self.json_pattern.search(text)
                if match:
                    text = match.group(1)
            elif text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)

            if schema and self._validate_schema(data, schema):
                return {"success": True, "data": data, "validated": True}
            elif schema:
                return {
                    "success": True,
                    "data": data,
                    "validated": False,
                    "warning": "Schema validation failed",
                }

            return {"success": True, "data": data}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {"success": False, "error": f"Invalid JSON: {str(e)}", "raw": text}
        except Exception as e:
            logger.error(f"Structured output error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        try:
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            for field in required:
                if field not in data:
                    logger.warning(f"Missing required field: {field}")
                    return False

            for field, value in data.items():
                if field in properties:
                    expected_type = properties[field].get("type")
                    if not self._check_type(value, expected_type):
                        logger.warning(f"Type mismatch for {field}: expected {expected_type}")
                        return False

            return True
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False

    def _check_type(self, value: Any, expected_type: Optional[str]) -> bool:
        if expected_type is None:
            return True

        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True

        return isinstance(value, expected_python_type)

    def generate_json_prompt(self, schema: Dict[str, Any], prompt: str) -> str:
        schema_str = json.dumps(schema, indent=2)

        return f"""{prompt}

IMPORTANT: Your response MUST be valid JSON matching this schema:
```json
{schema_str}
```

Respond ONLY with JSON. No additional text."""

    def extract_structured_data(self, text: str, format_type: OutputFormat) -> Dict[str, Any]:
        if format_type == OutputFormat.JSON or format_type == OutputFormat.JSON_OBJECT:
            return self.parse_json_response(text)

        elif format_type == OutputFormat.XML:
            return self._parse_xml(text)

        elif format_type == OutputFormat.MARKDOWN:
            return self._parse_markdown(text)

        return {"success": False, "error": f"Unsupported format: {format_type}"}

    def _parse_xml(self, text: str) -> Dict[str, Any]:
        try:
            data = {}
            pattern = re.compile(r"<(\w+)>(.*?)</\1>")
            for match in pattern.finditer(text):
                key, value = match.groups()
                data[key] = value.strip()
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": f"XML parse error: {e}"}

    def _parse_markdown(self, text: str) -> Dict[str, Any]:
        try:
            lines = text.strip().split("\n")
            data = {}
            current_key = None
            current_value = []

            for line in lines:
                if line.startswith("## "):
                    current_key = line[3:].strip().lower().replace(" ", "_")
                elif line.startswith("- ") and current_key:
                    current_value.append(line[2:].strip())

            if current_key:
                data[current_key] = (
                    current_value
                    if len(current_value) > 1
                    else current_value[0]
                    if current_value
                    else ""
                )

            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": f"Markdown parse error: {e}"}


structured_generator = StructuredOutputGenerator()


def get_structured_generator() -> StructuredOutputGenerator:
    return structured_generator
