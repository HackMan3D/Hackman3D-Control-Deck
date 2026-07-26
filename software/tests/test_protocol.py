from hackman_control_deck.protocol import DeviceEvent, DeviceInfo, EventKind, parse_line


def test_parse_key_event() -> None:
    assert parse_line("HCD_KEY|4|DOWN") == DeviceEvent(EventKind.KEY, 4, "DOWN")


def test_parse_info() -> None:
    assert parse_line("HCD_INFO|HackMan3D Control Deck|1.1.0|9") == DeviceInfo(
        "HackMan3D Control Deck", "1.1.0", 9
    )


def test_parse_info_with_model_identifier() -> None:
    assert parse_line("HCD_INFO|HackMan3D Control Deck|HCD-BASE|1.4.0|9") == DeviceInfo(
        "HackMan3D Control Deck", "1.4.0", 9, "HCD-BASE"
    )


def test_invalid_message_is_ignored() -> None:
    assert parse_line("HCD_KEY|wrong|DOWN") is None
    assert parse_line("") is None
