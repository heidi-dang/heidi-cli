from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import keyring
from pydantic import BaseModel


class HeidiConfig(BaseModel):
    version: str = "0.1.0"
    executor_default: str = "copilot"
    log_level: str = "info"
    workdir: Optional[Path] = None
    default_executor: str = "copilot"
    max_retries: int = 3
    copilot_model: str = "gpt-5"
    server_url: str = "http://localhost:7777"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HeidiConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.model_fields})


class HeidiSecrets(BaseModel):
    github_token: Optional[str] = None
    copilot_model: str = "gpt-5"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HeidiSecrets:
        return cls(**{k: v for k, v in data.items() if k in cls.model_fields})


class ConfigManager:
    HEIDI_DIR = Path.home() / ".heidi"
    CONFIG_FILE = HEIDI_DIR / "config.json"
    SECRETS_FILE = HEIDI_DIR / "secrets.json"
    RUNS_DIR = HEIDI_DIR / "runs"
    TASKS_DIR = HEIDI_DIR / "tasks"

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.HEIDI_DIR.mkdir(parents=True, exist_ok=True)
        cls.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        cls.TASKS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_config(cls) -> HeidiConfig:
        if not cls.CONFIG_FILE.exists():
            return HeidiConfig()
        data = json.loads(cls.CONFIG_FILE.read_text())
        return HeidiConfig.from_dict(data)

    @classmethod
    def save_config(cls, config: HeidiConfig) -> None:
        cls.ensure_dirs()
        cls.CONFIG_FILE.write_text(json.dumps(config.to_dict(), indent=2))

    @classmethod
    def load_secrets(cls) -> HeidiSecrets:
        if not cls.SECRETS_FILE.exists():
            return HeidiSecrets()
        data = json.loads(cls.SECRETS_FILE.read_text())
        return HeidiSecrets.from_dict(data)

    @classmethod
    def save_secrets(cls, secrets: HeidiSecrets) -> None:
        cls.ensure_dirs()
        cls.SECRETS_FILE.write_text(json.dumps(secrets.to_dict(), indent=2))
        os.chmod(cls.SECRETS_FILE, 0o600)

    @classmethod
    def get_github_token(cls) -> Optional[str]:
        secrets = cls.load_secrets()
        if secrets.github_token:
            return secrets.github_token
        token = keyring.get_password("heidi", "github_token")
        return token

    @classmethod
    def set_github_token(cls, token: str, store_keyring: bool = True) -> None:
        secrets = cls.load_secrets()
        secrets.github_token = token
        cls.save_secrets(secrets)
        if store_keyring:
            keyring.set_password("heidi", "github_token", token)

    @classmethod
    def get_valve(cls, key: str) -> Any:
        config = cls.load_config()
        return getattr(config, key, None)

    @classmethod
    def set_valve(cls, key: str, value: Any) -> None:
        config = cls.load_config()
        if hasattr(config, key):
            setattr(config, key, value)
            cls.save_config(config)
