from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .adb import DumpUnavailable
from .hierarchy import parse, flatten, label
from .panel_model import DrawButton, build_buttons, focused_field, preview_text

# Android keycodes used by the hardware-key row.
_KEY_BACK = 4
_KEY_HOME = 3
_KEY_RECENTS = 187
_KEY_POWER = 26
_KEY_ENTER = 66
_KEY_VOLUME_UP = 24
_KEY_VOLUME_DOWN = 25


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

        # Target field for the next typing action, refreshed with the screen.
        self._target_label = ""
        self._target_is_password = False
        # Confirm hook — swapped out in tests so the dialog never blocks.
        self._confirm = self._gui_confirm

        self.setWindowTitle("GhostTap")
        root = QVBoxLayout(self)

        self.status = QLabel("Ready.")
        root.addWidget(self.status)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        root.addWidget(refresh_btn)

        # The canvas keeps its logical size inside a scroll area so the input
        # controls below are always visible, however small the window is.
        self._canvas = _Canvas(self)
        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setWidgetResizable(False)
        root.addWidget(scroll, stretch=1)

        keys = QHBoxLayout()
        for name, code in [
            ("Back", _KEY_BACK),
            ("Home", _KEY_HOME),
            ("Recents", _KEY_RECENTS),
            ("Power", _KEY_POWER),
            ("Vol+", _KEY_VOLUME_UP),
            ("Vol-", _KEY_VOLUME_DOWN),
        ]:
            b = QPushButton(name)
            b.clicked.connect(lambda _checked=False, c=code: self._safe(lambda: self.client.keyevent(c)))
            keys.addWidget(b)
        root.addLayout(keys)

        self._target_lbl = QLabel("Typing into: (no field focused — tap one first)")
        root.addWidget(self._target_lbl)

        text_row = QHBoxLayout()
        self._text = QLineEdit()
        self._text.setPlaceholderText("type text / PIN")
        self._text.setEchoMode(QLineEdit.EchoMode.Password)
        type_btn = QPushButton("Type")
        type_btn.clicked.connect(self._type_text)
        enter_btn = QPushButton("Enter")
        enter_btn.clicked.connect(self._press_enter)
        text_row.addWidget(self._text)
        text_row.addWidget(type_btn)
        text_row.addWidget(enter_btn)
        root.addLayout(text_row)

        self.resize(480, 780)

    def refresh(self) -> None:
        try:
            xml = self.client.dump_ui()
            nodes = flatten(parse(xml))
            self.buttons = build_buttons(nodes, self.screen, self.canvas)
            self._update_target(nodes)
            try:
                focus = self.client.current_focus()
            except Exception:
                focus = ""
            self.status.setText(f"{len(self.buttons)} elements · {focus}")
        except DumpUnavailable:
            self.buttons = []
            self._update_target([])
            self.status.setText("This screen exposed no map (locked/secure). Use a manual layout or type a blind PIN.")
        except Exception as exc:
            self.buttons = []
            self._update_target([])
            self.status.setText(f"Error: {exc}")
        self._canvas.update()

    def _update_target(self, nodes) -> None:
        node = focused_field(nodes)
        if node is None:
            self._target_label = ""
            self._target_is_password = False
            self._target_lbl.setText("Typing into: (no field focused — tap one first)")
        else:
            self._target_label = label(node)
            self._target_is_password = node.password
            kind = "password/PIN" if node.password else "text"
            self._target_lbl.setText(f"Typing into: {self._target_label}  [{kind} field]")

    def handle_click(self, x: int, y: int) -> None:
        best = None
        best_area = None
        for btn in self.buttons:
            left, top, right, bottom = btn.rect
            if left <= x <= right and top <= y <= bottom:
                area = (right - left) * (bottom - top)
                if best_area is None or area < best_area:
                    best_area = area
                    best = btn
        if best is not None:
            self._safe(lambda b=best: self.client.tap(*b.tap))

    def _type_text(self) -> None:
        """Inject the text box into the device's focused field — but do NOT
        press Enter. The user reviews on the phone, then presses Enter
        separately, so nothing is submitted blindly."""
        text = self._text.text()
        if not text:
            self.status.setText("Nothing to type.")
            return
        target = self._target_label or "(no field detected — type anyway?)"
        if not self._confirm(preview_text(text, self._target_is_password), target):
            self.status.setText("Type cancelled.")
            return
        try:
            self.client.input_text(text)
        except Exception:
            # never include the exception text — it can contain the typed secret
            self.status.setText("Error: failed to type text")
            return
        self._text.clear()
        self.status.setText(
            f"Typed into {self._target_label or 'field'} — review on the phone, then press Enter."
        )

    def _press_enter(self) -> None:
        self._safe(lambda: self.client.keyevent(_KEY_ENTER))

    def _gui_confirm(self, preview: str, target: str) -> bool:
        reply = QMessageBox.question(
            self,
            "Confirm type",
            f"Type this into {target}?\n\n    {preview}\n\n"
            "(Enter is NOT pressed — you press it separately once it looks right.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:  # surface adb errors without crashing the UI
            self.status.setText(f"Error: {exc}")
            return
        # a device action likely changed the screen; re-dump shortly after
        self.refresh()
