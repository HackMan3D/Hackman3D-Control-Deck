from __future__ import annotations

from hackman_control_deck.device import HcdDeviceManager


def test_pro_layout_is_paced_and_not_duplicated_during_upload() -> None:
    manager = HcdDeviceManager()
    manager._connected = True
    manager._transport = "wifi"
    written: list[str] = []
    manager._write_line = written.append  # type: ignore[method-assign]

    colors = {
        "screen": "#080808",
        "key": "#171717",
        "border": "#404040",
        "header": "#FFFFFF",
        "led": "#F02020",
    }
    manager.set_pro_layout({"1": "One"}, {"1": bytes(8192)}, colors=colors)

    assert written[0].startswith("HCD_PRO_DISPLAY|")
    assert written[1] == "HCD_PRO_COLORS|080808|171717|404040|FFFFFF|F02020"
    assert manager._pro_upload_queue[0].startswith("HCD_PRO_ICON_BEGIN|1|8192|")
    assert sum(
        command.startswith("HCD_PRO_ICON_CHUNK|")
        for command in manager._pro_upload_queue
    ) == 25
    initial_queue = tuple(manager._pro_upload_queue)

    manager.set_pro_layout({"1": "Changed"}, {"1": bytes([1]) * 8192}, colors=colors)
    assert tuple(manager._pro_upload_queue) == initial_queue
    manager._pro_upload_timer.stop()
