from __future__ import annotations

from dataclasses import dataclass

from .hierarchy import Node, actionable, label, center
from .profiles import ManualLayout


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
