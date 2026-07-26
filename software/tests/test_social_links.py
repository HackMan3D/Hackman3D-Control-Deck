from hackman_control_deck.constants import SOCIAL_LINKS


def test_all_hackman_links_are_configured() -> None:
    links = {key: url for key, _, url in SOCIAL_LINKS}

    assert set(links) == {
        "creality",
        "makerworld",
        "tiktok",
        "instagram",
        "youtube",
        "email",
        "paypal",
    }
    assert links["email"].startswith("mailto:hackman3d.pro@gmail.com")
    assert links["paypal"] == "https://paypal.me/Hackman3D"
