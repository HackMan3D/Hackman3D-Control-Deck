from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PRIVATE_ROADMAP = ROOT / "roadmap.private.json"
MANIFEST_TEMPLATE = ROOT / "manifest.example.json"
PUBLIC_MANIFEST = ROOT / "manifest.json"


def progress(received_value: object, target_value: object) -> float:
    try:
        received = max(0.0, float(received_value))
        target = float(target_value)
    except (TypeError, ValueError):
        return 0.0
    if target <= 0:
        return 0.0
    return max(0.0, min(100.0, round(received * 100 / target, 1)))


def main() -> None:
    private = json.loads(PRIVATE_ROADMAP.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_TEMPLATE.read_text(encoding="utf-8"))
    received = private.get("total_received", 0)
    targets = private.get("targets", {})
    if not isinstance(targets, dict):
        targets = {}
    manifest["roadmap"] = {"progress": progress(received, targets.get("pro", 0))}
    PUBLIC_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Public roadmap generated: {manifest['roadmap']['progress']}%"
    )


if __name__ == "__main__":
    main()
