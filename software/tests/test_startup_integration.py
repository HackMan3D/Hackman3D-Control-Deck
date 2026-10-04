from hackman_control_deck import startup_integration


def test_linux_startup_round_trip(tmp_path, monkeypatch) -> None:
    startup_path = tmp_path / "autostart" / "hackman3d-control-deck.desktop"
    monkeypatch.setattr(startup_integration.sys, "platform", "linux")
    monkeypatch.setattr(startup_integration, "linux_autostart_path", lambda: startup_path)
    monkeypatch.setattr(startup_integration.sys, "executable", "/opt/hcd/HackMan3D Control Deck")
    monkeypatch.setattr(startup_integration.sys, "frozen", True, raising=False)

    startup_integration.set_start_at_login(True)

    contents = startup_path.read_text(encoding="utf-8")
    assert "HackMan3D Control Deck" in contents
    assert "--background" in contents
    assert startup_integration.is_start_at_login_enabled()

    startup_integration.set_start_at_login(False)
    assert not startup_path.exists()


def test_selecting_a_key_does_not_redraw_every_assigned_icon(monkeypatch) -> None:
    from hackman_control_deck.main_window import MainWindow

    class Button:
        def setProperty(self, *_args) -> None:
            pass

        def style(self):
            return self

        def unpolish(self, *_args) -> None:
            pass

        def polish(self, *_args) -> None:
            pass

    window = type("Window", (), {})()
    window._selection = None
    window._control_buttons = {str(index): Button() for index in range(1, 29)}
    window._show_action = lambda identifier: None
    window._refresh_control_labels = lambda: (_ for _ in ()).throw(
        AssertionError("selecting one key redrew every icon")
    )

    MainWindow._select(window, "1")

    assert window._selection == "1"
