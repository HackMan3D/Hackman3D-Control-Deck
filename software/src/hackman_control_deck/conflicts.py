from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import Profile


@dataclass(frozen=True, slots=True)
class ActionConflict:
    action_type: str
    value: str
    assignments: tuple[tuple[str, str], ...]


def find_action_conflicts(profile: Profile) -> list[ActionConflict]:
    assignments: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for key_id, action in profile.keys.items():
        if action.type != "none" and action.value.strip():
            assignments[(action.type, action.value.strip().casefold())].append((key_id, "short"))
        if action.long_type != "none" and action.long_value.strip():
            assignments[(action.long_type, action.long_value.strip().casefold())].append(
                (key_id, "long")
            )

    conflicts = []
    for (action_type, normalized_value), locations in assignments.items():
        if len(locations) < 2:
            continue
        first_key, first_press = locations[0]
        source = profile.keys[first_key]
        original_value = source.value if first_press == "short" else source.long_value
        conflicts.append(
            ActionConflict(action_type, original_value or normalized_value, tuple(locations))
        )
    return sorted(conflicts, key=lambda conflict: conflict.assignments)
