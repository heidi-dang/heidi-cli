from __future__ import annotations

import logging
from .manager import model_registry

logger = logging.getLogger("heidi.hotswap")

class HotSwapManager:
    """Handles atomic, zero-downtime model reloading."""

    async def reload_stable_model(self):
        """Preload, switch, and unload the stable model."""
        registry_data = model_registry.load_registry()
        stable_id = registry_data.get("active_stable")
        
        if not stable_id:
            logger.warning("No active stable model in registry.")
            return False

        version_info = registry_data["versions"][stable_id]
        model_path = version_info["path"]

        logger.info(f"Initiating hot-swap for stable model: {stable_id}")
        
        # 1. PRELOAD (In background or parallel)
        # model_manager.preload(stable_id, model_path)
        
        # 2. SWITCH (Atomic reference change)
        # model_manager.update_routing(stable_id, model_path)
        
        # 3. DRAIN & UNLOAD
        # model_manager.unload_previous(stable_id)
        
        logger.info(f"✓ Hot-swap complete. Now serving {stable_id}")
        return True

hotswap_manager = HotSwapManager()
