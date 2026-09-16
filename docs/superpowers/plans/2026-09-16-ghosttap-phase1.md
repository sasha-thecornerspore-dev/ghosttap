# GhostTap Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone GhostTap panel that reconstructs a clickable map of an Android screen from `adb`'s accessibility dump and taps the real device, so a phone can be operated from the PC even when scrcpy shows a black `FLAG_SECURE` surface or the physical screen is broken. No AI in this phase.

**Architecture:** A layered, all-Python app. A thin `AdbClient` shells out to the bundled adb binary using argument lists; a pure `hierarchy` module parses the dump XML into `Node`s and filters/labels/centers actionable ones; a `profiles` module persists per-device data and manual fallback layouts (for the keyguard); a pure `PanelModel` turns nodes into scaled draw-rects + tap coordinates; a thin PyQt6 `PanelWindow` renders them and routes clicks. Everything testable is kept out of the Qt widgets.

**Tech Stack:** Python 3.14, PyQt6 (>=6.11, verified cp314 wheel), stdlib `subprocess` / `xml.etree` / `json`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-ghosttap-design.md`

## Global Constraints

- Target runtime **Python 3.14**; `requires-python = ">=3.12"`.
- Qt binding is **PyQt6 >= 6.11** (has cp314 wheels; verified). If it ever fails to install, PySide6 6.11 is a drop-in with import name changes only — not expected, do not use preemptively.
- **No root, no on-device app install.** Interaction is adb-only.
- adb binary default: `C:/Users/sasha/Programs/scrcpy-win64-v3.3.4/adb.exe`, overridable via env var `GHOSTTAP_ADB`.
- **All subprocess calls use argument lists, never shell strings** (this is what avoids the Git-Bash `/sdcard` path mangling seen during probing).
- Source uses a **src layout**: modules live in `src/ghosttap/`, imported as `from ghosttap.X import ...`. `pyproject.toml` sets `pythonpath = ["src"]` for pytest.
- **Secrets (PINs, passwords) are never logged and never leave the machine.** No `print`/log of `input_text` arguments.
- **Every commit message ends with the trailer** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (shown via a second `-m` in each commit step).

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/ghosttap/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `ghosttap` package and a working `pytest` (with `src` on the path).

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "ghosttap"
version = "0.1.0"
description = "Operate an Android device from the PC via adb when the screen is black or broken."
requires-python = ">=3.12"
dependencies = ["PyQt6>=6.11"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package + test package markers**

Create `src/ghosttap/__init__.py`:

```python
"""GhostTap: operate an Android device from the PC via adb."""

__version__ = "0.1.0"
```

Create empty `tests/__init__.py` (no content needed).

- [ ] **Step 3: Write a smoke test**

Create `tests/test_smoke.py`:

```python
def test_package_imports():
    import ghosttap

    assert ghosttap.__version__ == "0.1.0"
```

- [ ] **Step 4: Install dev deps and run the smoke test**

Run:
```bash
pip install pytest
python -m pytest tests/test_smoke.py -v
```
Expected: PASS (1 passed). If `ghosttap` fails to import, confirm `pyproject.toml` has `pythonpath = ["src"]`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ghosttap/__init__.py tests/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold ghosttap package and pytest" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `config.py` — paths and adb location

**Files:**
- Create: `src/ghosttap/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Config` dataclass with fields `adb_path: str`, `data_dir: Path`.
  - `Config.profiles_path -> Path` property (`data_dir / "profiles.json"`).
  - `Config.ensure_dirs() -> None`.
  - Env overrides: `GHOSTTAP_ADB` (adb path), `GHOSTTAP_HOME` (data dir).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

from ghosttap.config import Config, DEFAULT_ADB


def test_default_adb_path():
    cfg = Config()
    assert cfg.adb_path == DEFAULT_ADB


def test_adb_env_override(monkeypatch):
    monkeypatch.setenv("GHOSTTAP_ADB", "D:/tools/adb.exe")
    cfg = Config()
    assert cfg.adb_path == "D:/tools/adb.exe"


def test_profiles_path_under_data_dir(tmp_path):
    cfg = Config(data_dir=tmp_path)
    assert cfg.profiles_path == tmp_path / "profiles.json"


def test_ensure_dirs_creates_data_dir(tmp_path):
    target = tmp_path / "nested" / "ghosttap"
    cfg = Config(data_dir=target)
    cfg.ensure_dirs()
    assert target.is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ghosttap.config'`.

