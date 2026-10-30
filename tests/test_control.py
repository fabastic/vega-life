"""Stop and Kill must work in seconds, must never touch the wrong process, and must not need the GPU to be tested.

These start real trainers on the CPU (VEGA_DEVICE=cpu), so they are safe to run while a life is training on the GPU.
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from vegalife import proc

ROOT = Path(__file__).resolve().parent.parent


def start(tmp_path, name):
    d = tmp_path / name
    d.mkdir()
    (d / "config.json").write_text(json.dumps({"seed": 3, "profile": "tiny_lean", "max_age_years": 90}), encoding="utf-8")
    env = dict(os.environ, VEGA_DEVICE="cpu")
    p = subprocess.Popen([sys.executable, "-m", "vegalife.trainer", str(d)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return d, p


def wait_for(cond, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.2)
    return False


def status(d):
    try:
        return json.loads((d / "live.json").read_text(encoding="utf-8"))["status"]
    except (OSError, ValueError, KeyError):
        return None


def server():
    spec = importlib.util.spec_from_file_location("ui_server", ROOT / "ui" / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def procs():
    started = []
    yield started
    for p in started:
        if p.poll() is None:
            p.kill()


def test_pid_file_is_exact(tmp_path):
    (tmp_path / "a").mkdir()
    proc.write_pidfile(tmp_path / "a")
    assert proc.alive(tmp_path / "a") is True
    d = json.loads((tmp_path / "a" / "pid").read_text())
    d["created"] += 1                                    # same pid, different process: pid reuse
    (tmp_path / "a" / "pid").write_text(json.dumps(d))
    assert proc.alive(tmp_path / "a") is False
    (tmp_path / "a" / "pid").write_text("12345")         # old plain-number format: cannot say
    assert proc.alive(tmp_path / "a") is None


def test_stop_ends_the_life_within_seconds_and_saves(tmp_path, procs):
    d, p = start(tmp_path, "s")
    procs.append(p)
    assert wait_for(lambda: status(d) == "running", 90), "trainer did not start"
    time.sleep(1.0)
    (d / "STOP").write_text("stop")
    assert wait_for(lambda: p.poll() is not None, 30), "did not stop"
    assert status(d) == "stopped" and (d / "mind.pt").exists()


def test_kill_ends_the_process_at_once(tmp_path, procs, monkeypatch):
    srv = server()
    monkeypatch.setattr(srv, "RUNS", tmp_path)
    d, p = start(tmp_path, "k")
    procs.append(p)
    assert wait_for(lambda: status(d) == "running" and proc.alive(d), 90)
    assert srv.run_info(d)["running"] is True
    t0 = time.time()
    r = srv.kill_run("k")
    assert r["ok"] and time.time() - t0 < 6, r
    assert not proc.alive(d)
    assert wait_for(lambda: p.poll() is not None, 5)         # the venv launcher above the trainer exits right after
    assert status(d) == "killed" and not (d / "KILL").exists()
    assert srv.run_info(d)["running"] is False


def test_kill_leaves_unrelated_processes_alone(tmp_path, procs, monkeypatch):
    srv = server()
    monkeypatch.setattr(srv, "RUNS", tmp_path)
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    procs.append(other)
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "pid").write_text(json.dumps({"pid": other.pid, "created": 1}))   # stale: wrong creation time
    monkeypatch.setattr(srv, "trainer_procs", lambda max_age=30.0: {})
    r = srv.kill_run("old")
    assert r["ok"] is False and other.poll() is None
