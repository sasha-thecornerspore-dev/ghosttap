from ghosttap.profiles import (
    LayoutButton,
    ManualLayout,
    DeviceProfile,
    ProfileStore,
    save_store,
    load_store,
)


def test_get_or_create_is_idempotent():
    store = ProfileStore()
    a = store.get_or_create("XYZ")
    b = store.get_or_create("XYZ")
    assert a is b
    assert a.serial == "XYZ"


def test_load_missing_file_returns_empty(tmp_path):
    store = load_store(tmp_path / "nope.json")
    assert store.profiles == {}


def test_round_trip_preserves_layout_and_tuple_types(tmp_path):
    store = ProfileStore()
    prof = store.get_or_create("XYZ")
    prof.label = "Pixel 3a"
    prof.screen = (1080, 2160)
    prof.density = 400
    prof.manual_layouts["keyguard_pin"] = ManualLayout(
        name="keyguard_pin",
        buttons=[
            LayoutButton(label="5", bounds=(400, 1200, 600, 1400)),
            LayoutButton(label="OK", bounds=(700, 1600, 900, 1720), action="key", value="66"),
        ],
    )

    path = tmp_path / "profiles.json"
    save_store(store, path)
    loaded = load_store(path)

    p = loaded.profiles["XYZ"]
    assert p.label == "Pixel 3a"
    assert p.screen == (1080, 2160)
    assert isinstance(p.screen, tuple)
    layout = p.manual_layouts["keyguard_pin"]
    assert layout.buttons[0].bounds == (400, 1200, 600, 1400)
    assert isinstance(layout.buttons[0].bounds, tuple)
    assert layout.buttons[1].action == "key"
    assert layout.buttons[1].value == "66"
