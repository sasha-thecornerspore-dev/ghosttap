# GhostTap — Design Spec

**Date:** 2026-09-15
**Status:** Approved design, pre-implementation
**Working name:** GhostTap (rename-friendly)

## 1. Problem

When mirroring/controlling an Android phone from a PC via `scrcpy`, any window
that sets `FLAG_SECURE` (the lock-screen keyguard, banking apps, password
prompts) is rendered as **solid black** in the mirror, because `FLAG_SECURE`
excludes the surface from the non-secure virtual display scrcpy captures. The
operator can no longer see where to tap. The same blindness happens when a
phone's **physical screen is broken** but the device is otherwise alive and
reachable over adb.

Key insight that makes a solution possible: `FLAG_SECURE` blocks **pixel
capture**, not (in most cases) the **accessibility tree**. `adb shell
uiautomator dump` frequently still returns every actionable element's exact
`bounds`, `text`, `resource-id`, and `content-desc` even while the screen is
black. Verified on the target device (`14SAXS00NVK`): a dump returned 37
clickable nodes with full geometry.

## 2. Goals

- Operate an Android phone entirely from the PC using adb, with **no root** and
  **no on-device app install**, even when the mirror/screen shows nothing.
- Reconstruct a **clickable map** of the current screen from the accessibility
  dump; clicking a reconstructed element taps the real device.
- Provide hardware keys (Back/Home/Recents/Power), text input, and swipe.
- Handle the two screens that resist dumping — the **keyguard PIN pad** and
  password fields — via a per-device **manual layout** fallback measured once
  and reused.
- (Later phases) An **AI agent** that takes a natural-language goal, reads the
  accessibility tree, and drives adb to accomplish it; and an **overlay** mode
  that draws the map directly on top of the scrcpy window.

## 3. Non-Goals

- Recovering the actual pixels of a `FLAG_SECURE` surface (impossible without
  root/DRM bypass, and explicitly not attempted).
- Defeating another party's device security. This is a tool for operating
  **your own** reachable device; it requires USB-debugging authorization the
  device owner grants.
- AI vision "reconstruct the UI from stock photos found online." Rejected during
  brainstorming: when the dump works it is more accurate than any photo; when it
  fails (keyguard) photos cannot yield *this* device's exact coordinates. The
  manual-layout fallback replaces it.
- Live-video-quality real-time rendering. GhostTap is snapshot/refresh-driven by
  design — that is precisely why it works when video is black.

## 4. Users & primary use cases

Single technical user on Windows, adb + scrcpy already in use.

1. **Black-screen unlock:** phone locked, keyguard black in scrcpy → GhostTap
   shows the PIN pad (from saved manual layout) → user taps PIN → unlocked.
2. **Broken-screen operation:** cracked display, device alive → operate apps
   from the reconstructed panel.
3. **Secure-app navigation:** a banking app blanks the mirror → dump still
   yields buttons → operate normally.
4. **(Phase 2) "Do this for me":** "unlock and open my messages" → agent loops
   dump→act until done.

## 5. Architecture

All-Python, PyQt6 GUI. Layered so each unit has one purpose, a clear interface,
and is independently testable.

```
main.py            entry point: load config, pick device, launch panel
adb.py             AdbClient: thin wrapper over the adb binary
hierarchy.py       parse dump XML -> Node tree; filter/label/center
profiles.py        per-serial DeviceProfile + ManualLayout persistence (JSON)
panel.py           PhaseReconstructionPanel (PyQt6): draw nodes, route clicks
config.py          paths, adb location, API key location, settings
--- phase 2 ---
agent.py           NL goal -> LLM action loop over the accessibility tree
overlay.py         translucent click-through window aligned over scrcpy
```

### 5.1 `adb.py` — `AdbClient`
Wraps the bundled `adb.exe`. Constructed with the adb path and an optional
device serial (multi-device safe via `-s`). Uses `subprocess` with **argument
lists** (never shell strings), which sidesteps the Git-Bash `/sdcard` path
mangling seen during probing. Methods:

- `devices() -> list[Device]`
- `dump_ui() -> str` — runs `uiautomator dump` then reads the file back
  (`exec-out cat`), returns raw XML. Raises `DumpUnavailable` if empty/failed.
- `tap(x, y)`, `swipe(x1,y1,x2,y2,ms)`, `input_text(s)`, `keyevent(code)`
- `wm_size() -> (w,h)`, `wm_density() -> int`
- `current_focus() -> str` (parsed from `dumpsys window`)
- `wake()` / `sleep()` helpers (keyevent 224/223)

Knows nothing about parsing or Qt. Unit-tested by mocking `subprocess.run`.

### 5.2 `hierarchy.py`
- `Node` dataclass: `bounds:(l,t,r,b)`, `text`, `resource_id`, `content_desc`,
  `cls`, `package`, `clickable`, `long_clickable`, `scrollable`, `editable`,
  `password`, `focused`, `children`.
- `parse(xml:str) -> Node` (root).
- `flatten(root) -> list[Node]`.
- `actionable(nodes) -> list[Node]` — clickable OR long-clickable OR editable
  OR scrollable, with a non-degenerate rect.
