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
    icon_data: str = ""
    icon_source: str = ""

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
        icon_data = str(data.get("icon_data", ""))
        icon_source = str(data.get("icon_source", ""))
        if icon_source not in {"auto", "custom"}:
            icon_source = "auto" if action_type == "open_url" and icon_data else ""
        return cls(
            type=action_type,
            value=str(short_data.get("value", "")),
            label=str(short_data.get("label", "Unassigned")),
            long_type=long_type,
            long_value=str(long_data.get("value", data.get("long_value", ""))),
            long_label=str(long_data.get("label", data.get("long_label", "No long-press action"))),
            long_press_ms=max(200, min(5000, long_press_ms)),
            icon_data=icon_data,
            icon_source=icon_source,
        )

    def long_action(self) -> Action:
        return Action(type=self.long_type, value=self.long_value, label=self.long_label)


def default_key_actions() -> dict[str, Action]:
    return {str(index): Action(label=f"Key {index}") for index in range(1, 10)}


def control_identifiers(key_count: int, potentiometer_count: int = 0) -> tuple[str, ...]:
    keys = tuple(str(index) for index in range(1, max(0, key_count) + 1))
    potentiometers = tuple(
        f"P{index}" for index in range(1, max(0, potentiometer_count) + 1)
    )
    return keys + potentiometers


def default_control_action(identifier: str) -> Action:
    label = (
        f"Potentiometer {identifier[1:]} click"
        if identifier.startswith("P")
        else f"Key {identifier}"
    )
    return Action(label=label)


@dataclass(slots=True)
class Profile:
    name: str = "Default"
    keys: dict[str, Action] = field(default_factory=default_key_actions)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def reset_keys(self) -> None:
        self.keys = default_key_actions()

    def ensure_controls(self, key_count: int, potentiometer_count: int = 0) -> None:
        for identifier in control_identifiers(key_count, potentiometer_count):
            self.keys.setdefault(identifier, default_control_action(identifier))

    def reset_controls(self, identifiers: tuple[str, ...]) -> None:
        for identifier in identifiers:
            self.keys[identifier] = default_control_action(identifier)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        profile = cls(name=str(data.get("name", "Default")))
        raw_keys = data.get("keys", {})
        if isinstance(raw_keys, dict):
            for key_id, value in raw_keys.items():
                identifier = str(key_id)
                valid_key = identifier.isdigit() and 1 <= int(identifier) <= 64
                valid_pot = (
                    identifier.startswith("P")
                    and identifier[1:].isdigit()
                    and 1 <= int(identifier[1:]) <= 16
                )
                if (valid_key or valid_pot) and isinstance(value, dict):
                    profile.keys[identifier] = Action.from_dict(value)

        return profile
