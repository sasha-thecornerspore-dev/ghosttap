from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .adb import DumpUnavailable
from .hierarchy import parse, flatten
from .panel_model import DrawButton, build_buttons

# Android keycodes used by the hardware-key row.
_KEY_BACK = 4
_KEY_HOME = 3
_KEY_RECENTS = 187
_KEY_POWER = 26
_KEY_ENTER = 66


class _Canvas(QWidget):
    """Draws DrawButtons and routes clicks back to the owning PanelWindow."""

    def __init__(self, owner: "PanelWindow"):
        super().__init__()
        self._owner = owner
        self.setMinimumSize(owner.canvas[0], owner.canvas[1])

    def paintEvent(self, event):  # noqa: N802 (Qt signature)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 24))
        pen = QPen(QColor(0, 200, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        for btn in self._owner.buttons:
            left, top, right, bottom = btn.rect
            rect = QRect(left, top, right - left, bottom - top)
            painter.drawRect(rect)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, btn.label)

    def mousePressEvent(self, event):  # noqa: N802 (Qt signature)
        pos = event.position()
        self._owner.handle_click(int(pos.x()), int(pos.y()))


class PanelWindow(QWidget):
    def __init__(self, client, screen: tuple[int, int], canvas: tuple[int, int] = (450, 900)):
        super().__init__()
        self.client = client
        self.screen = screen
        self.canvas = canvas
        self.buttons: list[DrawButton] = []

        self.setWindowTitle("GhostTap")
        root = QVBoxLayout(self)

        self.status = QLabel("Ready.")
        root.addWidget(self.status)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        root.addWidget(refresh_btn)

        self._canvas = _Canvas(self)
        root.addWidget(self._canvas)

        keys = QHBoxLayout()
        for name, code in [
            ("Back", _KEY_BACK),
            ("Home", _KEY_HOME),
            ("Recents", _KEY_RECENTS),
            ("Power", _KEY_POWER),
        ]:
            b = QPushButton(name)
            b.clicked.connect(lambda _checked=False, c=code: self._safe(lambda: self.client.keyevent(c)))
            keys.addWidget(b)
        root.addLayout(keys)

        text_row = QHBoxLayout()
        self._text = QLineEdit()
        self._text.setPlaceholderText("type text / PIN, then Send")
        send = QPushButton("Send")
        send.clicked.connect(self._send_text)
        text_row.addWidget(self._text)
        text_row.addWidget(send)
        root.addLayout(text_row)

    def refresh(self) -> None:
        try:
            xml = self.client.dump_ui()
        except DumpUnavailable:
            self.buttons = []
            self.status.setText("This screen exposed no map (locked/secure). Use a manual layout or Send a blind PIN.")
            self._canvas.update()
            return
        nodes = flatten(parse(xml))
        self.buttons = build_buttons(nodes, self.screen, self.canvas)
        self.status.setText(f"{len(self.buttons)} elements · {self.client.current_focus()}")
        self._canvas.update()

    def handle_click(self, x: int, y: int) -> None:
        for btn in self.buttons:
            left, top, right, bottom = btn.rect
            if left <= x <= right and top <= y <= bottom:
                self._safe(lambda b=btn: self.client.tap(*b.tap))
                return

    def _send_text(self) -> None:
        text = self._text.text()
        if not text:
            return
        self._safe(lambda: self.client.input_text(text))
        self._safe(lambda: self.client.keyevent(_KEY_ENTER))
        self._text.clear()

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:  # surface adb errors without crashing the UI
            self.status.setText(f"Error: {exc}")
            return
        # a device action likely changed the screen; re-dump shortly after
        self.refresh()
