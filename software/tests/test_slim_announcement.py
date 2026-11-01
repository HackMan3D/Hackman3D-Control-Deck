from __future__ import annotations

from hackman_control_deck.constants import HCD_BASE_SLIM_MODEL_LINKS


def test_slim_model_links_are_the_published_pages() -> None:
    destinations = {key: url for key, _label, url, _icon in HCD_BASE_SLIM_MODEL_LINKS}
    assert destinations == {
        "creality": "https://www.crealitycloud.com/fr/model-detail/6ae7460c9ec5138bb62d7686",
        "makerworld": "https://makerworld.com/fr/models/3529353-hackman3d-control-deck-base-slim",
        "printables": "https://www.printables.com/model/1898404-hackman3d-control-deck-base-slim",
    }
