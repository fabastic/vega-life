"""A small local server for watching and setting up a life. Standard library only.

    python ui/server.py            then open http://127.0.0.1:8765
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import hashlib
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vegalife import factors as fx          # noqa: E402
from vegalife import growth                 # noqa: E402
from vegalife import proc                   # noqa: E402
from vegalife.brainmap import BrainMap      # noqa: E402
from vegalife.family import Family          # noqa: E402
from vegalife.people import Circle          # noqa: E402
from vegalife.trainer import DEFAULTS       # noqa: E402

RUNS = ROOT / "runs"
NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
SERVER_VERSION = 18                # the page compares this with its own and warns if the server is older
_cache = {"at": 0.0, "procs": {}}
TRAINER_CMD = re.compile(r"runs[\\/]+([A-Za-z0-9_-]+)[\"']?\s*$")


def parse_seed(seed) -> tuple:
    """(number, phrase). A seed can be a number or any words: the same words always make the same life."""
    t = str(seed if seed is not None else "").strip()
    if not t:
        raise ValueError("give a seed: a number or a few words")
    if t.lstrip("-").isdigit():
        return int(t), ""
    return int(hashlib.sha256(t.lower().encode("utf-8")).hexdigest()[:12], 16) % 10 ** 10, t


def preview(body: dict) -> dict:
    """Everything the seed would give him, before he is born: every factor, his family, his friends. Whatever
    you have moved is kept; the rest follows the seed."""
    seed, phrase = parse_seed(body.get("seed"))
    over = {k: float(v) for k, v in (body.get("factors") or {}).items() if k in fx.ALL}
    F = fx.sample(seed, over, [])
    circle = Circle(F, seed, body.get("friends") or [], bool(body.get("friend_seed", True)))
    fam = Family(F, seed, body.get("family") or None, round(3 * F["siblings"]))
    people = []
    for r in sorted(fam.people, key=lambda r: r.born):
        people.append({"relation": r.relation, "name": r.name, "age_at_his_birth": round(-r.born / 12, 1),
                       "closeness": round(r.closeness, 2), "joins_at_years": round(r.joined / 12, 1),
                       "dies_at_years": None if r.dies_at is None else round(r.dies_at / 12, 1),
                       "lifespan_years": round(r.lifespan / 12, 1) if r.lifespan else None})
    friends = [{"name": f.name, "joined_years": round(f.joined / 12, 1),
                "left_years": None if f.left is None else round(f.left / 12, 1), "closeness": round(f.closeness, 2),
                "kindness": round(f.kindness, 2), "risk": round(f.risk, 2), "studiousness": round(f.studiousness, 2),
                "online": f.online} for f in sorted(circle.friends, key=lambda f: f.joined)]
    return {"seed": seed, "phrase": phrase, "factors": F.to_json(), "family": people, "friends": friends}


def run_dir(name: str) -> Path:
    if not NAME.match(name or ""):
        raise ValueError("run names use letters, digits, - and _ only")
    return RUNS / name


def trainer_procs(max_age: float = 30.0) -> dict:
    """{run name: [pids]} found from process command lines. Slow (it scans every python process), so it is used only
    when killing a run that predates the exact pid files, never while listing runs. It runs with no window."""
    if time.time() - _cache["at"] < max_age:
        return _cache["procs"]
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object "
          "{ $_.CommandLine -match 'vegalife.trainer' } | ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }")
    found: dict = {}
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True,
                             text=True, timeout=30, creationflags=proc.NO_WINDOW).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    for line in out.splitlines():
        pid, _, cmd = line.partition("|")
        m = TRAINER_CMD.search(cmd.strip())
        if pid.strip().isdigit() and m:
            found.setdefault(m.group(1), []).append(int(pid))
    _cache.update(at=time.time(), procs=found)
    return found


def is_running(d: Path, status: str = "") -> bool:
    """Exact when the run wrote a pid file with a creation time (pid reuse cannot fool it). Never starts a process.
    Older runs with a plain pid file count as running while that pid exists and live.json was written in the last
    ten minutes; a run that has just been started counts as running until its pid file appears."""
    a = proc.alive(d)
    if a is not None:
        return a
    if status not in ("running", "stopping", "starting", None, ""):
        return False
    try:
        fresh = time.time() - (d / "live.json").stat().st_mtime < 600
    except OSError:
        fresh = False
    old = proc.legacy_pid(d)
    if old is not None:
        return fresh and proc.create_time(old) is not None
    try:
        return time.time() - (d / "config.json").stat().st_mtime < 90        # starting: pid not written yet
    except OSError:
        return False


_brains: dict = {}
_brain_lock = threading.Lock()


def brain(d: Path):
    """A run's brain map, loaded once and then extended with whatever new lines the trainer has written since."""
    if not (d / "brain_nodes.jsonl").exists():
        return None
    with _brain_lock:                                      # requests run on several threads
        entry = _brains.get(d.name)
        if entry is None:
            entry = _brains[d.name] = {"bm": BrainMap(None), "pos": None}
        entry["pos"] = entry["bm"].extend(d, entry["pos"])
        return entry["bm"]


