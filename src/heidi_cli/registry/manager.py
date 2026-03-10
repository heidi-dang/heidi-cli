from __future__ import annotations

import json
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..shared.config import ConfigLoader

logger = logging.getLogger("heidi.registry")

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
            logger.info(f"Copying model from {path} to {target_path}")
            
            # Real model copying with validation
            if path.is_dir():
                # Copy entire model directory
                shutil.copytree(path, target_path, dirs_exist_ok=True)
            else:
                # Copy single model file
                shutil.copy2(path, target_path / "model.bin")
            
            # Create metadata file with checksum
            metadata = {
                "version_id": version_id,
                "source_path": str(path),
                "checksum": await self._calculate_checksum(target_path),
                "size_bytes": await self._get_directory_size(target_path),
                "registered_at": datetime.now().isoformat()
            }
            
            with open(target_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
        
        data["versions"][version_id] = {
            "path": str(target_path),
            "channel": channel,
            "registered_at": datetime.now().isoformat(),
            "checksum": await self._calculate_checksum(target_path),
            "size_bytes": await self._get_directory_size(target_path)
        }
        
        self.save_registry(data)
        return version_id
    
    async def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA-256 checksum for model directory."""
        hash_sha256 = hashlib.sha256()
        
        if path.is_file():
            with open(path, "rb") as f:
                hash_sha256.update(f.read())
        else:
            for file_path in sorted(path.rglob("*")):
                if file_path.is_file():
                    with open(file_path, "rb") as f:
                        hash_sha256.update(f.read())
        
        return hash_sha256.hexdigest()
    
    async def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        if path.is_file():
            return path.stat().st_size
        
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

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
    
    async def rollback(self) -> bool:
        """Rollback to the previous stable model."""
        data = self.load_registry()
        current_stable = data.get("active_stable")
        
        if not current_stable:
            logger.warning("No current stable model to rollback from")
            return False
        
        # Find previous stable model
        stable_versions = [
            vid for vid, info in data["versions"].items() 
            if info["channel"] == "stable" and vid != current_stable
        ]
        
        if not stable_versions:
            logger.warning("No previous stable model found for rollback")
            return False
        
        # Sort by registration time and get the most recent previous one
        stable_versions.sort(
            key=lambda vid: data["versions"][vid]["registered_at"],
            reverse=True
        )
        
        previous_stable = stable_versions[0]
        logger.info(f"Rolling back from {current_stable} to {previous_stable}")
        
        # Update active stable
        data["active_stable"] = previous_stable
        
        # Move current stable to candidate channel
        current_info = data["versions"][current_stable]
        current_info["channel"] = "candidate"
        
        # Update path to candidate directory
        candidate_root = self.config.state_dirs["models_candidate"]
        candidate_path = candidate_root / current_stable
        stable_path = Path(current_info["path"])
        
        if stable_path.exists():
            candidate_path.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stable_path), str(candidate_path))
            current_info["path"] = str(candidate_path)
        
        self.save_registry(data)
        logger.info(f"✓ Rollback complete. {previous_stable} is now stable")
        return True
    
    async def list_versions(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """List model versions, optionally filtered by channel."""
        data = self.load_registry()
        versions = []
        
        for version_id, info in data["versions"].items():
            if channel is None or info["channel"] == channel:
                versions.append({
                    "id": version_id,
                    "channel": info["channel"],
                    "path": info["path"],
                    "registered_at": info["registered_at"],
                    "checksum": info.get("checksum"),
                    "size_bytes": info.get("size_bytes"),
                    "is_active": (
                        version_id == data.get("active_stable") or
                        version_id == data.get("active_candidate")
                    )
                })
        
        return sorted(versions, key=lambda v: v["registered_at"], reverse=True)
    
    async def get_version_info(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific version."""
        data = self.load_registry()
        if version_id not in data["versions"]:
            return None
        
        info = data["versions"][version_id]
        model_path = Path(info["path"])
        
        # Load additional metadata if available
        metadata_file = model_path / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
        
        return {
            "id": version_id,
            "channel": info["channel"],
            "path": str(model_path),
            "registered_at": info["registered_at"],
            "checksum": info.get("checksum"),
            "size_bytes": info.get("size_bytes"),
            "metadata": metadata,
            "is_active": (
                version_id == data.get("active_stable") or
                version_id == data.get("active_candidate")
            )
        }

model_registry = ModelRegistry()
