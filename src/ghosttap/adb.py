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
        # Only spaces are escaped here: `adb shell input text` runs through an
        # on-device shell that reinterprets shell metacharacters ($ ; & | < > " '
        # etc.), so symbol-containing passwords may be mistyped or truncated.
        # Digits/PINs are unaffected. Robust per-character entry (e.g. via
        # `input keyevent` sequences or an IME-based sender) is deferred to backlog.
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
