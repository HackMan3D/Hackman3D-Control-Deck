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
