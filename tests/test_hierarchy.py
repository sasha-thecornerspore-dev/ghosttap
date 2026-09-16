from pathlib import Path

from ghosttap.hierarchy import Node, parse, parse_bounds, flatten

FIXTURE = Path(__file__).parent / "fixtures" / "sample_dump.xml"


def _xml() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_bounds_basic():
    assert parse_bounds("[100,1800][980,1920]") == (100, 1800, 980, 1920)


def test_parse_bounds_garbage_returns_zero_rect():
    assert parse_bounds("") == (0, 0, 0, 0)
    assert parse_bounds("nonsense") == (0, 0, 0, 0)


def test_parse_returns_root_with_top_level_children():
    root = parse(_xml())
    assert isinstance(root, Node)
    # one top-level FrameLayout under the synthetic root
    assert len(root.children) == 1
    frame = root.children[0]
    assert frame.cls == "android.widget.FrameLayout"
    assert len(frame.children) == 5


def test_parse_reads_attributes():
    frame = parse(_xml()).children[0]
    sign_in = frame.children[0]
    assert sign_in.text == "Sign in"
    assert sign_in.resource_id == "com.example.app:id/sign_in"
    assert sign_in.clickable is True
    assert sign_in.bounds == (100, 1800, 980, 1920)

    password = frame.children[1]
    assert password.password is True
    assert password.content_desc == "Password"
    assert password.editable is True  # class endswith EditText


def test_flatten_counts_every_node():
    root = parse(_xml())
    # synthetic root + FrameLayout + 5 children = 7
    assert len(flatten(root)) == 7
