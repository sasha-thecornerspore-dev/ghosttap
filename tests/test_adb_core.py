import subprocess

import pytest

from ghosttap.adb import AdbClient, Device, AdbError


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_builds_command_with_serial(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeCompleted(stdout="ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = AdbClient("adb.exe", serial="XYZ")
    out = client._run(["shell", "echo", "hi"])
    assert out == "ok"
    assert captured["cmd"] == ["adb.exe", "-s", "XYZ", "shell", "echo", "hi"]


def test_run_omits_serial_when_use_serial_false(monkeypatch):
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeCompleted(stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    AdbClient("adb.exe", serial="XYZ")._run(["devices"], use_serial=False)
    assert captured["cmd"] == ["adb.exe", "devices"]


def test_run_raises_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: FakeCompleted(returncode=1, stderr="boom"),
    )
    with pytest.raises(AdbError) as excinfo:
        AdbClient("adb.exe")._run(["shell", "true"])
    assert "boom" in str(excinfo.value)


def test_devices_parses_table(monkeypatch):
    table = "List of devices attached\n14SAXS00NVK\tdevice\nemulator-5554\toffline\n"
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: FakeCompleted(stdout=table))
    devices = AdbClient("adb.exe").devices()
    assert devices == [
        Device("14SAXS00NVK", "device"),
        Device("emulator-5554", "offline"),
    ]
