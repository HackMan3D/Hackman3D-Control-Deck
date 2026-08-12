from __future__ import annotations

from hackman_control_deck.device import HcdDeviceManager
from hackman_control_deck.protocol import DeviceInfo


def test_pro_layout_is_paced_and_not_duplicated_during_upload() -> None:
    manager = HcdDeviceManager()
    manager._connected = True
    manager._running = True
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

    assert written == []
    assert manager._pro_upload_queue[0] == "HCD_PRO_SYNC_BEGIN"
    assert manager._pro_upload_queue[1].startswith("HCD_PRO_DISPLAY|")
    assert manager._pro_upload_queue[2] == (
        "HCD_PRO_COLORS|080808|171717|404040|FFFFFF|F02020"
    )
    assert manager._pro_upload_queue[3].startswith("HCD_PRO_ICON_BEGIN|1|8192|")
    assert sum(
        command.startswith("HCD_PRO_ICON_CHUNK|")
        for command in manager._pro_upload_queue
    ) == 25
    assert manager._pro_upload_queue[-1] == "HCD_PRO_SYNC_END"
    assert "HCD_PRO_CACHE_COMMIT" not in manager._pro_upload_queue
    initial_queue = tuple(manager._pro_upload_queue)

    manager.set_pro_layout({"1": "Changed"}, {"1": bytes([1]) * 8192}, colors=colors)
    assert tuple(manager._pro_upload_queue) == initial_queue
    manager._pro_upload_timer.stop()


def test_pro_style_only_sync_is_wrapped_and_refreshed_once() -> None:
    manager = HcdDeviceManager()
    manager._connected = True
    manager._transport = "wifi"
    manager._pro_icon_signatures = {"1": None}

    assert manager.set_pro_layout(
        {"1": "One"},
        {},
        colors={"screen": "#111111", "key": "#222222"},
    )
    assert manager._pro_upload_queue[0] == "HCD_PRO_SYNC_BEGIN"
    assert manager._pro_upload_queue[-1] == "HCD_PRO_SYNC_END"
    assert "HCD_PRO_CACHE_COMMIT" not in manager._pro_upload_queue
    manager._pro_upload_timer.stop()


def test_stopped_manager_ignores_delayed_scans(monkeypatch) -> None:
    manager = HcdDeviceManager()
    attempts: list[str] = []
    monkeypatch.setattr(
        "hackman_control_deck.device.QSerialPortInfo.availablePorts",
        lambda: [],
    )
    monkeypatch.setattr(manager, "_send_discovery", lambda: attempts.append("discovery"))

    manager.start()
    manager.stop()
    manager._scan()

    assert attempts == ["discovery"]


def test_disconnect_resets_usb_candidates_for_immediate_rescan() -> None:
    manager = HcdDeviceManager()
    manager._candidate_ports = ["COM9"]
    manager._candidate_index = 1

    manager._close_connection()

    assert manager._candidate_ports == []
    assert manager._candidate_index == 0


def test_pro_upload_waits_for_network_backpressure(monkeypatch) -> None:
    manager = HcdDeviceManager()
    manager._connected = True
    manager._transport = "wifi"
    manager._pro_upload_queue.append("HCD_PRO_SYNC_END")
    written: list[str] = []
    monkeypatch.setattr(manager, "_write_line", written.append)
    monkeypatch.setattr(manager._tcp, "bytesToWrite", lambda: 20_000)

    manager._send_next_pro_upload()

    assert written == []
    assert list(manager._pro_upload_queue) == ["HCD_PRO_SYNC_END"]


def test_identity_is_requested_until_info_reply(monkeypatch) -> None:
    manager = HcdDeviceManager()
    manager._connected = True
    manager._running = True
    manager._transport = "serial"
    manager._last_pong = __import__("time").monotonic()
    written: list[str] = []
    received: list[DeviceInfo] = []
    monkeypatch.setattr(manager, "_transport_open", lambda: True)
    monkeypatch.setattr(manager, "_write_line", written.append)
    manager.info_received.connect(received.append)

    manager._heartbeat()
    assert written == ["HCD_PING", "HCD_GET_INFO"]

    manager._consume_data(
        b"HCD_INFO|HackMan3D Control Deck|HCD-BASE|1.7.0|9\n",
        manager._buffer,
        "serial",
    )
    manager._heartbeat()

    assert received and received[0].model_identifier == "HCD-BASE"
    assert written[-1] == "HCD_PING"
