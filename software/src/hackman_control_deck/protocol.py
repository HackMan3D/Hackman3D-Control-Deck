from dataclasses import dataclass
from enum import Enum


class EventKind(str, Enum):
    KEY = "key"
    POTENTIOMETER = "potentiometer"
    POTENTIOMETER_BUTTON = "potentiometer_button"
    ENCODER = "encoder"
    SLIDER = "slider"


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
    potentiometer_count: int = 0
    icon_signatures: tuple[int, ...] = ()


def parse_line(line: str) -> str | DeviceEvent | DeviceInfo | None:
    parts = [part.strip() for part in line.strip().split("|")]
    if not parts or not parts[0]:
        return None

    command = parts[0]
    if command in {"HCD_PONG", "HCD_READY"}:
        return command

    if command == "HCD_INFO" and len(parts) in {4, 5, 6, 7}:
        try:
            if len(parts) == 7:
                signatures = tuple(
                    int(value, 16) if value else 0
                    for value in parts[6].split(",")
                )
                return DeviceInfo(
                    parts[1],
                    parts[3],
                    int(parts[4]),
                    parts[2],
                    int(parts[5]),
                    signatures,
                )
            if len(parts) == 6:
                return DeviceInfo(
                    parts[1],
                    parts[3],
                    int(parts[4]),
                    parts[2],
                    int(parts[5]),
                )
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

    if command == "HCD_POT_BUTTON" and len(parts) == 3:
        try:
            return DeviceEvent(
                EventKind.POTENTIOMETER_BUTTON,
                int(parts[1]),
                parts[2].upper(),
            )
        except ValueError:
            return None

    if command == "HCD_POT" and len(parts) == 3:
        try:
            value = max(0, min(1023, int(parts[2])))
            return DeviceEvent(EventKind.POTENTIOMETER, int(parts[1]), str(value))
        except ValueError:
            return None

    if command == "HCD_ENCODER" and len(parts) == 3:
        try:
            direction = parts[2].upper()
            if direction not in {"LEFT", "RIGHT"}:
                return None
            return DeviceEvent(EventKind.ENCODER, int(parts[1]), direction)
        except ValueError:
            return None

    if command == "HCD_SLIDER" and len(parts) == 3:
        try:
            value = max(0, min(1023, int(parts[2])))
            return DeviceEvent(EventKind.SLIDER, int(parts[1]), str(value))
        except ValueError:
            return None

    return None