- [ ] **Step 3: Implement `config.py`**

Create `src/ghosttap/config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ADB = "C:/Users/sasha/Programs/scrcpy-win64-v3.3.4/adb.exe"


def _default_adb() -> str:
    return os.environ.get("GHOSTTAP_ADB", DEFAULT_ADB)


def _default_home() -> Path:
    override = os.environ.get("GHOSTTAP_HOME")
    return Path(override) if override else Path.home() / ".ghosttap"


@dataclass
class Config:
    adb_path: str = field(default_factory=_default_adb)
    data_dir: Path = field(default_factory=_default_home)

    @property
    def profiles_path(self) -> Path:
        return self.data_dir / "profiles.json"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ghosttap/config.py tests/test_config.py
git commit -m "feat: add Config with adb path and data dir resolution" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `hierarchy.py` — Node model, bounds, parse, flatten

**Files:**
- Create: `src/ghosttap/hierarchy.py`
- Create: `tests/fixtures/sample_dump.xml`
- Test: `tests/test_hierarchy.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Node` dataclass: `text, resource_id, content_desc, cls, package: str`; `bounds: tuple[int,int,int,int]`; `clickable, long_clickable, scrollable, password, focused: bool`; `enabled: bool = True`; `children: list[Node]`; and property `editable: bool`.
  - `parse_bounds(s: str) -> tuple[int,int,int,int]`.
  - `parse(xml: str) -> Node` (returns a synthetic root whose `children` are the top-level nodes).
  - `flatten(node: Node) -> list[Node]`.

- [ ] **Step 1: Create the test fixture**

Create `tests/fixtures/sample_dump.xml` (mirrors real uiautomator output; five children under one container):

```xml
<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.app" content-desc="" clickable="false" enabled="true" scrollable="false" long-clickable="false" password="false" focused="false" bounds="[0,0][1080,2160]">
    <node index="0" text="Sign in" resource-id="com.example.app:id/sign_in" class="android.widget.Button" package="com.example.app" content-desc="" clickable="true" enabled="true" scrollable="false" long-clickable="false" password="false" focused="false" bounds="[100,1800][980,1920]" />
    <node index="1" text="" resource-id="com.example.app:id/password" class="android.widget.EditText" package="com.example.app" content-desc="Password" clickable="true" enabled="true" scrollable="false" long-clickable="false" password="true" focused="true" bounds="[100,1000][980,1100]" />
    <node index="2" text="" resource-id="com.example.app:id/menu" class="android.widget.ImageButton" package="com.example.app" content-desc="Open menu" clickable="true" enabled="true" scrollable="false" long-clickable="false" password="false" focused="false" bounds="[20,60][140,180]" />
    <node index="3" text="" resource-id="com.example.app:id/list" class="androidx.recyclerview.widget.RecyclerView" package="com.example.app" content-desc="" clickable="false" enabled="true" scrollable="true" long-clickable="false" password="false" focused="false" bounds="[0,200][1080,1000]" />
    <node index="4" text="Disabled" resource-id="com.example.app:id/disabled_btn" class="android.widget.Button" package="com.example.app" content-desc="" clickable="true" enabled="false" scrollable="false" long-clickable="false" password="false" focused="false" bounds="[100,1600][980,1720]" />
  </node>
</hierarchy>
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_hierarchy.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_hierarchy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ghosttap.hierarchy'`.

- [ ] **Step 4: Implement the model, bounds, parse, flatten**

Create `src/ghosttap/hierarchy.py`:

