import json

from hackman_control_deck.release_feed import parse_release_feed, version_key


def test_release_feed_selects_platform_download_and_clamps_progress() -> None:
    payload = json.dumps(
        {
            "schema": 1,
            "latest_version": "0.18.0",
            "downloads": {
                "macos": "https://example.com/mac",
                "windows": "https://example.com/windows",
            },
            "roadmap": {"plus": 48.4, "pro": 140},
        }
    ).encode()

    data = parse_release_feed(payload)

    assert data.latest_version == "0.18.0"
    assert data.plus_progress == 48
    assert data.pro_progress == 100
    assert data.download_url.startswith("https://example.com/")
    assert data.update_available


def test_release_feed_defaults_invalid_percentages_to_zero() -> None:
    payload = json.dumps(
        {
            "schema": 1,
            "latest_version": "0.17.2",
            "downloads": {},
            "roadmap": {"plus": "unknown", "pro": -3},
        }
    ).encode()

    data = parse_release_feed(payload)

    assert data.plus_progress == 0
    assert data.pro_progress == 0
    assert not data.update_available


def test_versions_are_compared_numerically() -> None:
    assert version_key("0.20.0") > version_key("0.9.9")
