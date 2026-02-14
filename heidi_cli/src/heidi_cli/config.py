from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any, Optional

import keyring
from pydantic import BaseModel


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """Find the project root by walking up for .git folder, else fallback to cwd."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    return Path.cwd()


def heidi_config_dir() -> Path:
    """Get the global config directory for Heidi CLI.

    Priority:
    1. HEIDI_HOME env var (power users / CI override)
    2. OS default:
       - Linux: ${XDG_CONFIG_HOME:-$HOME/.config}/heidi
       - macOS: ~/Library/Application Support/Heidi
       - Windows: %APPDATA%/Heidi (Roaming)
    """
    override = os.environ.get("HEIDI_HOME")
    if override:
        return Path(override).expanduser().resolve()

    system = platform.system().lower()

    if system == "windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Heidi"

    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / "Heidi"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    return base / "heidi"


def heidi_state_dir() -> Optional[Path]:
    """Get the optional state directory for Heidi CLI.

    - Linux: ${XDG_STATE_HOME:-$HOME/.local/state}/heidi
    - macOS: ~/Library/Application Support/Heidi (uses same as config)
    - Windows: %LOCALAPPDATA%/Heidi
    """
    system = platform.system().lower()

    if system == "windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Heidi"

    if system == "darwin":
        return None

    xdg_state = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg_state) if xdg_state else (Path.home() / ".local" / "state")
    return base / "heidi"


def heidi_cache_dir() -> Optional[Path]:
    """Get the optional cache directory for Heidi CLI.

    - Linux: ${XDG_CACHE_HOME:-$HOME/.cache}/heidi
    - macOS: ~/Library/Caches/Heidi
    - Windows: %LOCALAPPDATA%/Heidi/Cache
    """
    system = platform.system().lower()

    if system == "windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Heidi" / "Cache"

    if system == "darwin":
        return Path.home() / "Library" / "Caches" / "Heidi"

    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else (Path.home() / ".cache")
    return base / "heidi"


def heidi_ui_dir() -> Path:
    """Get the UI directory for Heidi CLI.

    Priority:
    1. $HEIDI_HOME/ui (if HEIDI_HOME set)
    2. <cache_dir>/ui (e.g., ~/.cache/heidi/ui on Linux)
    """
    heidi_home = os.environ.get("HEIDI_HOME")
    if heidi_home:
        return Path(heidi_home) / "ui"

    cache = heidi_cache_dir()
    if cache:
        return cache / "ui"

    # Fallback to config dir
    return heidi_config_dir() / "ui"


def check_legacy_heidi_dir() -> Optional[Path]:
    """Check for legacy ./.heidi/ in current project directory."""
    legacy_path = Path.cwd() / ".heidi"
    if legacy_path.exists() and legacy_path.is_dir():
        return legacy_path
    return None


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
    TASKS_DIR_NAME = "tasks"

    @classmethod
    def config_dir(cls) -> Path:
        """Get the global config directory (for secrets/config)."""
        return heidi_config_dir()

    @classmethod
    def project_root(cls) -> Path:
        """Get the project root (where tasks are stored)."""
        return find_project_root()

    @classmethod
    def tasks_dir(cls) -> Path:
        """Get the tasks directory (always in project root)."""
        return cls.project_root() / cls.TASKS_DIR_NAME

    @classmethod
    def heidi_dir(cls) -> Path:
        """Get the global config directory (legacy alias for compatibility)."""
        return cls.config_dir()

    @classmethod
    def config_file(cls) -> Path:
        return cls.config_dir() / "config.json"

    @classmethod
    def secrets_file(cls) -> Path:
        return cls.config_dir() / "secrets.json"

    @classmethod
    def runs_dir(cls) -> Path:
        return cls.config_dir() / "runs"

    @classmethod
    def backups_dir(cls) -> Path:
        return cls.config_dir() / "backups"

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.config_dir().mkdir(parents=True, exist_ok=True)
        cls.runs_dir().mkdir(parents=True, exist_ok=True)
        cls.backups_dir().mkdir(parents=True, exist_ok=True)
        cls.tasks_dir().mkdir(parents=True, exist_ok=True)
        os.chmod(cls.secrets_file(), 0o600) if cls.secrets_file().exists() else None

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
