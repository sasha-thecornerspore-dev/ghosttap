# GhostTap

**Operate an Android phone from your PC when the screen is black or broken.**

When you mirror a phone with [scrcpy](https://github.com/Genymobile/scrcpy), any
screen that sets `FLAG_SECURE` — the lock‑screen keyguard, banking apps, PIN and
password prompts — comes through as **solid black**, because the OS excludes those
surfaces from screen capture. The same blackout happens, permanently, when a
phone's display is physically **cracked or dead** but the device still runs and
answers over USB.

GhostTap works around that. `FLAG_SECURE` blocks the *pixels*, not the
*accessibility tree*, so `adb shell uiautomator dump` still reports every button's
exact position and label even while the mirror is black. GhostTap reads that dump,
**reconstructs the screen as labeled, clickable buttons**, and taps the real phone
when you click one — no root, no app installed on the phone.

> Built for operating **your own** device that you can already reach over USB
> debugging. It does not bypass anyone else's security and it cannot recover the
> pixels of a secure surface — it reconstructs the *layout* from the phone's own
> accessibility data.

---

## Features

- **Reconstructed screen** — a clickable map of the current screen, rebuilt from
  the accessibility dump; works when scrcpy shows only black.
- **Deepest‑element tapping** — clicking a control taps the most specific element
  under your cursor (lists and nested views behave correctly).
- **Hardware keys** — Back, Home, Recents, Power, Volume up/down.
- **Safe typing (no blind input)** — a dedicated text box with a **Type** button
  (injects text, does *not* submit) and a separate **Enter** button, plus a
  confirm preview. For password/PIN fields the preview is masked (dots + digit
  count) so you can verify the length without ever displaying the value.
- **Target awareness** — shows which field your text will land in, or warns when
  nothing typable is focused.
- **Self‑update** — checks GitHub Releases on launch and offers a newer build.
- **Secret‑safe** — a typed PIN is never logged, never shown in an error, and
  never leaves your machine.

## Requirements

- **adb** (bundled with [scrcpy](https://github.com/Genymobile/scrcpy), or the
  Android platform‑tools). GhostTap finds `adb` on your `PATH`; otherwise set
  `GHOSTTAP_ADB` to its full path.
- A device with **USB debugging** enabled and authorized (`adb devices` shows it
  as `device`).
- No root required.

## Install

### Download a build (recommended)
Grab the latest **Windows `.exe`** or **macOS `.app`** from the
[Releases page](https://github.com/sasha-thecornerspore-dev/ghosttap/releases).

Because the builds are not code‑signed yet, your OS will warn on first run:
- **Windows:** SmartScreen → *More info* → *Run anyway*.
- **macOS:** right‑click the app → *Open* → *Open* (Gatekeeper, "unidentified
  developer").

### Run from source
```bash
git clone https://github.com/sasha-thecornerspore-dev/ghosttap
cd ghosttap
pip install -e .
ghosttap          # or:  PYTHONPATH=src python -m ghosttap.main
```

## Usage

1. Connect the phone over USB, enable USB debugging, and accept the prompt.
2. Launch GhostTap. It picks the first authorized device and draws the current
   screen as buttons.
3. Click a button to tap the phone; the view refreshes automatically. Use
   **Refresh** after you navigate on the phone.

### Walkthrough: unlock a black lock screen
1. With the keyguard showing (black in scrcpy), click **Refresh**. GhostTap shows
   whatever the prompt exposes — often the password field.
2. The **Typing into:** line shows the target field.
3. Type your PIN in the box → **Type**. The confirm shows masked dots + the digit
   count; approve it. This injects the PIN but does **not** submit.
4. Glance at the phone to confirm, then click **Enter** to submit.

### Walkthrough: operate a cracked screen
The reconstructed panel is a full remote: click controls, use the hardware keys,
and type into fields exactly as above, entirely from the PC.

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for more, and
[`docs/superpowers/specs`](docs/superpowers/specs) for the design.

## How it works

```
adb (uiautomator dump) ──▶ hierarchy (parse XML → Node tree, pick actionable)
                              │
                              ▼
                     panel_model (scale to canvas, map click → device tap)
                              │
                              ▼
                     panel (PyQt6 window: draw, route clicks, safe typing)
```

Each layer is small and independently tested. `adb.py` shells out with argument
lists (never shell strings); the GUI holds no geometry logic, so the tricky parts
are covered by unit tests.

## Configuration

| Variable | Meaning |
|----------|---------|
| `GHOSTTAP_ADB` | Full path to the `adb` binary (overrides auto‑detection). |
| `GHOSTTAP_HOME` | Data directory for device profiles (default `~/.ghosttap`). |

## Development

```bash
pip install -e .[dev]
QT_QPA_PLATFORM=offscreen python -m pytest -q   # run the test suite
python packaging/build.py                        # build a local binary
```

## Roadmap

- Manual layout **capture** UI for keyguards that expose no map (measure the PIN
  pad once, reuse it).
- AI agent: drive the phone from a natural‑language goal over the accessibility
  tree.
- Overlay mode: draw the reconstructed map directly on top of the scrcpy window.
- Device picker, on‑canvas swipe gestures, code‑signed builds.

## License

[MIT](LICENSE) © 2026 Alexander Mitriache
