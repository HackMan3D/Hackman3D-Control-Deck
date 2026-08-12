import json

from hackman_control_deck.release_feed import parse_release_feed, version_key


def test_release_feed_selects_platform_download_and_clamps_progress() -> None:
    payload = json.dumps(
        {
            "schema": 1,
            "latest_version": "1.5.5",
            "downloads": {
                "macos": "https://example.com/mac",
                "windows": "https://example.com/windows",
            },
            "roadmap": {"progress": 48.4},
        }
    ).encode()

    data = parse_release_feed(payload)

    assert data.latest_version == "1.5.5"
    assert data.roadmap_progress == 48.4
    assert data.download_url.startswith("https://example.com/")
    assert data.update_available


def test_release_feed_defaults_invalid_percentages_to_zero() -> None:
    payload = json.dumps(
        {
            "schema": 1,
            "latest_version": "1.0.0",
            "downloads": {},
            "roadmap": {"progress": "unknown"},
        }
    ).encode()

    data = parse_release_feed(payload)

    assert data.roadmap_progress == 0
    assert not data.update_available


def test_versions_are_compared_numerically() -> None:
    assert version_key("0.20.0") > version_key("0.9.9")
