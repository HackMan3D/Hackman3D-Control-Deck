from hackman_control_deck.constants import ASSET_DIR


def test_device_render_is_packaged() -> None:
    render = ASSET_DIR / "hcd_device_render_off.png"

    assert render.is_file()
    assert render.stat().st_size > 100_000


def test_macos_icon_has_rounded_transparent_source() -> None:
    preview = ASSET_DIR / "hcd_app_icon_rounded.png"
    icon = ASSET_DIR / "hcd_app_icon.icns"

    png = preview.read_bytes()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert png[25] == 6  # PNG RGBA colour type.
    assert icon.read_bytes().startswith(b"icns")
