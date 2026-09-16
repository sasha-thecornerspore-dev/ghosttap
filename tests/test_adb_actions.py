import pytest

from ghosttap.adb import AdbClient, DumpUnavailable

HIER = "<?xml version='1.0'?><hierarchy rotation='0'></hierarchy>"


def make_client(monkeypatch, responder):
    """responder(args) -> stdout string; records calls in client._calls."""
    client = AdbClient("adb.exe", serial="XYZ")
    client._calls = []

    def fake_run(args, use_serial=True, timeout=None):
        client._calls.append(args)
        return responder(args)

    monkeypatch.setattr(client, "_run", fake_run)
    return client


def test_dump_ui_returns_hierarchy(monkeypatch):
    def responder(args):
        return HIER if args[:2] == ["exec-out", "cat"] else "dumped"

    client = make_client(monkeypatch, responder)
    assert "<hierarchy" in client.dump_ui()
    # first call dumps, second cats
    assert client._calls[0][:3] == ["shell", "uiautomator", "dump"]
    assert client._calls[1][:2] == ["exec-out", "cat"]


def test_dump_ui_raises_when_empty(monkeypatch):
    client = make_client(monkeypatch, lambda args: "" if args[:2] == ["exec-out", "cat"] else "dumped")
    with pytest.raises(DumpUnavailable):
        client.dump_ui()


def test_tap_builds_input_tap(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.tap(540, 1860)
    assert client._calls[-1] == ["shell", "input", "tap", "540", "1860"]


def test_swipe_builds_command(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.swipe(10, 20, 30, 40, 150)
    assert client._calls[-1] == ["shell", "input", "swipe", "10", "20", "30", "40", "150"]


def test_input_text_escapes_spaces(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.input_text("hello world")
    assert client._calls[-1] == ["shell", "input", "text", "hello%sworld"]


def test_keyevent_builds_command(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.keyevent(66)
    assert client._calls[-1] == ["shell", "input", "keyevent", "66"]


def test_wm_size_prefers_override(monkeypatch):
    out = "Physical size: 1080x2160\nOverride size: 720x1440\n"
    client = make_client(monkeypatch, lambda args: out)
    assert client.wm_size() == (720, 1440)


def test_wm_size_falls_back_to_physical(monkeypatch):
    client = make_client(monkeypatch, lambda args: "Physical size: 1080x2160\n")
    assert client.wm_size() == (1080, 2160)


def test_current_focus_extracts_line(monkeypatch):
    out = "  mCurrentFocus=Window{5b25622 u0 NotificationShade}\n"
    client = make_client(monkeypatch, lambda args: out)
    assert "NotificationShade" in client.current_focus()
