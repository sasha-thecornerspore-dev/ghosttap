from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ADB = "C:/Users/sasha/Programs/scrcpy-win64-v3.3.4/adb.exe"


def resolve_adb(adb_path: str) -> str:
    """Pick a usable adb binary: the configured path if it exists, else one on
    PATH, else the bare name 'adb' (let the OS resolve it). This keeps the app
    working on machines that don't have the bundled scrcpy path."""
    if adb_path and Path(adb_path).exists():
        return adb_path
    return shutil.which("adb") or "adb"


def _default_adb() -> str:
    return os.environ.get("GHOSTTAP_ADB", DEFAULT_ADB)


def _default_home() -> Path:
    override = os.environ.get("GHOSTTAP_HOME")
    return Path(override) if override else Path.home() / ".ghosttap"


@dataclass
class Config:
    adb_path: str = field(default_factory=_default_adb)
    data_dir: Path = field(default_factory=_default_home)

    @property
    def profiles_path(self) -> Path:
        return self.data_dir / "profiles.json"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
