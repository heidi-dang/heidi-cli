from __future__ import annotations

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..shared.config import ConfigLoader

class CurationEngine:
    """Crates training datasets from raw runs with secret redaction."""

    def __init__(self):
        self.config = ConfigLoader.load()
        # Common secret patterns (API keys, tokens, etc.)
        self.redaction_patterns = [
            re.compile(r"sk-[a-zA-Z0-9]{32,}", re.I),           # OpenAI
            re.compile(r"gh[oprs]_[a-zA-Z0-9]{36,}", re.I),     # GitHub
            re.compile(r"(?:password|secret|key|token)\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{8,})['\"]?", re.I),
        ]

    def redact_text(self, text: str) -> str:
        """Apply all redaction patterns to a string."""
        redacted = text
        for pattern in self.redaction_patterns:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    def redact_json(self, data: Any) -> Any:
        """Recursively redact secrets from a JSON-like object."""
        if isinstance(data, str):
            return self.redact_text(data)
        elif isinstance(data, dict):
            result = {}
            for k, v in data.items():
                # If key looks like a secret, redact the value directly
                k_lower = str(k).lower()
                if any(sec in k_lower for sec in ["password", "secret", "key", "token"]):
                    if isinstance(v, str) and len(v) > 5:
                        result[k] = "[REDACTED]"
                    else:
                        result[k] = self.redact_json(v)
                else:
                    result[k] = self.redact_json(v)
            return result
        elif isinstance(data, list):
            return [self.redact_json(i) for i in data]
        return data

    async def curate_dataset(self, date_filter: Optional[str] = None) -> int:
        """Collect raw runs, redact secrets, and write to curated output."""
        raw_root = self.config.state_dirs["datasets_raw"]
        curated_root = self.config.state_dirs["datasets_curated"]
        
        curated_data = []
        count = 0
        
        # Iterate through dated folders
        for date_dir in raw_root.iterdir():
            if not date_dir.is_dir():
                continue
            if date_filter and date_dir.name != date_filter:
                continue
            
            for run_dir in date_dir.iterdir():
                if not run_dir.is_dir():
                    continue
                run_file = run_dir / "run.json"
                if not run_file.exists():
                    continue
                
                with open(run_file, "r") as f:
                    raw_run = json.load(f)
                    
                # Redact and add to collection
                curated_run = self.redact_json(raw_run)
                curated_data.append(curated_run)
                count += 1

        if curated_data:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = curated_root / f"dataset_{stamp}.jsonl"
            with open(output_file, "w") as f:
                for entry in curated_data:
                    f.write(json.dumps(entry) + "\n")
                    
        return count

curation_engine = CurationEngine()
