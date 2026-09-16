import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ghosttap.panel import PanelWindow  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sample_dump.xml"

_app = QApplication.instance() or QApplication([])


class FakeClient:
    def __init__(self, xml):
        self._xml = xml
        self.taps = []

    def dump_ui(self):
        return self._xml

    def wm_size(self):
        return (1080, 2160)

    def current_focus(self):
        return "mCurrentFocus=Window{demo}"

    def tap(self, x, y):
        self.taps.append((x, y))

    def keyevent(self, code):
        pass

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
