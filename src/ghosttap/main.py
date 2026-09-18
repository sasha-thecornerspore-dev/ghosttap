from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from . import __version__
from .adb import AdbClient
from .config import Config, resolve_adb
from .panel import PanelWindow
from .update import check_for_update


def main() -> int:
    cfg = Config()
    cfg.ensure_dirs()
    client = AdbClient(resolve_adb(cfg.adb_path))

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

    # One-off, best-effort update check (swallows offline/errors, short timeout).
    update = check_for_update(__version__)

    app = QApplication(sys.argv)
    window = PanelWindow(client, screen=screen, update=update)
    window.refresh()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
