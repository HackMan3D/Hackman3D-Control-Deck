import plistlib

from hackman_control_deck import macos_integration


def test_login_agent_round_trip(tmp_path, monkeypatch) -> None:
    agent_path = tmp_path / "com.hackman3d.control-deck.plist"
    monkeypatch.setattr(macos_integration, "launch_agent_path", lambda: agent_path)
    monkeypatch.setattr(macos_integration.sys, "platform", "darwin")

    macos_integration.set_start_at_login(True)
    payload = plistlib.loads(agent_path.read_bytes())
    assert payload["Label"] == "com.hackman3d.control-deck"
    assert payload["RunAtLoad"] is True
    assert "--background" not in payload["ProgramArguments"]
    assert macos_integration.is_start_at_login_enabled()

    macos_integration.set_start_at_login(False)
    assert not agent_path.exists()