def mark(d: Path, status: str) -> None:
    live = d / "live.json"
    try:
        data = json.loads(live.read_text(encoding="utf-8"))
        data["status"] = status
        tmp = live.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(live)
    except (ValueError, OSError):
        pass


def stop_run(name: str) -> str:
    """Asks the life to stop at its next safe point (seconds, even in the middle of a long step) and save."""
    d = run_dir(name)
    (d / "STOP").write_text("stop", encoding="utf-8")
    return "stopping: it finishes the current step, saves, and ends"


def kill_run(name: str) -> dict:
    """Ends a run's trainer at once. Two independent routes: a KILL file that the trainer's own control thread obeys
    within half a second, and ending the process tree directly. Only a process proven to be this run's trainer is
    ever touched (matching pid and creation time, or its command line for runs that predate pid files)."""
    d = run_dir(name)
    exact = proc.alive(d)
    if exact:
        pids = {proc.read_pidfile(d)["pid"]}
    elif exact is None:
        pids = set(trainer_procs(0).get(name, []))
    else:
        pids = set()
    if not pids:
        (d / "KILL").unlink(missing_ok=True)
        return {"ok": False, "killed": [], "message": "nothing is running for this life"}
    (d / "KILL").write_text("kill", encoding="utf-8")
    for pid in sorted(pids):
        proc.kill_tree(pid)
    deadline = time.time() + 5
    while time.time() < deadline and (proc.alive(d) if exact is not None else name in trainer_procs(0)):
        time.sleep(0.2)
    gone = not (proc.alive(d) if exact is not None else name in trainer_procs(0))
    (d / "KILL").unlink(missing_ok=True)
    if gone:
        mark(d, "killed")
    _cache["at"] = 0.0
    return {"ok": gone, "killed": sorted(pids),
            "message": "killed" if gone else "the process did not end within 5 seconds"}


# Started through a stub that exits at once, so the trainer is not this server's child: stopping or restarting the
# server (which ends its whole process tree) must never end a life. vega-9 was lost for a few minutes that way.
_STUB = ("import json,subprocess,sys\n"
         "a=json.loads(sys.argv[1]);f=open(a['log'],a['mode'],encoding='utf-8')\n"
         "try:\n"
         "    subprocess.Popen(a['args'],cwd=a['cwd'],stdout=f,stderr=subprocess.STDOUT,creationflags=a['flags']|0x01000000)\n"
         "except OSError:\n"
         "    subprocess.Popen(a['args'],cwd=a['cwd'],stdout=f,stderr=subprocess.STDOUT,creationflags=a['flags'])\n")


def spawn_detached(args: list, log: Path, append: bool, env: dict) -> None:
    """A hidden console of its own (not DETACHED_PROCESS: with no console at all, the venv launcher's child python
    opens a visible window), its own process group, out of this server's job and process tree when Windows allows."""
    flags = (proc.NO_WINDOW | 0x00000200) if os.name == "nt" else 0
    a = {"args": args, "cwd": str(ROOT), "log": str(log), "mode": "a" if append else "w", "flags": flags}
    subprocess.Popen([sys.executable, "-c", _STUB, json.dumps(a)], cwd=ROOT, env=env, creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=30)


def launch(d: Path, device: str = "", resume: bool = False) -> None:
    """Starts a life's trainer, detached from this server."""
    env = dict(os.environ)
    if device in ("cpu", "cuda"):
        env["VEGA_DEVICE"] = device
    args = [sys.executable, "-m", "vegalife.trainer", str(d)] + (["--resume"] if resume else [])
    spawn_detached(args, d / "trainer.log", resume, env)


# ---------------------------------------------------------------------------- talking to him (vegalife/chat.py)
def chat_worker_alive(d: Path) -> bool:
    try:
        w = json.loads((d / "chat.pid").read_text(encoding="utf-8"))
        return w.get("created") is not None and proc.create_time(int(w["pid"])) == w["created"]
    except (OSError, ValueError, KeyError):
        return False


