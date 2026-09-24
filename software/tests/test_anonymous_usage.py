from hackman_control_deck.anonymous_usage import normalized_usage_endpoint, usage_payload


def test_usage_endpoint_requires_https() -> None:
    assert normalized_usage_endpoint("http://example.com/v1/usage") == ""
    assert normalized_usage_endpoint("https://example.com/v1/usage").startswith("https://")


def test_payload_contains_only_anonymous_grouped_fields() -> None:
    payload = usage_payload("temporary-session", "heartbeat", 4)
    assert payload == {
        "schema": 1,
        "session": "temporary-session",
        "event": "heartbeat",
        "actions": 4,
    }


def test_stop_payload_is_supported() -> None:
    assert usage_payload("temporary-session", "stop", 2)["event"] == "stop"


def test_installation_identifier_is_persistent(tmp_path) -> None:
    from PySide6.QtCore import QSettings
    from hackman_control_deck.anonymous_usage import installation_identifier
    settings = QSettings(str(tmp_path / "privacy.ini"), QSettings.IniFormat)
    first = installation_identifier(settings)
    assert len(first) >= 20
    assert installation_identifier(QSettings(str(tmp_path / "privacy.ini"), QSettings.IniFormat)) == first
    assert usage_payload("session", "start", 0, first)["installation"] == first
