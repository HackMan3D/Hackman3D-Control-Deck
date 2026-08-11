from hackman_control_deck.favicon import favicon_candidates, normalized_website_url


def test_website_url_gets_https_scheme() -> None:
    assert normalized_website_url("example.com/page") == "https://example.com/page"


def test_declared_favicon_is_preferred_and_relative_url_is_resolved() -> None:
    html = b'<html><head><link rel="icon" href="/assets/site.png"></head></html>'

    candidates = favicon_candidates("https://example.com/page", html)

    assert candidates[0] == "https://example.com/assets/site.png"
    assert any(candidate.startswith("https://www.google.com/s2/favicons?") for candidate in candidates)