- `label(node) -> str` — first non-empty of text → content_desc →
  resource-id (short form) → class basename.
- `center(node) -> (x,y)`.

Pure functions over data; no adb, no Qt. Tested against captured sample XML
(including a real dump saved as a fixture).

### 5.3 `profiles.py`
- `DeviceProfile`: `serial`, `label`, `screen:(w,h)`, `density`, and
  `manual_layouts: dict[str, ManualLayout]`.
- `ManualLayout`: a named set of labeled rectangles + the action each triggers
  (`tap` at center, or `input_text`/`keyevent`), for screens the dump can't see
  (e.g. `"keyguard_pin"`). Includes a `capture` helper flow: user marks buttons
  once on a reference screenshot / measured grid; stored to JSON.
- Persistence: `~/.ghosttap/profiles.json` (path via `config.py`).

### 5.4 `panel.py` — the standalone window (Phase 1 deliverable)
- Header: device picker, **Refresh** (re-dump), current-focus label, connection
  status.
- Center: a scaled phone rectangle (aspect from `wm_size`). Each actionable
  `Node` drawn as a labeled, positioned button. Click → `adb.tap(center)` →
  auto-refresh after a short delay.
- Right/side strip: hardware keys (Back=4, Home=3, Recents=187, Power=26,
  Vol±), a text box → `input_text`, and an "Enter" (66).
- Empty/blocked dump path: banner "This screen didn't expose a map" → offer to
  **load a saved manual layout** for this device, or **create one**, or send a
  **blind PIN** (`input_text` + Enter).
- Renders from the model only; no adb/XML logic lives here.

### 5.5 Data flow (Phase 1)
```
adb.dump_ui() -> hierarchy.parse() -> flatten -> actionable
   -> panel draws buttons
   -> user click -> adb.tap(center) -> (delay) -> dump_ui() again
```
A snapshot loop. No dependency on the video stream.

## 6. Phasing

**Phase 1 — v1 core (no AI):** `config`, `adb`, `hierarchy`, `profiles`,
`panel`, `main`. Fully solves black/broken-screen operation including the
keyguard via manual layout + blind PIN. This is the milestone we build and
verify first.

**Phase 2 — AI + overlay:** `agent.py` (Anthropic SDK; action loop over the
tree) and `overlay.py` (frameless translucent always-on-top click-through
window, 2-point calibration to map phone→screen coordinates, drawn over
scrcpy).

**Phase 3 — polish:** PyInstaller single-`.exe`, saved macros/sequences,
multi-device niceties.

## 7. Hard cases (addressed in Phase 1)

- **Keyguard dumps empty:** expected on many devices. Handled by
  `ManualLayout("keyguard_pin")` — measured once, reused — plus a blind
  `input_text(pin)` + keyevent 66 shortcut.
- **`password="true"` fields:** contents intentionally unreadable; write via
  `input_text`. GhostTap never attempts to read secure field contents.

## 8. AI design & safety (Phase 2, decided now)

- The model receives only a **compact JSON of the accessibility tree** (index,
  label, center, action flags) plus the user's goal. Never pixels, never secure
  field contents.
- The model returns a single structured action per step
  (`tap` node / `input_text` / `keyevent` / `swipe` / `done`); the app executes
  it via `AdbClient`, then re-dumps. Bounded step count with user-visible log.
- **PIN/secret handling:** the model is never given the PIN. When a step needs
  it, the app injects a locally-stored secret (user's choice to store) or
  prompts the user — the secret never enters the model context or an API
  request. This keeps "AI unlocks my phone" from leaking credentials off-device.

## 9. Tech choices

- Python 3.14 (installed), PyQt6, `anthropic` SDK (Phase 2), stdlib
  `xml.etree`/`subprocess`/`json`.
- Bundled adb at `C:/Users/sasha/Programs/scrcpy-win64-v3.3.4/adb.exe`
  (configurable).
- Subprocess uses argument lists → no shell path mangling.

## 10. Testing strategy

- `hierarchy.py`: unit tests against saved real-dump fixtures (parse, filter,
  label, center) — pure, high coverage.
- `adb.py`: unit tests mocking `subprocess`; one opt-in integration test against
  a live device behind an env flag.
- `profiles.py`: round-trip JSON persistence tests.
- `panel.py`: logic (model→button mapping, click→coordinate) factored out of Qt
  widgets so it is testable without a display; a thin manual smoke test for the
  GUI itself.

## 11. Risks

- Some OEM keyguards expose nothing to accessibility and reject coordinate taps
  while locked → mitigated by manual layout + blind input; if a device blocks
  even that, documented as a device limitation.
- `uiautomator dump` can be slow (~0.5–2s) → async dump + spinner; never block
  the UI thread.
- Coordinate drift if device rotates between dump and tap → include rotation in
  each dump and re-map.

## 12. Resolved decisions

- Standalone reconstruction panel first; overlay is Phase 2. ✔
- Snapshot/refresh model, not live video. ✔
- All-Python / PyQt6, single stack across both phases. ✔
- AI reads the tree and drives adb; no photo-based reconstruction. ✔
- PIN never sent to the model. ✔
