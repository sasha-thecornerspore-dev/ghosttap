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
