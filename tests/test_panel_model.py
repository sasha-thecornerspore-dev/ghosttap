from pathlib import Path

from ghosttap.hierarchy import parse, flatten, Node
from ghosttap.profiles import ManualLayout, LayoutButton
from ghosttap.panel_model import (
    scale_factor,
    build_buttons,
    buttons_from_layout,
    focused_field,
    preview_text,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_dump.xml"


def test_scale_factor_uses_min_axis():
    assert scale_factor((1080, 2160), (540, 1080)) == 0.5


def test_scale_factor_zero_screen_is_one():
    assert scale_factor((0, 0), (540, 1080)) == 1.0


def test_build_buttons_scales_rect_and_keeps_device_tap():
    nodes = flatten(parse(FIXTURE.read_text(encoding="utf-8")))
    buttons = build_buttons(nodes, (1080, 2160), (540, 1080))
    assert len(buttons) == 4  # same as actionable count
    sign_in = next(b for b in buttons if b.label == "Sign in")
    assert sign_in.rect == (50, 900, 490, 960)   # bounds * 0.5
    assert sign_in.tap == (540, 1860)            # device center, unscaled


def test_buttons_from_layout_scales_and_centers():
    layout = ManualLayout(
        name="keyguard_pin",
        buttons=[LayoutButton(label="5", bounds=(400, 1200, 600, 1400))],
    )
    buttons = buttons_from_layout(layout, (1080, 2160), (540, 1080))
    assert buttons[0].label == "5"
    assert buttons[0].rect == (200, 600, 300, 700)
    assert buttons[0].tap == (500, 1300)


def _edit(rid, focused=False, password=False):
    return Node(
        cls="android.widget.EditText", resource_id=rid,
        bounds=(0, 0, 10, 10), focused=focused, password=password,
    )


def test_focused_field_prefers_focused_editable():
    a = _edit("a")
    b = _edit("b", focused=True)
    assert focused_field([a, b]) is b


def test_focused_field_falls_back_to_first_editable():
    label_node = Node(cls="android.widget.TextView", bounds=(0, 0, 10, 10))
    a = _edit("a")
    assert focused_field([label_node, a]) is a


def test_focused_field_none_when_no_editable():
    assert focused_field([Node(cls="android.widget.TextView", bounds=(0, 0, 10, 10))]) is None


def test_preview_masks_password():
    assert preview_text("1234", True) == "****  (4 digits)"


def test_preview_shows_plain_text():
    assert preview_text("hi there", False) == "hi there"
