import json
import re
from copy import deepcopy
from pathlib import Path

from .constants import profile_directory
from .models import Profile


class ProfileStore:
    PROFILE_FORMAT = "hackman-control-deck-profile"
    BACKUP_FORMAT = "hackman-control-deck-backup"
    FORMAT_VERSION = 1

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or profile_directory()
        self._root.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[str]:
        names = [path.stem for path in self._root.glob("*.json") if path.is_file()]
        if not names:
            self.save(Profile())
            return ["Default"]
        return sorted(names, key=str.casefold)

    def load(self, name: str) -> Profile:
        path = self._path(name)
        if not path.exists():
            profile = Profile(name=name)
            self.save(profile)
            return profile
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return Profile(name=name)
        return Profile.from_dict(data) if isinstance(data, dict) else Profile(name=name)

    def save(self, profile: Profile) -> None:
        path = self._path(profile.name)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(profile.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def create(self, requested_name: str) -> Profile:
        clean_name = requested_name.strip() or "New Profile"
        if self._path(clean_name).exists():
            raise FileExistsError(clean_name)
        profile = Profile(name=clean_name)
        self.save(profile)
        return profile

    def duplicate(self, name: str, requested_name: str | None = None) -> Profile:
        source = self.load(name)
        target_name = requested_name.strip() if requested_name else f"{name} Copy"
        target_name = self.available_name(target_name)
        profile = Profile.from_dict(deepcopy(source.to_dict()))
        profile.name = target_name
        self.save(profile)
        return profile

    def export_profile(self, name: str, destination: Path) -> None:
        payload = {
            "format": self.PROFILE_FORMAT,
            "version": self.FORMAT_VERSION,
            "profile": self.load(name).to_dict(),
        }
        self._write_json(destination, payload)

    def import_profile(self, source: Path) -> Profile:
        data = self._read_json(source)
        if data.get("format") != self.PROFILE_FORMAT or not isinstance(data.get("profile"), dict):
            raise ValueError("Unsupported HackMan3D Control Deck profile file")
        profile = Profile.from_dict(data["profile"])
        profile.name = self.available_name(profile.name)
        self.save(profile)
        return profile

    def export_backup(self, destination: Path) -> None:
        payload = {
            "format": self.BACKUP_FORMAT,
            "version": self.FORMAT_VERSION,
            "profiles": [self.load(name).to_dict() for name in self.list_profiles()],
        }
        self._write_json(destination, payload)

    def import_backup(self, source: Path) -> list[Profile]:
        data = self._read_json(source)
        raw_profiles = data.get("profiles")
        if data.get("format") != self.BACKUP_FORMAT or not isinstance(raw_profiles, list):
            raise ValueError("Unsupported HackMan3D Control Deck backup file")
        imported: list[Profile] = []
        for raw_profile in raw_profiles:
            if not isinstance(raw_profile, dict):
                continue
            profile = Profile.from_dict(raw_profile)
            profile.name = self.available_name(profile.name)
            self.save(profile)
            imported.append(profile)
        return imported

    def available_name(self, requested_name: str) -> str:
        base = requested_name.strip() or "Imported Profile"
        if not self._path(base).exists():
            return base
        index = 2
        while self._path(f"{base} {index}").exists():
            index += 1
        return f"{base} {index}"

    def rename(self, current_name: str, requested_name: str) -> Profile:
        clean_name = requested_name.strip()
        if not clean_name:
            raise ValueError("Profile name cannot be empty")

        current_path = self._path(current_name)
        target_path = self._path(clean_name)
        if target_path != current_path and target_path.exists():
            raise FileExistsError(clean_name)

        profile = self.load(current_name)
        profile.name = clean_name
        self.save(profile)
        if target_path != current_path:
            current_path.unlink(missing_ok=True)
        return profile

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)

    def _path(self, name: str) -> Path:
        safe_name = re.sub(r"[^\w .-]", "_", name, flags=re.UNICODE).strip(" .")
        return self._root / f"{safe_name or 'Profile'}.json"

    @staticmethod
    def _write_json(destination: Path, payload: dict[str, object]) -> None:
        destination.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _read_json(source: Path) -> dict[str, object]:
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("Invalid profile file") from error
        if not isinstance(data, dict):
            raise ValueError("Invalid profile file")
        return data
