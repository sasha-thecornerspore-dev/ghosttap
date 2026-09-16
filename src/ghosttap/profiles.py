from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LayoutButton:
    label: str
    bounds: tuple[int, int, int, int]
    action: str = "tap"   # "tap" | "key" | "text"
    value: str = ""        # keycode string (action=key) or text (action=text)


@dataclass
class ManualLayout:
    name: str
    buttons: list[LayoutButton] = field(default_factory=list)


@dataclass
class DeviceProfile:
    serial: str
    label: str = ""
    screen: tuple[int, int] = (0, 0)
    density: int = 0
    manual_layouts: dict[str, ManualLayout] = field(default_factory=dict)


@dataclass
class ProfileStore:
    profiles: dict[str, DeviceProfile] = field(default_factory=dict)

    def get_or_create(self, serial: str) -> DeviceProfile:
        if serial not in self.profiles:
            self.profiles[serial] = DeviceProfile(serial=serial)
        return self.profiles[serial]


def _store_to_dict(store: ProfileStore) -> dict:
    return {
        "profiles": {
            serial: {
                "serial": p.serial,
                "label": p.label,
                "screen": list(p.screen),
                "density": p.density,
                "manual_layouts": {
                    name: {
                        "name": ml.name,
                        "buttons": [
                            {
                                "label": b.label,
                                "bounds": list(b.bounds),
                                "action": b.action,
                                "value": b.value,
                            }
                            for b in ml.buttons
                        ],
                    }
                    for name, ml in p.manual_layouts.items()
                },
            }
            for serial, p in store.profiles.items()
        }
    }


def _store_from_dict(data: dict) -> ProfileStore:
    store = ProfileStore()
    for serial, pd in data.get("profiles", {}).items():
        prof = DeviceProfile(
            serial=pd["serial"],
            label=pd.get("label", ""),
            screen=tuple(pd.get("screen", [0, 0])),
            density=pd.get("density", 0),
        )
        for name, mld in pd.get("manual_layouts", {}).items():
            prof.manual_layouts[name] = ManualLayout(
                name=mld["name"],
                buttons=[
                    LayoutButton(
                        label=b["label"],
                        bounds=tuple(b["bounds"]),
                        action=b.get("action", "tap"),
                        value=b.get("value", ""),
                    )
                    for b in mld.get("buttons", [])
                ],
            )
        store.profiles[serial] = prof
    return store


def save_store(store: ProfileStore, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_store_to_dict(store), indent=2), encoding="utf-8")


def load_store(path: Path) -> ProfileStore:
    if not path.exists():
        return ProfileStore()
    return _store_from_dict(json.loads(path.read_text(encoding="utf-8")))
