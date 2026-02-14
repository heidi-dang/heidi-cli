from __future__ import annotations


PERSONAS = {
    "default": {
        "system_prefix": "You are a helpful coding assistant.",
        "review_focus": "code quality, correctness",
        "risk_tolerance": "medium",
    },
    "security": {
        "system_prefix": "You are a security-focused coding assistant. Prioritize security in all decisions.",
        "review_focus": "security vulnerabilities, authentication, authorization, data protection",
        "risk_tolerance": "low",
    },
    "docs": {
        "system_prefix": "You are a documentation-focused coding assistant. Prioritize clear documentation.",
        "review_focus": "documentation completeness, clarity, examples",
        "risk_tolerance": "medium",
    },
    "refactor": {
        "system_prefix": "You are a refactoring-focused coding assistant. Prioritize clean, maintainable code.",
        "review_focus": "code smells, duplication, complexity, SOLID principles",
        "risk_tolerance": "high",
    },
}


def get_persona(name: str) -> dict:
    return PERSONAS.get(name, PERSONAS["default"])


def get_persona_system_prompt(persona: str) -> str:
    return get_persona(persona)["system_prefix"]


def get_persona_review_focus(persona: str) -> str:
    return get_persona(persona)["review_focus"]


def get_persona_risk_tolerance(persona: str) -> str:
    return get_persona(persona)["risk_tolerance"]


def list_personas() -> list[tuple[str, str]]:
    return [(name, info["system_prefix"][:60] + "...") for name, info in PERSONAS.items()]
