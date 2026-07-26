from dataclasses import dataclass
from enum import Enum


class EventKind(str, Enum):
    KEY = "key"


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    kind: EventKind
    control_id: int
    state: str


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    product: str
    firmware_version: str
    key_count: int
    model_identifier: str = "HCD-LEGACY"


def parse_line(line: str) -> str | DeviceEvent | DeviceInfo | None:
    parts = [part.strip() for part in line.strip().split("|")]
    if not parts or not parts[0]:
        return None

    command = parts[0]
    if command in {"HCD_PONG", "HCD_READY"}:
        return command

    if command == "HCD_INFO" and len(parts) in {4, 5}:
        try:
            if len(parts) == 5:
                return DeviceInfo(parts[1], parts[3], int(parts[4]), parts[2])
            return DeviceInfo(parts[1], parts[2], int(parts[3]))
        except ValueError:
            return None

    if command == "HCD_KEY" and len(parts) == 3:
        try:
            return DeviceEvent(EventKind.KEY, int(parts[1]), parts[2].upper())
        except ValueError:
            return None

    return None
