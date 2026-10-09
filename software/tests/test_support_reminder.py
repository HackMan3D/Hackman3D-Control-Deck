from hackman_control_deck.support_reminder import (
    MINIMUM_ACTIONS,
    MINIMUM_AGE_SECONDS,
    REMINDER_COOLDOWN_SECONDS,
    REMINDER_SNOOZE_SECONDS,
    support_reminder_due,
)


def test_reminder_waits_for_real_use() -> None:
    assert not support_reminder_due(
        first_seen=100,
        action_count=MINIMUM_ACTIONS - 1,
        last_shown=0,
        disabled=False,
        now=100 + MINIMUM_AGE_SECONDS - 1,
    )
    assert support_reminder_due(
        first_seen=100,
        action_count=MINIMUM_ACTIONS,
        last_shown=0,
        disabled=False,
        now=101,
    )


def test_reminder_uses_age_and_respects_cooldown_and_opt_out() -> None:
    now = 100 + MINIMUM_AGE_SECONDS + REMINDER_COOLDOWN_SECONDS
    assert support_reminder_due(
        first_seen=100,
        action_count=0,
        last_shown=0,
        disabled=False,
        now=now,
    )
    assert not support_reminder_due(
        first_seen=100,
        action_count=100,
        last_shown=now - REMINDER_COOLDOWN_SECONDS + 1,
        disabled=False,
        now=now,
    )


def test_reminder_can_be_snoozed_for_four_days() -> None:
    now = 1_000_000
    snoozed_until = now + REMINDER_SNOOZE_SECONDS
    assert not support_reminder_due(
        first_seen=1,
        action_count=MINIMUM_ACTIONS,
        last_shown=0,
        snoozed_until=snoozed_until,
        disabled=False,
        now=snoozed_until - 1,
    )
    assert support_reminder_due(
        first_seen=1,
        action_count=MINIMUM_ACTIONS,
        last_shown=0,
        snoozed_until=snoozed_until,
        disabled=False,
        now=snoozed_until,
    )
    assert not support_reminder_due(
        first_seen=100,
        action_count=100,
        last_shown=0,
        disabled=True,
        now=now,
    )
