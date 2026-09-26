from hackman_control_deck.supporter import normalized_supporter_endpoint


def test_supporter_endpoint_requires_https() -> None:
    assert normalized_supporter_endpoint("https://example.com/v1/supporter/") == (
        "https://example.com/v1/supporter"
    )
    assert normalized_supporter_endpoint("http://example.com") == ""
    assert normalized_supporter_endpoint(None) == ""
