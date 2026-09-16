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
        pass


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


def test_send_text_failure_does_not_leak_secret_or_submit_enter():
    from ghosttap.adb import AdbError

    class FailingInput(FakeClient):
        def input_text(self, s):
            # Mirrors AdbClient._run, which embeds the raw command (including
            # the typed secret) into the exception message on a non-zero exit.
            raise AdbError(f"adb shell input text {s} failed: some device error")

    client = FailingInput(FIXTURE.read_text(encoding="utf-8"))
    win = PanelWindow(client, screen=(1080, 2160), canvas=(540, 1080))
    win._text.setText("1234")

    win._send_text()

    assert "1234" not in win.status.text()
    assert client.keyevents == []
