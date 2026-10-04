import re
from pathlib import Path

from hackman_control_deck import __version__
from hackman_control_deck.constants import APP_VERSION


ROOT = Path(__file__).resolve().parents[2]


def test_packaging_versions_match_application_version() -> None:
    assert __version__ == APP_VERSION
    expected = APP_VERSION
    files = {
        "pyproject": ROOT / "software/pyproject.toml",
        "spec": ROOT / "software/HackMan3D Control Deck.spec",
        "installer": ROOT / "software/windows_installer.iss",
        "windows metadata": ROOT / "software/scripts/windows_version_info.txt",
    }
    for label, path in files.items():
        assert expected in path.read_text(encoding="utf-8"), f"{label} does not use {expected}"

    for workflow in (ROOT / ".github/workflows").glob("build-*.yml"):
        text = workflow.read_text(encoding="utf-8")
        release_versions = set(re.findall(r"(?:v|Windows-|macOS-|_64-)(\d+\.\d+\.\d+)", text))
        assert release_versions == {expected}, (
            f"{workflow.name} contains release versions {release_versions}, expected {expected}"
        )
