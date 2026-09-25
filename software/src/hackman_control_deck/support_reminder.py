from __future__ import annotations


MINIMUM_ACTIONS = 50
MINIMUM_AGE_SECONDS = 7 * 24 * 60 * 60
REMINDER_COOLDOWN_SECONDS = 90 * 24 * 60 * 60


def support_reminder_due(
    *,
    first_seen: int,
    action_count: int,
    last_shown: int,
    disabled: bool,
    now: int,
) -> bool:
    if disabled:
        return False
    experienced = action_count >= MINIMUM_ACTIONS or now - first_seen >= MINIMUM_AGE_SECONDS
    if not experienced:
        return False
    return last_shown <= 0 or now - last_shown >= REMINDER_COOLDOWN_SECONDS
