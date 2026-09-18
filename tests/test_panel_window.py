import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ghosttap.panel import PanelWindow  # noqa: E402
from ghosttap.panel_model import DrawButton  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sample_dump.xml"

_app = QApplication.instance() or QApplication([])


class FakeClient:
    def __init__(self, xml):
        self._xml = xml
        self.taps = []
        self.keyevents = []
        self.input_texts = []

    def dump_ui(self):
        return self._xml

    def wm_size(self):
        return (1080, 2160)

    def current_focus(self):
        return "mCurrentFocus=Window{demo}"

    def tap(self, x, y):
        self.taps.append((x, y))

    def keyevent(self, code):
        self.keyevents.append(code)

    def input_text(self, s):
        self.input_texts.append(s)


def test_refresh_populates_buttons():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = PanelWindow(client, screen=(1080, 2160), canvas=(540, 1080))
    win.refresh()
    assert len(win.buttons) == 4
    labels = {b.label for b in win.buttons}
    assert "Sign in" in labels


def test_refresh_handles_unavailable_dump():
    from ghosttap.adb import DumpUnavailable

    class Blocked(FakeClient):
        def dump_ui(self):
            raise DumpUnavailable("locked")

    win = PanelWindow(Blocked(""), screen=(1080, 2160), canvas=(540, 1080))
    win.refresh()
    assert win.buttons == []


def test_handle_click_selects_deepest():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = PanelWindow(client, screen=(1080, 2160), canvas=(540, 1080))
    win.buttons = [
        DrawButton(label="container", rect=(0, 0, 400, 400), tap=(200, 200)),
        DrawButton(label="child", rect=(10, 10, 60, 60), tap=(35, 35)),
    ]

    win.handle_click(35, 35)

    assert client.taps == [(35, 35)]


def test_refresh_survives_adb_error():
    from ghosttap.adb import AdbError

    class Erroring(FakeClient):
        def dump_ui(self):
            raise AdbError("adb shell uiautomator dump failed: device offline")

    win = PanelWindow(Erroring(""), screen=(1080, 2160), canvas=(540, 1080))

    win.refresh()  # must not raise

    assert win.buttons == []
    assert win.status.text().startswith("Error")


def _win(client):
    win = PanelWindow(client, screen=(1080, 2160), canvas=(540, 1080))
    win._confirm = lambda preview, target: True  # never open a real dialog in tests
    return win


def test_type_injects_text_without_pressing_enter():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = _win(client)
    win._text.setText("1234")

    win._type_text()

    assert client.input_texts == ["1234"]  # text was injected
    assert client.keyevents == []           # but Enter was NOT sent
    assert win._text.text() == ""           # box cleared after typing


def test_type_is_cancelled_when_not_confirmed():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = _win(client)
    win._confirm = lambda preview, target: False
    win._text.setText("1234")

    win._type_text()

    assert client.input_texts == []  # nothing typed when the user declines
    assert client.keyevents == []


def test_type_failure_does_not_leak_secret():
    from ghosttap.adb import AdbError

    class FailingInput(FakeClient):
        def input_text(self, s):
            # Mirrors AdbClient._run, which embeds the raw command (including
            # the typed secret) into the exception message on a non-zero exit.
            raise AdbError(f"adb shell input text {s} failed: some device error")

    client = FailingInput(FIXTURE.read_text(encoding="utf-8"))
    win = _win(client)
    win._text.setText("1234")

    win._type_text()

    assert "1234" not in win.status.text()
    assert client.keyevents == []


def test_press_enter_sends_enter_keyevent():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = _win(client)

    win._press_enter()

    assert client.keyevents == [66]


def test_refresh_sets_target_from_focused_password_field():
    # The fixture has a focused password EditText (content-desc "Password").
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = _win(client)

    win.refresh()

    assert win._target_label == "Password"
    assert win._target_is_password is True


def test_update_banner_shown_when_update_passed():
    from ghosttap.update import Release

    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    rel = Release(tag="v9.9.9", version=(9, 9, 9), url="https://example/rel", assets=[])
    win = PanelWindow(client, screen=(1080, 2160), canvas=(540, 1080), update=rel)

    assert "v9.9.9" in win.update_banner.text()


def test_check_updates_reports_up_to_date():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = _win(client)
    win._update_check = lambda: None

    win._check_updates()

    assert "Up to date" in win.status.text()
