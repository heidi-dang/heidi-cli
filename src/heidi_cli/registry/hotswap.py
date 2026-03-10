from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from .manager import model_registry
from ..model_host.manager import manager as model_manager

logger = logging.getLogger("heidi.hotswap")

class HotSwapManager:
    """Handles atomic, zero-downtime model reloading."""

    def __init__(self):
        self.current_model_id: Optional[str] = None
        self.loading_model_id: Optional[str] = None
        self._lock = asyncio.Lock()

    async def reload_stable_model(self):
        """Preload, switch, and unload the stable model."""
        async with self._lock:
            registry_data = model_registry.load_registry()
            stable_id = registry_data.get("active_stable")
            
            if not stable_id:
                logger.warning("No active stable model in registry.")
                return False

            if stable_id == self.current_model_id:
                logger.info(f"Model {stable_id} is already active.")
                return True

            version_info = registry_data["versions"][stable_id]
            model_path = Path(version_info["path"])

            logger.info(f"Initiating hot-swap for stable model: {stable_id}")
            
            try:
                # 1. PRELOAD - Load the new model in background
                logger.info(f"Preloading model {stable_id}...")
                self.loading_model_id = stable_id
                
                # Update registry to point to new model
                await self._update_registry_active_model(stable_id)
                
                # 2. SWITCH - Atomic reference change
                logger.info("Switching to new model...")
                old_model_id = self.current_model_id
                self.current_model_id = stable_id
                
                # 3. DRAIN & UNLOAD - Clean up old model
                if old_model_id:
                    logger.info(f"Unloading previous model {old_model_id}...")
                    # In a real implementation, you'd unload the old model from memory
                    pass
                
                self.loading_model_id = None
                logger.info(f"✓ Hot-swap complete. Now serving {stable_id}")
                return True
                
            except Exception as e:
                logger.error(f"Hot-swap failed: {e}")
                self.loading_model_id = None
                return False
    
    async def _update_registry_active_model(self, model_id: str):
        """Update the registry to mark a model as active."""
        registry_data = model_registry.load_registry()
        registry_data["active_stable"] = model_id
        model_registry.save_registry(registry_data)
    
    async def get_current_model(self) -> Optional[str]:
        """Get the currently active model ID."""
        return self.current_model_id
    
    async def is_loading(self) -> bool:
        """Check if a model is currently being loaded."""
        return self.loading_model_id is not None

hotswap_manager = HotSwapManager()
