from hackman_control_deck.action_runner import ActionRunner
from hackman_control_deck.main_window import MainWindow
from hackman_control_deck.models import Action, Profile
from pynput.keyboard import Key
from pathlib import Path
from types import SimpleNamespace

_ = Key


class KeyboardRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def press(self, key: object) -> None:
        self.events.append(("press", key))

    def release(self, key: object) -> None:
        self.events.append(("release", key))


def test_system_action_is_loaded_from_profile_data() -> None:
    action = Action.from_dict({"type": "system", "value": "volume_up", "label": "Increase volume"})

    assert action.type == "system"
    assert action.value == "volume_up"


def test_media_system_command_presses_and_releases_key(monkeypatch) -> None:
    recorder = KeyboardRecorder()
    runner = ActionRunner()
    monkeypatch.setattr("hackman_control_deck.action_runner.sys.platform", "win32")
    monkeypatch.setattr(runner, "_keyboard_controller", lambda: recorder)

    runner._system("volume_up")

    assert [event for event, _ in recorder.events] == ["press", "release"]
    assert recorder.events[0][1] == recorder.events[1][1]


def test_macos_volume_uses_audio_command_without_accessibility(monkeypatch) -> None:
    commands: list[str] = []
    runner = ActionRunner()
    monkeypatch.setattr("hackman_control_deck.action_runner.sys.platform", "darwin")
    monkeypatch.setattr(runner, "_macos_audio", commands.append)

    runner._system("volume_up")
    runner._system("volume_down")
    runner._system("volume_mute")

    assert commands == ["volume_up", "volume_down", "volume_mute"]


def test_macos_media_controls_still_use_system_events(monkeypatch) -> None:
    key_types: list[int] = []
    runner = ActionRunner()
    monkeypatch.setattr("hackman_control_deck.action_runner.sys.platform", "darwin")
    monkeypatch.setattr(runner, "_macos_system_key", key_types.append)

    runner._system("media_play_pause")

    assert key_types == [16]


def test_macos_power_commands_use_native_handler(monkeypatch) -> None:
    commands: list[str] = []
    runner = ActionRunner()
    monkeypatch.setattr("hackman_control_deck.action_runner.sys.platform", "darwin")
    monkeypatch.setattr(runner, "_macos_power", commands.append)

    for command in ("lock", "sleep", "restart", "shutdown"):
        runner._system(command)

    assert commands == ["lock", "sleep", "restart", "shutdown"]


def test_macos_lock_does_not_simulate_keyboard_input(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(
        "hackman_control_deck.action_runner.subprocess.run",
        lambda arguments, **kwargs: calls.append(arguments) or Result(),
    )

    ActionRunner._macos_power("lock")

    assert calls == [["/usr/bin/pmset", "displaysleepnow"]]


def test_system_presets_include_power_and_microphone_commands() -> None:
    commands = {command for _, command in MainWindow._system_command_presets()}

    assert {"microphone_mute", "lock", "sleep", "restart", "shutdown"} <= commands


def test_system_presets_hide_commands_unsupported_by_platform(monkeypatch) -> None:
    monkeypatch.setattr("hackman_control_deck.main_window.sys.platform", "freebsd")

    assert MainWindow._system_command_presets() == ()


def test_linux_system_presets_include_desktop_commands(monkeypatch) -> None:
    monkeypatch.setattr("hackman_control_deck.main_window.sys.platform", "linux")

    commands = {command for _, command in MainWindow._system_command_presets()}

    assert {"volume_up", "microphone_mute", "lock", "shutdown"} <= commands


def test_unknown_system_command_is_rejected() -> None:
    runner = ActionRunner()

    try:
        runner._system("not_a_command")
    except ValueError as error:
        assert "not_a_command" in str(error)
    else:
        raise AssertionError("Unknown commands must not be ignored")


class PresetTranslator:
    @staticmethod
    def _text(key: str) -> str:
        return key


def test_shortcut_presets_are_platform_specific(monkeypatch) -> None:
    translator = PresetTranslator()
    monkeypatch.setattr("hackman_control_deck.main_window.sys.platform", "darwin")
    mac_shortcuts = dict(MainWindow._shortcut_presets(translator))
    monkeypatch.setattr("hackman_control_deck.main_window.sys.platform", "win32")
    windows_shortcuts = dict(MainWindow._shortcut_presets(translator))

    assert mac_shortcuts["command_copy"] == "CMD+C"
    assert windows_shortcuts["command_copy"] == "CTRL+C"
    assert mac_shortcuts["command_screenshot"] == "CMD+SHIFT+4"
    assert windows_shortcuts["command_screenshot"] == "WIN+SHIFT+S"


def test_windows_start_menu_apps_are_discovered(tmp_path: Path) -> None:
    programs = tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    utilities = programs / "Utilities"
    utilities.mkdir(parents=True)
    (programs / "Example App.lnk").touch()
    (utilities / "Web Tool.url").touch()
    (programs / "Uninstall Example.lnk").touch()

    applications = MainWindow._windows_start_menu_applications([programs])

    assert set(applications) == {"example app", "web tool"}


def test_linux_desktop_apps_are_discovered(tmp_path: Path) -> None:
    visible = tmp_path / "example.desktop"
    visible.write_text("[Desktop Entry]\nName=Example App\nExec=example\n")
    hidden = tmp_path / "hidden.desktop"
    hidden.write_text("[Desktop Entry]\nName=Hidden App\nNoDisplay=true\n")

    applications = MainWindow._linux_desktop_applications((tmp_path,))

    assert applications == {"example app": str(visible)}


def test_linux_volume_uses_wpctl(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "hackman_control_deck.action_runner.shutil.which",
        lambda name: "/usr/bin/wpctl" if name == "wpctl" else None,
    )
    monkeypatch.setattr(
        "hackman_control_deck.action_runner.subprocess.run",
        lambda arguments, **kwargs: calls.append(arguments)
        or SimpleNamespace(returncode=0, stdout="Volume: 0.42", stderr=""),
    )

    assert ActionRunner._linux_audio_level("sink") == 42
    ActionRunner._linux_set_audio_level("sink", 55)

    assert calls == [
        ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "55%"],
    ]


