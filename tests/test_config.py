from pathlib import Path

from ghosttap.config import Config, DEFAULT_ADB


def test_default_adb_path():
    cfg = Config()
    assert cfg.adb_path == DEFAULT_ADB


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