```python
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


@dataclass
class Node:
    text: str = ""
    resource_id: str = ""
    content_desc: str = ""
    cls: str = ""
    package: str = ""
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
    clickable: bool = False
    long_clickable: bool = False
    scrollable: bool = False
    password: bool = False
    focused: bool = False
    enabled: bool = True
    children: list["Node"] = field(default_factory=list)

    @property
    def editable(self) -> bool:
        return self.cls.endswith("EditText") or self.password


def _flag(value: str) -> bool:
    return value == "true"


def parse_bounds(s: str) -> tuple[int, int, int, int]:
    match = _BOUNDS_RE.search(s or "")
    if not match:
        return (0, 0, 0, 0)
    left, top, right, bottom = (int(g) for g in match.groups())
    return (left, top, right, bottom)


def _node_from_el(el: ET.Element) -> Node:
    a = el.attrib
    return Node(
        text=a.get("text", ""),
        resource_id=a.get("resource-id", ""),
        content_desc=a.get("content-desc", ""),
        cls=a.get("class", ""),
        package=a.get("package", ""),
        bounds=parse_bounds(a.get("bounds", "")),
        clickable=_flag(a.get("clickable", "false")),
        long_clickable=_flag(a.get("long-clickable", "false")),
        scrollable=_flag(a.get("scrollable", "false")),
        password=_flag(a.get("password", "false")),
        focused=_flag(a.get("focused", "false")),
        enabled=_flag(a.get("enabled", "true")),
        children=[_node_from_el(c) for c in el if c.tag == "node"],
    )


def parse(xml: str) -> Node:
    root_el = ET.fromstring(xml)
    root = Node(cls=root_el.tag)  # synthetic "hierarchy" root
    root.children = [_node_from_el(c) for c in root_el if c.tag == "node"]
    return root


def flatten(node: Node) -> list[Node]:
    out = [node]
    for child in node.children:
        out.extend(flatten(child))
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_hierarchy.py -v`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add src/ghosttap/hierarchy.py tests/test_hierarchy.py tests/fixtures/sample_dump.xml
git commit -m "feat: parse uiautomator dump into a Node tree" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `hierarchy.py` — actionable filter, label, center

**Files:**
- Modify: `src/ghosttap/hierarchy.py` (append functions)
- Test: `tests/test_hierarchy_actionable.py`

**Interfaces:**
- Consumes: `Node`, `flatten`, `parse` from Task 3.
- Produces:
  - `actionable(nodes: list[Node]) -> list[Node]` — keeps enabled nodes with a non-degenerate rect that are `clickable` or `long_clickable` or `scrollable` or `editable`.
  - `label(node: Node) -> str` — first non-empty of `text` → `content_desc` → short resource-id (after `/`) → class basename → `"?"`.
  - `center(node: Node) -> tuple[int, int]` — integer midpoint of bounds.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_hierarchy_actionable.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_hierarchy_actionable.py -v`
Expected: FAIL with `ImportError: cannot import name 'actionable'`.

- [ ] **Step 3: Append the implementation to `hierarchy.py`**

Add to the end of `src/ghosttap/hierarchy.py`:

```python
def actionable(nodes: list[Node]) -> list[Node]:
    result: list[Node] = []
    for n in nodes:
        if not n.enabled:
            continue
        left, top, right, bottom = n.bounds
        if right <= left or bottom <= top:
            continue
        if n.clickable or n.long_clickable or n.scrollable or n.editable:
            result.append(n)
    return result


def _short_rid(resource_id: str) -> str:
    return resource_id.split("/")[-1] if "/" in resource_id else resource_id


def label(node: Node) -> str:
    if node.text.strip():
        return node.text.strip()
    if node.content_desc.strip():
        return node.content_desc.strip()
    if node.resource_id:
        return _short_rid(node.resource_id)
    if node.cls:
        return node.cls.split(".")[-1]
    return "?"


