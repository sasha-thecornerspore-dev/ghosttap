# GhostTap User Guide

GhostTap lets you operate an Android phone from your PC over `adb`, even when the
screen is black (a `FLAG_SECURE` prompt in scrcpy) or physically broken. This
guide covers day‑to‑day use.

## 1. Prerequisites

- **adb** available — bundled with scrcpy or Android platform‑tools. GhostTap
  auto‑detects `adb` on your `PATH`; otherwise set `GHOSTTAP_ADB` to the full path
  of the binary (e.g. `C:/Users/you/scrcpy/adb.exe`).
- **USB debugging** enabled on the phone (Settings → Developer options), the phone
  plugged in, and the on‑device authorization prompt accepted. Confirm with:
  ```bash
  adb devices        # your device should appear as "device", not "unauthorized"
  ```

## 2. Launching

- **From a build:** run the downloaded `GhostTap` app.
- **From source:** `ghosttap` (after `pip install -e .`) or
  `PYTHONPATH=src python -m ghosttap.main`.

GhostTap picks the first authorized device and draws its current screen. If no
device is authorized it tells you and exits — fix `adb devices` and relaunch.

## 3. The window

- **Status line** — element count and the currently focused app/window.
- **Update banner** — appears when a newer release exists.
- **Refresh / Check for updates**.
- **Reconstructed screen** — each actionable element is a labeled box. Clicking a
  box taps the real phone at that element's center, then auto‑refreshes. Clicking
  where boxes overlap taps the *smallest* (most specific) one.
- **Hardware keys** — Back, Home, Recents, Power, Vol+, Vol‑.
- **Typing into: …** — the field your text will target (or a warning to tap one).
- **Text box + Type + Enter** — the safe typing flow (below).

## 4. Safe typing (no blind input)

Typing is deliberately two steps so nothing is submitted sight‑unseen:

1. Make sure a field is focused — the **Typing into:** line should name it. If it
   says *no field focused*, click the field on the reconstructed screen first,
   then **Refresh**.
2. Type into the box and press **Type**. A confirm appears:
   - normal field → shows the actual text;
   - password/PIN field → shows masked dots and the digit count (e.g.
     `****  (4 digits)`), never the value.
   Approve it. The text is injected but **Enter is not pressed.**
3. Verify on the phone, then press **Enter** to submit.

This avoids submitting a wrong or truncated PIN — important because failed device
PIN attempts can trigger lockout escalation.

## 5. Unlocking a black lock screen

1. On the keyguard (black in scrcpy), click **Refresh**.
2. If a password field is exposed, follow the safe‑typing steps to enter the PIN.
3. If the screen exposes **no map** (some keyguards hide their PIN pad from
   accessibility), GhostTap says so. For now, use the physical screen if it works,
   or wait for the manual‑layout capture feature on the roadmap.

## 6. Troubleshooting

| Symptom | Fix |
|--------|-----|
| "No authorized device" on launch | `adb devices` must show `device`; accept the USB prompt, replug, relaunch. |
| "This screen exposed no map" | The current screen hides its controls from accessibility (common on hardened keyguards). Not all screens are reconstructable. |
| Everything looks squished | A leftover `wm size` override; reset with `adb shell wm size reset`. |
| adb not found | Set `GHOSTTAP_ADB` to the full path of `adb`. |
| Wrong element tapped | Click nearer the center of the intended control; overlapping boxes resolve to the smallest one. |

## 7. Privacy & safety

- GhostTap never reads the contents of secure/password fields (the OS keeps them
  hidden); it only *writes* into them when you type.
- A typed PIN/password is never printed, logged, shown in an error message, or
  sent anywhere off your machine.
- GhostTap only controls a device you have already authorized for USB debugging.