class EditorValue:
    def __init__(self, value: str) -> None:
        self.value = value

    def text(self) -> str:
        return self.value


class EditorPresets:
    def __init__(self, value: str) -> None:
        self.value = value

    def currentData(self) -> str:
        return self.value


def test_system_action_save_uses_selected_command() -> None:
    value = MainWindow._editor_value(
        "system",
        EditorValue(""),  # type: ignore[arg-type]
        EditorPresets("brightness_up"),  # type: ignore[arg-type]
    )

    assert value == "brightness_up"


def test_system_action_save_keeps_remembered_shutdown_command() -> None:
    value = MainWindow._editor_value(
        "system",
        EditorValue(""),  # type: ignore[arg-type]
        EditorPresets(""),  # type: ignore[arg-type]
        "shutdown",
    )

    assert value == "shutdown"


def test_windows_shortcut_uses_embedded_high_resolution_icon(
    monkeypatch, tmp_path: Path
) -> None:
    shortcut = tmp_path / "Example App.lnk"
    executable = tmp_path / "Example App.exe"
    shortcut.touch()
    executable.touch()
    output = (
        '{"shortcut":"'
        + str(shortcut).replace("\\", "\\\\")
        + '","source":"'
        + str(executable).replace("\\", "\\\\")
        + '"}'
    )
    monkeypatch.setattr(
        "hackman_control_deck.main_window.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=output),
    )

    sources = MainWindow._windows_shortcut_icon_sources([shortcut])

    assert sources[str(shortcut)] == str(executable)


def test_shutdown_command_is_saved_on_pro_key_28() -> None:
    profile = Profile()
    profile.ensure_controls(28)
    saved: list[Profile] = []
    status = SimpleNamespace(showMessage=lambda *args: None)
    window = SimpleNamespace(
        _selection="28",
        _editor_action=lambda: Action(
            type="system", value="shutdown", label="Shut down computer"
        ),
        _long_editor_action=lambda: Action(),
        _custom_icon_data="",
        _icon_source="",
        _long_press_delay=SimpleNamespace(value=lambda: 650),
        _profile=profile,
        _store=SimpleNamespace(save=saved.append),
        _refresh_control_labels=lambda: None,
        statusBar=lambda: status,
        _text=lambda key, **values: key,
    )

    MainWindow._save_action(window)  # type: ignore[arg-type]

    assert saved == [profile]
    assert profile.keys["28"].type == "system"
    assert profile.keys["28"].value == "shutdown"
