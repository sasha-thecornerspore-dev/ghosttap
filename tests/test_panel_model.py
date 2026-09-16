from pathlib import Path

from ghosttap.hierarchy import parse, flatten
from ghosttap.profiles import ManualLayout, LayoutButton
from ghosttap.panel_model import scale_factor, build_buttons, buttons_from_layout

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
