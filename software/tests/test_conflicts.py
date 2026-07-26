from hackman_control_deck.conflicts import find_action_conflicts
from hackman_control_deck.models import Action, Profile


def test_duplicate_shortcuts_are_reported_with_their_press_types() -> None:
    profile = Profile(name="Editing")
    profile.keys["1"] = Action("shortcut", "CMD+C", "Copy")
    profile.keys["2"] = Action(
        "shortcut",
        "CMD+V",
        "Paste",
        long_type="shortcut",
        long_value="cmd+c",
        long_label="Copy",
    )

    conflicts = find_action_conflicts(profile)

    assert len(conflicts) == 1
    assert conflicts[0].value == "CMD+C"
    assert conflicts[0].assignments == (("1", "short"), ("2", "long"))


def test_unassigned_keys_are_not_conflicts() -> None:
    assert find_action_conflicts(Profile()) == []
