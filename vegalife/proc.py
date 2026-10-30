"""Telling whether a run's trainer is really alive, and ending it, without scanning every process.

A trainer writes `pid` as {"pid": N, "created": T}, where T is the process's creation time. Windows reuses process
ids, so a pid alone proves nothing: a process only counts as the trainer if both match. That also means a stale
`pid` file can never lead to killing an unrelated program.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

# Start console programs (taskkill, the trainer, powershell) without opening a window on Windows.
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def create_time(pid: int) -> Optional[int]:
    """Creation time of a live process (Windows FILETIME), or None if it is not running."""
    if os.name != "nt":
        try:
            return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])
        except (OSError, ValueError, IndexError):
            return None
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:     # 259 = still running
            return None
        c, e, kt, u = (wintypes.FILETIME() for _ in range(4))
        if not k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(u)):
            return None
        return (c.dwHighDateTime << 32) | c.dwLowDateTime
    finally:
        k.CloseHandle(h)


def write_pidfile(run_dir: Path) -> None:
    pid = os.getpid()
    (run_dir / "pid").write_text(json.dumps({"pid": pid, "created": create_time(pid)}), encoding="utf-8")


def read_pidfile(run_dir: Path) -> Optional[dict]:
    try:
        d = json.loads((run_dir / "pid").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("pid"), int) else None
    except (OSError, ValueError):
        return None                                       # missing, or the old plain-number format


def legacy_pid(run_dir: Path) -> Optional[int]:
    """The pid from an old plain-number pid file, if that is what the run has."""
    try:
        t = (run_dir / "pid").read_text(encoding="utf-8").strip()
        return int(t) if t.isdigit() else None
    except OSError:
        return None


def alive(run_dir: Path) -> Optional[bool]:
    """True/False if the pid file can say; None if it cannot (no file, or an old-format one)."""
    d = read_pidfile(run_dir)
    if d is None or d.get("created") is None:
        return None
    return create_time(d["pid"]) == d["created"]


def keep_awake() -> bool:
    """Asks Windows not to sleep while this process runs (cleared automatically when it exits). Sleep with a life on
    the GPU resets the driver under it. This stops idle sleep only: closing the lid or restarting still ends the run."""
    if os.name != "nt":
        return False
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    return bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))


def kill_tree(pid: int) -> bool:
    """Ends a process and everything it started. Returns whether it worked."""
    if os.name == "nt":
        return subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                              creationflags=NO_WINDOW).returncode == 0
    try:
        os.kill(pid, 9)
        return True
    except OSError:
        return False
