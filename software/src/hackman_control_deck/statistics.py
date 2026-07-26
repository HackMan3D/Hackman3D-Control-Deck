from __future__ import annotations

import json
from pathlib import Path

from .constants import profile_directory


class StatisticsStore:
    FORMAT_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or profile_directory().parent / "statistics.json"

    def record(self, profile_name: str, key_id: str, press_kind: str) -> None:
        data = self._load()
        profiles = data.setdefault("profiles", {})
        profile = profiles.setdefault(profile_name, {})
        key = profile.setdefault(key_id, {"short": 0, "long": 0})
        kind = "long" if press_kind == "long" else "short"
        key[kind] = int(key.get(kind, 0)) + 1
        self._save(data)

    def counts(self, profile_name: str) -> dict[str, dict[str, int]]:
        profile = self._load().get("profiles", {}).get(profile_name, {})
        return {
            str(key_id): {
                "short": int(values.get("short", 0)),
                "long": int(values.get("long", 0)),
            }
            for key_id, values in profile.items()
            if isinstance(values, dict)
        }

    def reset(self, profile_name: str) -> None:
        data = self._load()
        profiles = data.setdefault("profiles", {})
        profiles.pop(profile_name, None)
        self._save(data)

    def _load(self) -> dict:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": self.FORMAT_VERSION, "profiles": {}}
        if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
            return {"version": self.FORMAT_VERSION, "profiles": {}}
        return data

    def _save(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        temporary.replace(self._path)
