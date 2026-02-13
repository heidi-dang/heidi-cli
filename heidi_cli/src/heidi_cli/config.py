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
    default_agent: str = "high-autonomy"
    provider: str = "copilot"
    telemetry_enabled: bool = False
    openwebui_url: Optional[str] = "http://localhost:3000"
    openwebui_token: Optional[str] = None
    ollama_url: str = "http://localhost:11434"
    lmstudio_url: str = "http://localhost:1234"
    persona: str = "default"

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
    TASKS_DIR = Path("./tasks")

    @classmethod
    def heidi_dir(cls) -> Path:
        return Path.cwd() / ".heidi"

    @classmethod
    def config_file(cls) -> Path:
        return cls.heidi_dir() / "config.json"

    @classmethod
    def secrets_file(cls) -> Path:
        return cls.heidi_dir() / "secrets.json"

    @classmethod
    def runs_dir(cls) -> Path:
        return cls.heidi_dir() / "runs"

    @classmethod
    def backups_dir(cls) -> Path:
        return cls.heidi_dir() / "backups"

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.heidi_dir().mkdir(parents=True, exist_ok=True)
        cls.runs_dir().mkdir(parents=True, exist_ok=True)
        cls.backups_dir().mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_config(cls) -> HeidiConfig:
        if not cls.config_file().exists():
            return HeidiConfig()
        data = json.loads(cls.config_file().read_text())
        return HeidiConfig.from_dict(data)

    @classmethod
    def save_config(cls, config: HeidiConfig) -> None:
        cls.ensure_dirs()
        cls.config_file().write_text(json.dumps(config.to_dict(), indent=2))

    @classmethod
    def load_secrets(cls) -> HeidiSecrets:
        if not cls.secrets_file().exists():
            return HeidiSecrets()
        data = json.loads(cls.secrets_file().read_text())
        return HeidiSecrets.from_dict(data)

    @classmethod
    def save_secrets(cls, secrets: HeidiSecrets) -> None:
        cls.ensure_dirs()
        cls.secrets_file().write_text(json.dumps(secrets.to_dict(), indent=2))
        os.chmod(cls.secrets_file(), 0o600)

    @classmethod
    def get_github_token(cls) -> Optional[str]:
        secrets = cls.load_secrets()
        if secrets.github_token:
            return secrets.github_token
        try:
            token = keyring.get_password("heidi", "github_token")
            return token
        except Exception:
            return None

    @classmethod
    def set_github_token(cls, token: str, store_keyring: bool = True) -> None:
        secrets = cls.load_secrets()
        secrets.github_token = token
        cls.save_secrets(secrets)
        if store_keyring:
            try:
                keyring.set_password("heidi", "github_token", token)
            except Exception:
                pass

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
