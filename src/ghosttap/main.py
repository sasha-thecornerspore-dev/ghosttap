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
