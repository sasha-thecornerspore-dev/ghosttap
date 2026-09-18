from pathlib import Path

import ghosttap.config as config
from ghosttap.config import Config, DEFAULT_ADB, resolve_adb


def test_default_adb_path(monkeypatch):
    monkeypatch.delenv("GHOSTTAP_ADB", raising=False)
    cfg = Config()
    assert cfg.adb_path == DEFAULT_ADB


def test_resolve_adb_prefers_existing_configured_path(tmp_path):
    fake_adb = tmp_path / "adb.exe"
    fake_adb.write_text("", encoding="utf-8")
    assert resolve_adb(str(fake_adb)) == str(fake_adb)


def test_resolve_adb_falls_back_to_path_lookup(monkeypatch):
    monkeypatch.setattr(config.shutil, "which", lambda name: "/usr/bin/adb")
    assert resolve_adb("/does/not/exist/adb.exe") == "/usr/bin/adb"


def test_resolve_adb_last_resort_is_bare_name(monkeypatch):
    monkeypatch.setattr(config.shutil, "which", lambda name: None)
    assert resolve_adb("/does/not/exist/adb.exe") == "adb"


def test_adb_env_override(monkeypatch):
    monkeypatch.setenv("GHOSTTAP_ADB", "D:/tools/adb.exe")
    cfg = Config()
    assert cfg.adb_path == "D:/tools/adb.exe"


def test_profiles_path_under_data_dir(tmp_path):
    cfg = Config(data_dir=tmp_path)
    assert cfg.profiles_path == tmp_path / "profiles.json"


def test_ensure_dirs_creates_data_dir(tmp_path):
    target = tmp_path / "nested" / "ghosttap"
    cfg = Config(data_dir=target)
    cfg.ensure_dirs()
    assert target.is_dir()