def chat_reply(d: Path, rid: str):
    try:
        lines = (d / "chat_out.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines[-200:]):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("id") == rid:
            return r
    return None


def chat_send(d: Path, message: str, history: list) -> dict:
    """Leaves the message for him. A running life answers it between learning steps; otherwise a small worker
    wakes his last checkpoint to answer. Waits up to 40 s for the reply, then the page polls."""
    message = message.strip()
    if not message:
        raise ValueError("say something first")
    if len(message) > 300:
        raise ValueError("keep it under 300 characters: his whole context is 512 bytes")
    if not (d / "resume.pt").exists() and not (d / "mind.pt").exists() and not is_running(d):
        raise ValueError(f"{d.name} has no saved mind to talk to yet")
    rid = uuid.uuid4().hex[:12]
    hist = [{"who": h.get("who"), "text": str(h.get("text", ""))[:300]} for h in history[-8:] if isinstance(h, dict)]
    with open(d / "chat_in.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": rid, "t": time.time(), "message": message, "history": hist}) + "\n")
    live = is_running(d)
    if not live and not chat_worker_alive(d):
        spawn_detached([sys.executable, "-m", "vegalife.chat", str(d)], d / "chat.log", True, dict(os.environ))
    deadline = time.time() + 40
    while time.time() < deadline:
        r = chat_reply(d, rid)
        if r:
            return r
        time.sleep(0.25)
    return {"id": rid, "pending": True,
            "message": "he is still thinking" + ("" if live else " (waking his saved mind can take a minute)")}


