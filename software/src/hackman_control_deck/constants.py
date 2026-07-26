import os
import shutil
import sys
from pathlib import Path

APP_NAME = "HackMan3D Control Deck"
LEGACY_APP_NAME = "HackMan Control Deck"
COMPATIBLE_PRODUCT_NAMES = (APP_NAME, LEGACY_APP_NAME)
APP_SHORT_NAME = "HCD"
ORGANIZATION_NAME = "HackMan3D"
APP_VERSION = "0.17.0"
RELEASE_MANIFEST_URL = os.environ.get(
    "HCD_RELEASE_MANIFEST_URL",
    "",
)
RELEASE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60

CONTACT_EMAIL = "hackman3d.pro@gmail.com"
CONTACT_URL = "mailto:hackman3d.pro@gmail.com?subject=HackMan3D%20Control%20Deck%20feedback"
PAYPAL_URL = "https://paypal.me/Hackman3D"

SOCIAL_LINKS = (
    (
        "creality",
        "Creality Cloud",
        "https://www.crealitycloud.com/user/5221417142",
    ),
    ("makerworld", "MakerWorld", "https://makerworld.com/fr/@HackMan3D"),
    ("tiktok", "TikTok", "https://www.tiktok.com/@hackman3d"),
    ("instagram", "Instagram", "https://www.instagram.com/hackman_3dprint/"),
    ("youtube", "YouTube", "https://www.youtube.com/@hackman3D"),
    (
        "email",
        CONTACT_EMAIL,
        CONTACT_URL,
    ),
    (
        "paypal",
        "Support HackMan3D with PayPal",
        PAYPAL_URL,
    ),
)

BAUD_RATE = 115_200
HEARTBEAT_INTERVAL_MS = 1_000
CONNECTION_TIMEOUT_MS = 3_200
PORT_SCAN_INTERVAL_MS = 500
PORT_PROBE_TIMEOUT_MS = 600

PACKAGE_DIR = Path(__file__).resolve().parent
ASSET_DIR = PACKAGE_DIR / "assets"


def profile_directory() -> Path:
    override = os.environ.get("HCD_PROFILE_DIR")
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = root / ORGANIZATION_NAME / APP_NAME / "profiles"
    legacy_path = root / ORGANIZATION_NAME / LEGACY_APP_NAME / "profiles"
    if not path.exists() and legacy_path.is_dir():
        shutil.copytree(legacy_path, path)
    path.mkdir(parents=True, exist_ok=True)
    return path
