from __future__ import annotations

from dataclasses import dataclass

from .hierarchy import Node, actionable, label, center
from .profiles import ManualLayout


def focused_field(nodes: list[Node]) -> Node | None:
    """The text field a typed string would land in: the focused editable node,
    else the first editable node, else None (nothing typable on screen)."""
    editables = [n for n in nodes if n.editable and n.enabled]
    for node in editables:
        if node.focused:
            return node
    return editables[0] if editables else None


def preview_text(text: str, is_password: bool) -> str:
    """A human-readable preview of what will be typed, for the confirm step.
    Password/PIN fields are masked (dots + digit count) so the value is never
    shown; other fields show the literal text."""
    if is_password:
        n = len(text)
        return "*" * n + f"  ({n} digit{'s' if n != 1 else ''})"
    return text


@dataclass
class DrawButton:
    label: str
    rect: tuple[int, int, int, int]   # scaled to the canvas
    tap: tuple[int, int]              # device coordinate to send to `input tap`


def scale_factor(screen: tuple[int, int], canvas: tuple[int, int]) -> float:
    sw, sh = screen
    cw, ch = canvas
    if sw <= 0 or sh <= 0:
        return 1.0
    return min(cw / sw, ch / sh)


def _scaled_rect(bounds: tuple[int, int, int, int], f: float) -> tuple[int, int, int, int]:
    left, top, right, bottom = bounds
    return (int(left * f), int(top * f), int(right * f), int(bottom * f))


def build_buttons(
    nodes: list[Node],
    screen: tuple[int, int],
    canvas: tuple[int, int],
) -> list[DrawButton]:
    f = scale_factor(screen, canvas)
    buttons: list[DrawButton] = []
    for node in actionable(nodes):
        buttons.append(
            DrawButton(
                label=label(node),
                rect=_scaled_rect(node.bounds, f),
                tap=center(node),
            )
        )
    return buttons


def buttons_from_layout(
    layout: ManualLayout,
    screen: tuple[int, int],
    canvas: tuple[int, int],
) -> list[DrawButton]:
    f = scale_factor(screen, canvas)
    buttons: list[DrawButton] = []
    for btn in layout.buttons:
        left, top, right, bottom = btn.bounds
        buttons.append(
            DrawButton(
                label=btn.label,
                rect=_scaled_rect(btn.bounds, f),
                tap=((left + right) // 2, (top + bottom) // 2),
            )
        )
    return buttons
