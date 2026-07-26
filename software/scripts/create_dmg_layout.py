from __future__ import annotations

import sys
from pathlib import Path

from ds_store import DSStore


def create_layout(stage: Path, volume_name: str) -> None:
    del volume_name

    browser = {
        "ShowStatusBar": False,
        "WindowBounds": "{{180, 180}, {660, 440}}",
        "ContainerShowSidebar": False,
        "PreviewPaneVisibility": False,
        "SidebarWidth": 0,
        "ShowTabView": False,
        "ShowToolbar": False,
        "ShowPathbar": False,
        "ShowSidebar": False,
    }
    icon_view = {
        "viewOptionsVersion": 1,
        "backgroundType": 1,
        "backgroundColorRed": 0.025,
        "backgroundColorGreen": 0.025,
        "backgroundColorBlue": 0.025,
        "gridOffsetX": 0.0,
        "gridOffsetY": 0.0,
        "gridSpacing": 100.0,
        "arrangeBy": "none",
        "showIconPreview": True,
        "showItemInfo": False,
        "labelOnBottom": True,
        "textSize": 13.0,
        "iconSize": 112.0,
        "scrollPositionX": 0.0,
        "scrollPositionY": 0.0,
    }

    with DSStore.open(str(stage / ".DS_Store"), "w+") as store:
        store["."]["vSrn"] = ("long", 1)
        store["."]["bwsp"] = browser
        store["."]["icvp"] = icon_view
        store["."]["icvl"] = ("type", "icnv")
        store["HackMan3D Control Deck.app"]["Iloc"] = (170, 250)
        store["→.png"]["Iloc"] = (330, 250)
        store["Applications"]["Iloc"] = (490, 250)


if __name__ == "__main__":
    create_layout(Path(sys.argv[1]).resolve(), sys.argv[2])
