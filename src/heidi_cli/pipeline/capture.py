from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..shared.config import ConfigLoader

class CaptureEngine:
    """Captures raw run data for offline curation."""

    def __init__(self):
        self.config = ConfigLoader.load()
        self.raw_root = self.config.state_dirs["datasets_raw"]

    def create_run_folder(self, run_id: Optional[str] = None) -> Path:
        """Create a dated folder for a new run."""
        if not run_id:
            run_id = str(uuid.uuid4())
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        run_folder = self.raw_root / date_str / run_id
        run_folder.mkdir(parents=True, exist_ok=True)
        return run_folder

    async def capture_run(self, task: str, messages: List[Dict[str, str]], response: Dict[str, Any], meta: Optional[Dict[str, Any]] = None):
        """Save raw run data and metadata."""
        run_id = str(uuid.uuid4())
        run_folder = self.create_run_folder(run_id)
        
        data = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "messages": messages,
            "response": response,
            "metadata": meta or {}
        }
        
        with open(run_folder / "run.json", "w") as f:
            json.dump(data, f, indent=2)
            
        return run_id

capture_engine = CaptureEngine()
