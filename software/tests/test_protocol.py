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


def test_parse_hcd_plus_info_and_potentiometer_events() -> None:
    assert parse_line(
        "HCD_INFO|HackMan3D Control Deck Plus|HCD-PLUS|1.0.0|12|2"
    ) == DeviceInfo(
        "HackMan3D Control Deck Plus",
        "1.0.0",
        12,
        "HCD-PLUS",
        2,
    )
    assert parse_line("HCD_POT|2|768") == DeviceEvent(
        EventKind.POTENTIOMETER,
        2,
        "768",
    )
    assert parse_line("HCD_POT_BUTTON|1|DOWN") == DeviceEvent(
        EventKind.POTENTIOMETER_BUTTON,
        1,
        "DOWN",
    )


def test_parse_hcd_pro_info() -> None:
    assert parse_line(
        "HCD_INFO|HackMan3D Control Deck Pro|HCD-PRO|1.0.0|12|0"
    ) == DeviceInfo(
        "HackMan3D Control Deck Pro",
        "1.0.0",
        12,
        "HCD-PRO",
        0,
    )


def test_parse_hcd_pro_info_with_flash_icon_cache() -> None:
    assert parse_line(
        "HCD_INFO|HackMan3D Control Deck Pro|HCD-PRO|1.2.33|3|0|"
        "00000000,1a2b3c4d,ffffffff"
    ) == DeviceInfo(
        "HackMan3D Control Deck Pro",
        "1.2.33",
        3,
        "HCD-PRO",
        0,
        (0, 0x1A2B3C4D, 0xFFFFFFFF),
    )


def test_parse_hcd_pro_slider_event() -> None:
    assert parse_line("HCD_SLIDER|1|820") == DeviceEvent(EventKind.SLIDER, 1, "820")


def test_invalid_message_is_ignored() -> None:
    assert parse_line("HCD_KEY|wrong|DOWN") is None
    assert parse_line("") is None
