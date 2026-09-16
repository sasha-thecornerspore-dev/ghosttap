from pathlib import Path

from ghosttap.hierarchy import parse, flatten, actionable, label, center

FIXTURE = Path(__file__).parent / "fixtures" / "sample_dump.xml"


def _nodes():
    return flatten(parse(FIXTURE.read_text(encoding="utf-8")))


def test_actionable_selects_four_and_excludes_disabled_and_containers():
    act = actionable(_nodes())
    ids = {n.resource_id for n in act}
    # sign_in (clickable), password (editable), menu (clickable), list (scrollable)
    assert ids == {
        "com.example.app:id/sign_in",
        "com.example.app:id/password",
        "com.example.app:id/menu",
        "com.example.app:id/list",
    }
    # disabled_btn is clickable but enabled=false -> excluded
    assert "com.example.app:id/disabled_btn" not in ids


def test_label_prefers_text_then_desc_then_rid_then_class():
    act = {n.resource_id: n for n in actionable(_nodes())}
    assert label(act["com.example.app:id/sign_in"]) == "Sign in"       # text
    assert label(act["com.example.app:id/menu"]) == "Open menu"        # content_desc
    assert label(act["com.example.app:id/list"]) == "list"            # short resource-id


def test_center_is_integer_midpoint():
    act = {n.resource_id: n for n in actionable(_nodes())}
    assert center(act["com.example.app:id/sign_in"]) == (540, 1860)
