from __future__ import annotations

import json
from pathlib import Path


class MemoryStore:
    """Small JSON-backed memory for durable facts across an agent run."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def remember(self, key: str, value: str) -> dict[str, str]:
        data = self.load()
        data[str(key)] = str(value)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return data

