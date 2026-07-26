from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ACTION_TYPES = ("none", "shortcut", "system", "text", "open_url", "launch")


@dataclass(slots=True)
class Action:
    type: str = "none"
    value: str = ""
    label: str = "Unassigned"
    long_type: str = "none"
    long_value: str = ""
    long_label: str = "No long-press action"
    long_press_ms: int = 650

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        short_data = data
        legacy_short = data.get("sequence", [])
        if isinstance(legacy_short, list) and legacy_short and isinstance(legacy_short[0], dict):
            short_data = legacy_short[0]

        long_data: dict[str, Any] = {}
        legacy_long = data.get("long_sequence", [])
        if isinstance(legacy_long, list) and legacy_long and isinstance(legacy_long[0], dict):
            long_data = legacy_long[0]

        action_type = str(short_data.get("type", "none"))
        if action_type not in ACTION_TYPES:
            action_type = "none"
        long_type = str(long_data.get("type", data.get("long_type", "none")))
        if long_type not in ACTION_TYPES:
            long_type = "none"
        try:
            long_press_ms = int(data.get("long_press_ms", 650))
        except (TypeError, ValueError):
            long_press_ms = 650
        return cls(
            type=action_type,
            value=str(short_data.get("value", "")),
            label=str(short_data.get("label", "Unassigned")),
            long_type=long_type,
            long_value=str(long_data.get("value", data.get("long_value", ""))),
            long_label=str(long_data.get("label", data.get("long_label", "No long-press action"))),
            long_press_ms=max(200, min(5000, long_press_ms)),
        )

    def long_action(self) -> Action:
        return Action(type=self.long_type, value=self.long_value, label=self.long_label)


def default_key_actions() -> dict[str, Action]:
    return {str(index): Action(label=f"Key {index}") for index in range(1, 10)}


@dataclass(slots=True)
class Profile:
    name: str = "Default"
    keys: dict[str, Action] = field(default_factory=default_key_actions)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def reset_keys(self) -> None:
        self.keys = default_key_actions()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        profile = cls(name=str(data.get("name", "Default")))
        raw_keys = data.get("keys", {})
        if isinstance(raw_keys, dict):
            for key_id, value in raw_keys.items():
                if key_id in profile.keys and isinstance(value, dict):
                    profile.keys[key_id] = Action.from_dict(value)

        return profile
