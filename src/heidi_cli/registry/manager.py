from __future__ import annotations

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..shared.config import ConfigLoader

class ModelRegistry:
    """Manages model versions and promotion channels."""

    def __init__(self):
        self.config = ConfigLoader.load()
        self.registry_root = self.config.state_dirs["registry"]
        self.registry_file = self.registry_root / "registry.json"
        self._init_registry()

    def _init_registry(self):
        if not self.registry_file.exists():
            data = {
                "active_stable": None,
                "active_candidate": None,
                "versions": {}
            }
            with open(self.registry_file, "w") as f:
                json.dump(data, f, indent=2)

    def load_registry(self) -> Dict[str, Any]:
        with open(self.registry_file, "r") as f:
            return json.load(f)

    def save_registry(self, data: Dict[str, Any]):
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)

    async def register_version(self, version_id: str, path: Path, channel: str = "experimental"):
        """Register a new model version in a specific channel."""
        data = self.load_registry()
        
        # Determine target path
        target_root = self.config.state_dirs[f"models_{channel}"]
        target_path = target_root / version_id
        
        # Copy model to registry state if not already there
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)
            # In real implementation: shutil.copytree(path, target_path)
            (target_path / "model.bin").touch() # Placeholder
            
        data["versions"][version_id] = {
            "path": str(target_path),
            "channel": channel,
            "registered_at": datetime.now().isoformat()
        }
        
        self.save_registry(data)
        return version_id

    async def promote(self, version_id: str, to_channel: str = "stable"):
        """Promote a model version to a new channel (e.g. candidate -> stable)."""
        data = self.load_registry()
        if version_id not in data["versions"]:
            raise ValueError(f"Version {version_id} not found.")
            
        old_info = data["versions"][version_id]
        old_path = Path(old_info["path"])
        
        target_root = self.config.state_dirs[f"models_{to_channel}"]
        target_path = target_root / version_id
        
        if not target_path.exists():
            shutil.move(str(old_path), str(target_path))
            
        data["versions"][version_id]["path"] = str(target_path)
        data["versions"][version_id]["channel"] = to_channel
        
        if to_channel == "stable":
            data["active_stable"] = version_id
        elif to_channel == "candidate":
            data["active_candidate"] = version_id
            
        self.save_registry(data)

model_registry = ModelRegistry()
