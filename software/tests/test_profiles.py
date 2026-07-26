from hackman_control_deck.models import Action, Profile
from hackman_control_deck.profile_store import ProfileStore


def test_profile_round_trip(tmp_path) -> None:
    store = ProfileStore(tmp_path)
    profile = Profile(name="Fusion 360")
    profile.keys["1"] = Action("shortcut", "CTRL+S", "Save")
    store.save(profile)

    loaded = store.load("Fusion 360")
    assert loaded.name == "Fusion 360"
    assert loaded.keys["1"] == Action("shortcut", "CTRL+S", "Save")
    assert len(loaded.keys) == 9


def test_profile_rename_preserves_actions(tmp_path) -> None:
    store = ProfileStore(tmp_path)
    profile = store.create("Design")
    profile.keys["2"] = Action("launch", "/Applications/FreeCAD.app", "FreeCAD")
    store.save(profile)

    renamed = store.rename("Design", "CAD")

    assert store.list_profiles() == ["CAD"]
    assert renamed.keys["2"].value == "/Applications/FreeCAD.app"


def test_profile_delete_recreates_default_when_last_profile_is_removed(tmp_path) -> None:
    store = ProfileStore(tmp_path)
    store.create("Temporary")

    store.delete("Temporary")

    assert store.list_profiles() == ["Default"]


def test_profile_names_cannot_overwrite_an_existing_profile(tmp_path) -> None:
    store = ProfileStore(tmp_path)
    store.create("Work")

    try:
        store.create("Work")
    except FileExistsError:
        pass
    else:
        raise AssertionError("Duplicate profile should have been rejected")


def test_profile_can_reset_all_nine_keys() -> None:
    profile = Profile(name="Editing")
    profile.keys["1"] = Action("shortcut", "CMD+S", "Save")
    profile.keys["9"] = Action("system", "volume_up", "Volume")

    profile.reset_keys()

    assert len(profile.keys) == 9
    assert all(action.type == "none" for action in profile.keys.values())
    assert profile.keys["1"].label == "Key 1"
    assert profile.keys["9"].label == "Key 9"


def test_short_and_long_press_actions_round_trip(tmp_path) -> None:
    store = ProfileStore(tmp_path)
    profile = Profile(name="Automation")
    profile.keys["1"] = Action(
        type="shortcut",
        value="CMD+S",
        label="Build",
        long_type="launch",
        long_value="/Applications/Terminal.app",
        long_label="Terminal",
        long_press_ms=900,
    )
    store.save(profile)

    loaded = store.load("Automation").keys["1"]

    assert loaded.type == "shortcut"
    assert loaded.value == "CMD+S"
    assert loaded.long_type == "launch"
    assert loaded.long_value == "/Applications/Terminal.app"
    assert loaded.long_press_ms == 900


def test_legacy_sequences_keep_their_first_action() -> None:
    action = Action.from_dict(
        {
            "sequence": [
                {"type": "shortcut", "value": "CMD+S", "label": "Save"},
                {"type": "text", "value": "Done", "label": "Confirmation"},
            ],
            "long_sequence": [
                {
                    "type": "launch",
                    "value": "/Applications/Terminal.app",
                    "label": "Terminal",
                }
            ],
            "long_press_ms": 900,
        }
    )

    assert (action.type, action.value, action.label) == ("shortcut", "CMD+S", "Save")
    assert (action.long_type, action.long_value, action.long_label) == (
        "launch",
        "/Applications/Terminal.app",
        "Terminal",
    )


def test_profile_export_import_duplicate_and_backup(tmp_path) -> None:
    source_store = ProfileStore(tmp_path / "source")
    profile = source_store.create("CAD")
    profile.keys["2"] = Action("launch", "/Applications/FreeCAD.app", "FreeCAD")
    source_store.save(profile)
    exported = tmp_path / "CAD.hcdprofile"
    backup = tmp_path / "profiles.hcdbackup"
    source_store.export_profile("CAD", exported)
    source_store.export_backup(backup)

    duplicate = source_store.duplicate("CAD")
    target_store = ProfileStore(tmp_path / "target")
    imported = target_store.import_profile(exported)
    restored = target_store.import_backup(backup)

    assert duplicate.name == "CAD Copy"
    assert imported.keys["2"].label == "FreeCAD"
    assert restored[0].name == "CAD 2"