def resume_info(d: Path) -> dict:
    """Whether a life can be carried on from its checkpoint, and from what age."""
    ck = d / "resume.pt"
    if not ck.exists():
        return {"resumable": False}
    return {"resumable": True, "checkpoint_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(ck.stat().st_mtime))}


def run_info(p: Path) -> dict:
    info = {"name": p.name, "running": False, "status": "no data", "age_years": None, "params": None,
            "profile": None, "optimizer": None}
    try:
        L = json.loads((p / "live.json").read_text(encoding="utf-8"))
        info.update(status=L.get("status"), age_years=L.get("age_years"), params=L.get("model", {}).get("params"),
                    profile=L.get("profile"), optimizer=L.get("optimizer"))
    except (ValueError, OSError):
        pass
    info["running"] = is_running(p, info["status"] or "")
    if info["status"] == "starting":                     # just launched (or resumed): its pid file may not exist yet
        try:
            info["running"] = info["running"] or time.time() - (p / "live.json").stat().st_mtime < 90
        except OSError:
            pass
    if info["status"] in ("running", "stopping") and not info["running"]:
        info["status"] = "not running (stopped without finishing)"
    info.update(resume_info(p))
    info["resumable"] = info["resumable"] and not info["running"] and not str(info["status"]).startswith("finished")
    return info


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, code: int, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self.send(200, (ROOT / "ui" / "index.html").read_bytes(), "text/html; charset=utf-8")
            if u.path == "/brain":
                return self.send(200, (ROOT / "ui" / "brain.html").read_bytes(), "text/html; charset=utf-8")
            if u.path == "/fx.js":
                return self.send(200, (ROOT / "ui" / "fx.js").read_bytes(), "text/javascript; charset=utf-8")
            if u.path == "/theme.css":
                return self.send(200, (ROOT / "ui" / "theme.css").read_bytes(), "text/css; charset=utf-8")
            if u.path == "/api/catalogue":
                return self.send(200, {"factors": fx.catalogue(), "stages": fx.STAGE_LABEL, "defaults": DEFAULTS,
                                       "profiles": growth.PROFILES, "notes": growth.NOTES,
                                       "schedule": growth.describe(growth.PROFILES["full"])})
            if u.path == "/api/runs":
                RUNS.mkdir(exist_ok=True)
                runs = sorted((p for p in RUNS.iterdir() if (p / "config.json").exists()),
                              key=lambda p: p.stat().st_mtime, reverse=True)
                return self.send(200, [run_info(p) for p in runs])
            if u.path == "/api/chat":
                r = chat_reply(run_dir(q.get("run", "")), q.get("id", ""))
                return self.send(200, r or {"id": q.get("id"), "pending": True})
            if u.path == "/api/chat/history":
                d = run_dir(q.get("run", ""))
                out = {}
                try:
                    for line in (d / "chat_out.jsonl").read_text(encoding="utf-8").splitlines()[-200:]:
                        r = json.loads(line)
                        out[r.get("id")] = r
                    turns = []
                    for line in (d / "chat_in.jsonl").read_text(encoding="utf-8").splitlines()[-40:]:
                        m = json.loads(line)
                        turns.append({"id": m["id"], "t": m["t"], "message": m["message"], "reply": out.get(m["id"])})
                except (OSError, ValueError):
                    turns = []
                return self.send(200, {"turns": turns})
            if u.path == "/api/version":
                return self.send(200, {"version": SERVER_VERSION})
            if u.path.startswith("/api/brain/"):
                bm = brain(run_dir(q.get("run", "")))
                if bm is None:
                    return self.send(200, {"none": True, "message": "this life has no brain map (it predates it)"})
                num = lambda k, d: int(q[k]) if q.get(k, "").lstrip("-").isdigit() else d
                if u.path == "/api/brain/top":
                    kinds = set(q["kinds"].split(",")) if q.get("kinds") else None
                    a, b = num("from", -1), num("to", -1)
                    out = bm.top(a * 12 if a >= 0 else None, b * 12 + 11 if b >= 0 else None, min(num("n", 300), 600),
                                 kinds, q.get("q", ""))
                    return self.send(200, out | {"stats": bm.stats()})
                if u.path == "/api/brain/overview":
                    a, b = num("from", -1), num("to", -1)
                    out = bm.overview(a * 12 if a >= 0 else None, b * 12 + 11 if b >= 0 else None)
                    return self.send(200, out | {"stats": bm.stats()})
                if u.path == "/api/brain/node":
                    return self.send(200, bm.neighbourhood(q.get("id", "")))
                if u.path == "/api/brain/trace":
                    return self.send(200, bm.trace(q.get("id", ""), q.get("dir", "up"), min(num("depth", 4), 8),
                                                   min(num("limit", 300), 600)))
            if u.path == "/api/live":
                f = run_dir(q.get("run", "")) / "live.json"
                if not f.exists():
                    return self.send(200, {"status": "starting"})
                raw = f.read_bytes()
                try:
                    L = json.loads(raw)
                except ValueError:
                    return self.send(200, {"status": "starting"})      # caught between writes; the page polls again
                if L.get("status") in ("running", "stopping") and not is_running(f.parent, L["status"]):
                    L["status"] = "not running (stopped without finishing)"   # e.g. the computer slept or restarted
                    return self.send(200, L)
                return self.send(200, raw)
        except (ValueError, OSError) as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if u.path == "/api/preview":                    # before he exists: no run yet
                return self.send(200, preview(body))
            d = run_dir(body.get("run", ""))
            if u.path == "/api/start":
                if d.exists():
                    raise ValueError(f"run {d.name} already exists")
                cfg = {k: body[k] for k in ("seed", "profile", "max_age_years", "factors", "timeline", "sim", "corpus_dir",
                                            "friends", "friend_seed", "family") if k in body}
                cfg["seed"], cfg["seed_phrase"] = parse_seed(body.get("seed", 1))
                for rel in cfg.get("family", []):
                    if not isinstance(rel, dict) or not str(rel.get("relation", "")).strip():
                        raise ValueError("every family member needs a relation")
                for fr in cfg.get("friends", []):
                    if not isinstance(fr, dict) or not str(fr.get("name", "")).strip():
                        raise ValueError("every listed friend needs a name")
                for k in cfg.get("factors", {}):
                    if k not in fx.ALL:
                        raise ValueError(f"unknown factor {k}")
                if cfg.get("profile", "laptop") not in growth.PROFILES:
                    raise ValueError("unknown profile")
                d.mkdir(parents=True)
                (d / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                launch(d, body.get("device", ""))
                return self.send(200, {"ok": True, "run": d.name})
            if u.path == "/api/resume":
                if not d.exists():
                    raise ValueError(f"no run called {d.name}")
                info = run_info(d)
                if info["running"]:
                    raise ValueError(f"{d.name} is already running")
                if not (d / "resume.pt").exists():
                    raise ValueError(f"{d.name} has no checkpoint: it was started before resume existed")
                if str(info["status"]).startswith("finished"):
                    raise ValueError(f"{d.name} has finished its life")
                mark(d, "starting")
                launch(d, body.get("device", ""), resume=True)
                return self.send(200, {"ok": True, "run": d.name, "message": "resuming from the last checkpoint"})
            if u.path == "/api/chat":
                if not d.exists():
                    raise ValueError(f"no run called {d.name}")
                return self.send(200, chat_send(d, str(body.get("message", "")), list(body.get("history", []))))
            if u.path == "/api/intervene":
                if isinstance(body.get("friend"), dict):
                    fr = body["friend"]
                    if not str(fr.get("name", "")).strip():
                        raise ValueError("a friend needs a name")
                    with open(d / "interventions.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps({"friend": fr}) + "\n")
                    return self.send(200, {"ok": True})
                if body.get("key") not in fx.ALL:
                    raise ValueError("unknown factor")
                v = float(body["value"])
                with open(d / "interventions.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"key": body["key"], "value": max(0.0, min(1.0, v))}) + "\n")
                return self.send(200, {"ok": True})
            if u.path == "/api/kill":
                if not d.exists():
                    raise ValueError(f"no run called {d.name}")
                return self.send(200, kill_run(d.name))
            if u.path == "/api/stop":
                if not d.exists():
                    raise ValueError(f"no run called {d.name}")
                return self.send(200, {"ok": True, "message": stop_run(d.name)})
        except (ValueError, KeyError, OSError) as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Vega life UI on http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
