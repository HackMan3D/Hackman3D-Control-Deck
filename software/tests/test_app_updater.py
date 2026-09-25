import hashlib
from pathlib import Path

import pytest

from hackman_control_deck.app_updater import download_update


def test_downloader_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        download_update("http://example.com/update")


def test_checksum_shape_used_by_updater() -> None:
    payload = b"HackMan3D"
    assert hashlib.sha256(payload).hexdigest() == (
        "5fac83af46d92e81f41ae02af2654e5a2e0629abd46a15cb9fe0da0593fdca30"
    )
