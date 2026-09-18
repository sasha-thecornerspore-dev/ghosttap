"""Build a standalone GhostTap binary with PyInstaller.

Cross-platform: run `python packaging/build.py` on Windows or macOS.
- Windows -> dist/GhostTap.exe  (one file, windowed)
- macOS   -> dist/GhostTap.app  (windowed app bundle)
"""
from __future__ import annotations

import pathlib

import PyInstaller.__main__

ROOT = pathlib.Path(__file__).resolve().parents[1]

PyInstaller.__main__.run(
    [
        str(ROOT / "src" / "ghosttap" / "main.py"),
        "--name", "GhostTap",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(ROOT / "src"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]
)