def center(node: Node) -> tuple[int, int]:
    left, top, right, bottom = node.bounds
    return ((left + right) // 2, (top + bottom) // 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_hierarchy_actionable.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ghosttap/hierarchy.py tests/test_hierarchy_actionable.py
git commit -m "feat: filter actionable nodes and derive label/center" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `adb.py` — client core: run wrapper, devices, errors

**Files:**
- Create: `src/ghosttap/adb.py`
- Test: `tests/test_adb_core.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Exceptions `AdbError(RuntimeError)` and `DumpUnavailable(AdbError)`.
  - `Device` dataclass: `serial: str`, `state: str`.
  - `AdbClient(adb_path: str, serial: str | None = None, timeout: float = 20.0)`.
  - `AdbClient._run(args: list[str], use_serial: bool = True, timeout: float | None = None) -> str` (raises `AdbError` on non-zero exit).
  - `AdbClient.devices() -> list[Device]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_adb_core.py`:

```python
import subprocess

import pytest

from ghosttap.adb import AdbClient, Device, AdbError


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_builds_command_with_serial(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeCompleted(stdout="ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = AdbClient("adb.exe", serial="XYZ")
    out = client._run(["shell", "echo", "hi"])
    assert out == "ok"
    assert captured["cmd"] == ["adb.exe", "-s", "XYZ", "shell", "echo", "hi"]


def test_run_omits_serial_when_use_serial_false(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: captured.setdefault("cmd", cmd) or FakeCompleted(stdout=""),
    )
    AdbClient("adb.exe", serial="XYZ")._run(["devices"], use_serial=False)
    assert captured["cmd"] == ["adb.exe", "devices"]


def test_run_raises_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: FakeCompleted(returncode=1, stderr="boom"),
    )
    with pytest.raises(AdbError) as excinfo:
        AdbClient("adb.exe")._run(["shell", "true"])
    assert "boom" in str(excinfo.value)


def test_devices_parses_table(monkeypatch):
    table = "List of devices attached\n14SAXS00NVK\tdevice\nemulator-5554\toffline\n"
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: FakeCompleted(stdout=table))
    devices = AdbClient("adb.exe").devices()
    assert devices == [
        Device("14SAXS00NVK", "device"),
        Device("emulator-5554", "offline"),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_adb_core.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ghosttap.adb'`.

- [ ] **Step 3: Implement the client core**

Create `src/ghosttap/adb.py`:

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass


class AdbError(RuntimeError):
    """An adb command exited non-zero or produced unusable output."""


class DumpUnavailable(AdbError):
    """uiautomator dump returned no usable hierarchy (e.g. a locked keyguard)."""


@dataclass
class Device:
    serial: str
    state: str


class AdbClient:
    def __init__(self, adb_path: str, serial: str | None = None, timeout: float = 20.0):
        self.adb_path = adb_path
        self.serial = serial
        self.timeout = timeout

    def _run(
        self,
        args: list[str],
        use_serial: bool = True,
        timeout: float | None = None,
    ) -> str:
        cmd = [self.adb_path]
        if use_serial and self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or self.timeout,
        )
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip()
            raise AdbError(f"adb {' '.join(args)} failed: {detail}")
        return proc.stdout

    def devices(self) -> list[Device]:
        out = self._run(["devices"], use_serial=False)
        result: list[Device] = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            serial, state = line.split("\t", 1)
            result.append(Device(serial.strip(), state.strip()))
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_adb_core.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ghosttap/adb.py tests/test_adb_core.py
git commit -m "feat: add AdbClient core with run wrapper and device listing" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `adb.py` — dump, input actions, screen queries

**Files:**
- Modify: `src/ghosttap/adb.py` (add methods to `AdbClient`)
- Test: `tests/test_adb_actions.py`

**Interfaces:**
- Consumes: `AdbClient`, `AdbError`, `DumpUnavailable` from Task 5.
- Produces (methods on `AdbClient`):
  - `dump_ui() -> str` — runs `uiautomator dump` then `exec-out cat`; raises `DumpUnavailable` if the result has no `<hierarchy`.
  - `tap(x: int, y: int) -> None`, `swipe(x1, y1, x2, y2, ms: int = 200) -> None`.
  - `input_text(s: str) -> None` (spaces sent as `%s`).
  - `keyevent(code: int) -> None`.
  - `wm_size() -> tuple[int, int]` (prefers `Override size`, else `Physical size`).
  - `current_focus() -> str` (the `mCurrentFocus` line, or `""`).
  - `wake() -> None` (keyevent 224), `sleep() -> None` (keyevent 223).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_adb_actions.py`:

```python
import pytest

from ghosttap.adb import AdbClient, DumpUnavailable

HIER = "<?xml version='1.0'?><hierarchy rotation='0'></hierarchy>"


def make_client(monkeypatch, responder):
    """responder(args) -> stdout string; records calls in client._calls."""
    client = AdbClient("adb.exe", serial="XYZ")
    client._calls = []

    def fake_run(args, use_serial=True, timeout=None):
        client._calls.append(args)
        return responder(args)

    monkeypatch.setattr(client, "_run", fake_run)
    return client


def test_dump_ui_returns_hierarchy(monkeypatch):
    def responder(args):
        return HIER if args[:2] == ["exec-out", "cat"] else "dumped"

    client = make_client(monkeypatch, responder)
    assert "<hierarchy" in client.dump_ui()
    # first call dumps, second cats
    assert client._calls[0][:3] == ["shell", "uiautomator", "dump"]
    assert client._calls[1][:2] == ["exec-out", "cat"]


def test_dump_ui_raises_when_empty(monkeypatch):
    client = make_client(monkeypatch, lambda args: "" if args[:2] == ["exec-out", "cat"] else "dumped")
    with pytest.raises(DumpUnavailable):
        client.dump_ui()


def test_tap_builds_input_tap(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.tap(540, 1860)
    assert client._calls[-1] == ["shell", "input", "tap", "540", "1860"]


def test_input_text_escapes_spaces(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.input_text("hello world")
    assert client._calls[-1] == ["shell", "input", "text", "hello%sworld"]


def test_keyevent_builds_command(monkeypatch):
    client = make_client(monkeypatch, lambda args: "")
    client.keyevent(66)
    assert client._calls[-1] == ["shell", "input", "keyevent", "66"]


def test_wm_size_prefers_override(monkeypatch):
    out = "Physical size: 1080x2160\nOverride size: 720x1440\n"
    client = make_client(monkeypatch, lambda args: out)
    assert client.wm_size() == (720, 1440)


def test_wm_size_falls_back_to_physical(monkeypatch):
    client = make_client(monkeypatch, lambda args: "Physical size: 1080x2160\n")
    assert client.wm_size() == (1080, 2160)


def test_current_focus_extracts_line(monkeypatch):
    out = "  mCurrentFocus=Window{5b25622 u0 NotificationShade}\n"
    client = make_client(monkeypatch, lambda args: out)
    assert "NotificationShade" in client.current_focus()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_adb_actions.py -v`
Expected: FAIL with `AttributeError: 'AdbClient' object has no attribute 'dump_ui'`.

- [ ] **Step 3: Add methods to `AdbClient`**

Append inside the `AdbClient` class in `src/ghosttap/adb.py` (same indentation as `devices`):

```python
    _DUMP_PATH = "/sdcard/ghosttap_dump.xml"

    def dump_ui(self) -> str:
        self._run(["shell", "uiautomator", "dump", self._DUMP_PATH])
        xml = self._run(["exec-out", "cat", self._DUMP_PATH])
        if "<hierarchy" not in xml:
            raise DumpUnavailable("uiautomator dump returned no hierarchy")
        return xml

    def tap(self, x: int, y: int) -> None:
        self._run(["shell", "input", "tap", str(x), str(y)])

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 200) -> None:
        self._run(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(ms)])

    def input_text(self, s: str) -> None:
        # `input text` treats spaces as argument separators; %s is the accepted escape.
        self._run(["shell", "input", "text", s.replace(" ", "%s")])

    def keyevent(self, code: int) -> None:
        self._run(["shell", "input", "keyevent", str(code)])

    def wm_size(self) -> tuple[int, int]:
        out = self._run(["shell", "wm", "size"])
        target = None
        for line in out.splitlines():
            if "Override size" in line:
                target = line
        if target is None:
            for line in out.splitlines():
                if "Physical size" in line:
                    target = line
        if target is None:
            raise AdbError(f"could not parse wm size from: {out!r}")
        w_str, h_str = target.split(":", 1)[1].strip().lower().split("x")
        return (int(w_str), int(h_str))

    def current_focus(self) -> str:
        out = self._run(["shell", "dumpsys", "window"])
        for line in out.splitlines():
            if "mCurrentFocus" in line:
                return line.strip()
        return ""

    def wake(self) -> None:
        self.keyevent(224)

    def sleep(self) -> None:
        self.keyevent(223)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_adb_actions.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ghosttap/adb.py tests/test_adb_actions.py
git commit -m "feat: add dump_ui, input actions, and screen queries to AdbClient" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `profiles.py` — device profiles and manual layouts

**Files:**
- Create: `src/ghosttap/profiles.py`
- Test: `tests/test_profiles.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `LayoutButton` dataclass: `label: str`, `bounds: tuple[int,int,int,int]`, `action: str = "tap"`, `value: str = ""`.
  - `ManualLayout` dataclass: `name: str`, `buttons: list[LayoutButton]`.
  - `DeviceProfile` dataclass: `serial: str`, `label: str = ""`, `screen: tuple[int,int] = (0,0)`, `density: int = 0`, `manual_layouts: dict[str, ManualLayout]`.
  - `ProfileStore` dataclass: `profiles: dict[str, DeviceProfile]`; `get_or_create(serial: str) -> DeviceProfile`.
  - `save_store(store: ProfileStore, path: Path) -> None`, `load_store(path: Path) -> ProfileStore` (missing file → empty store).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profiles.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ghosttap.profiles'`.

- [ ] **Step 3: Implement `profiles.py`**

Create `src/ghosttap/profiles.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ghosttap/profiles.py tests/test_profiles.py
git commit -m "feat: add device profiles and manual layout persistence" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `panel_model.py` — pure geometry and hit mapping

**Files:**
- Create: `src/ghosttap/panel_model.py`
- Test: `tests/test_panel_model.py`

**Interfaces:**
- Consumes: `Node`, `actionable`, `label`, `center` from `ghosttap.hierarchy`; `ManualLayout` from `ghosttap.profiles`.
- Produces:
  - `DrawButton` dataclass: `label: str`, `rect: tuple[int,int,int,int]` (scaled canvas rect), `tap: tuple[int,int]` (device coordinate).
  - `scale_factor(screen: tuple[int,int], canvas: tuple[int,int]) -> float`.
  - `build_buttons(nodes: list[Node], screen: tuple[int,int], canvas: tuple[int,int]) -> list[DrawButton]`.
  - `buttons_from_layout(layout: ManualLayout, screen: tuple[int,int], canvas: tuple[int,int]) -> list[DrawButton]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_panel_model.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_panel_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ghosttap.panel_model'`.

- [ ] **Step 3: Implement `panel_model.py`**

Create `src/ghosttap/panel_model.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_panel_model.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ghosttap/panel_model.py tests/test_panel_model.py
git commit -m "feat: add pure panel model for scaled draw buttons" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `panel.py` + `main.py` — the PyQt6 window and entry point

**Files:**
- Create: `src/ghosttap/panel.py`
- Create: `src/ghosttap/main.py`
- Test: `tests/test_panel_window.py`

**Interfaces:**
- Consumes: `AdbClient` (`dump_ui`, `wm_size`, `tap`, `keyevent`, `input_text`, `current_focus`) from `ghosttap.adb`; `parse`, `flatten` from `ghosttap.hierarchy`; `build_buttons`, `DrawButton` from `ghosttap.panel_model`; `Config` from `ghosttap.config`.
- Produces:
  - `PanelWindow(QWidget)` with `__init__(self, client, screen: tuple[int,int], canvas: tuple[int,int] = (450, 900))`, a `buttons: list[DrawButton]` attribute, and a `refresh() -> None` method that re-dumps and repopulates `buttons` (safe when a dump is unavailable — sets `buttons=[]` and a status message).
  - `main() -> int` entry point.

**Note on GUI testing:** all geometry/logic lives in `panel_model.py` (Task 8, fully unit-tested). This task's automated test only proves the window constructs and `refresh()` populates buttons under the offscreen Qt platform; the interactive behavior is a manual smoke test.

- [ ] **Step 1: Write the failing test**

Create `tests/test_panel_window.py`:

```python
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ghosttap.panel import PanelWindow  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sample_dump.xml"

_app = QApplication.instance() or QApplication([])


class FakeClient:
    def __init__(self, xml):
        self._xml = xml
        self.taps = []

    def dump_ui(self):
        return self._xml

    def wm_size(self):
        return (1080, 2160)

    def current_focus(self):
        return "mCurrentFocus=Window{demo}"

    def tap(self, x, y):
        self.taps.append((x, y))

    def keyevent(self, code):
        pass

    def input_text(self, s):
        pass


def test_refresh_populates_buttons():
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    win = PanelWindow(client, screen=(1080, 2160), canvas=(540, 1080))
    win.refresh()
    assert len(win.buttons) == 4
    labels = {b.label for b in win.buttons}
    assert "Sign in" in labels


def test_refresh_handles_unavailable_dump():
    from ghosttap.adb import DumpUnavailable

    class Blocked(FakeClient):
        def dump_ui(self):
            raise DumpUnavailable("locked")

    win = PanelWindow(Blocked(""), screen=(1080, 2160), canvas=(540, 1080))
    win.refresh()
    assert win.buttons == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_panel_window.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ghosttap.panel'` (or `PyQt6` skip if not yet installed — install it in Step 3).

- [ ] **Step 3: Install PyQt6 and implement `panel.py`**

Run: `pip install "PyQt6>=6.11"`

Create `src/ghosttap/panel.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_panel_window.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Implement `main.py`**

Create `src/ghosttap/main.py`:

```python
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from .adb import AdbClient
from .config import Config
from .panel import PanelWindow


def main() -> int:
    cfg = Config()
    cfg.ensure_dirs()
    client = AdbClient(cfg.adb_path)

    devices = client.devices()
    ready = [d for d in devices if d.state == "device"]
    if not ready:
        print("No authorized device. Run `adb devices` and accept the USB-debugging prompt.")
        return 1
    client.serial = ready[0].serial

    try:
        screen = client.wm_size()
    except Exception:
        screen = (1080, 2160)

    app = QApplication(sys.argv)
    window = PanelWindow(client, screen=screen)
    window.refresh()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Full test run + manual smoke test**

Run: `python -m pytest -v`
Expected: PASS (all tests across every task green).

Manual smoke test (device connected and unlocked):
```bash
python -m ghosttap.main
```
Expected: a GhostTap window opens; **Refresh** shows labeled boxes for the current screen; clicking a box taps the phone (verify on the device or in scrcpy); Back/Home/Recents and the text box work. Close the window (exit code 0).

- [ ] **Step 7: Commit**

```bash
git add src/ghosttap/panel.py src/ghosttap/main.py tests/test_panel_window.py
git commit -m "feat: add PyQt6 panel window and app entry point" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- adb-only, no root/install → `AdbClient` (Tasks 5–6), Global Constraints. ✔
- Reconstruct clickable map from dump → `hierarchy` + `panel_model` + `panel` (Tasks 3, 4, 8, 9). ✔
- Click reconstructed element → real tap → `PanelWindow.handle_click` → `client.tap` (Task 9). ✔
- Hardware keys, text input → Task 9 key row + text row. ✔
- Manual-layout fallback for keyguard/blocked dumps → `profiles.ManualLayout` + `buttons_from_layout` + `refresh()`'s `DumpUnavailable` branch + blind-PIN via Send (Tasks 7, 8, 9). ✔
- password fields never read; write via `input_text` → Task 6; secrets never logged → Global Constraints. ✔
- Snapshot/refresh model → `refresh()` re-dumps after each action (Task 9). ✔
- wm_size for aspect/scaling → Task 6 + used in `main` and `PanelWindow`. ✔
- Config with adb path + data dir → Task 2. ✔
- Testing: pure modules unit-tested against a real-shaped fixture; adb mocked; GUI smoke-tested offscreen → Tasks 3–9. ✔
- Phase 2 items (AI agent, overlay) intentionally excluded from this plan. ✔

**Placeholder scan:** No TBD/TODO; every code and test step contains complete, runnable content. ✔

**Type consistency:** `DrawButton(label, rect, tap)` used identically in Tasks 8 and 9; `AdbClient` method names (`dump_ui`, `tap`, `keyevent`, `input_text`, `current_focus`, `wm_size`) consistent across Tasks 5, 6, 9; `ManualLayout`/`LayoutButton` fields consistent across Tasks 7 and 8; `parse`/`flatten`/`actionable`/`label`/`center` signatures consistent across Tasks 3, 4, 8. ✔

**Manual-layout note:** Task 7 builds the persistence and Task 8 renders a layout; the interactive *capture* flow (measuring the PIN pad once) and wiring the manual layout into the window's UI are deferred to a small follow-up within Phase 1 — the data model, rendering, and the `DumpUnavailable` fallback path all exist, and the blind-PIN Send path already lets you unlock a black keyguard today.
