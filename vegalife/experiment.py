"""Fork a life and run controlled experiments on it.

At any saved month a life is a complete, bit-identical state: the whole Python world (resume.pt) and the network's
weights. This forks it into arms that start from exactly the same person and the same randomness, changes one thing
in each (an intervention or an ablation), lives each arm forward the same number of months, and compares them.

  python -m vegalife.experiment --from runs/vega-9 --name ex1 --months 24 \\
      --arm control --arm poverty:state.wealth=0.02,state.income=0.05 --arm no_conscience:ablate=conscience \\
      --arm no_mother:remove=mother --arm lonely:community_ties=0.05

Arm syntax: name:change,change,...  where a change is one of
  key=value          a factor (see factors.py), set live from the fork month
  state.key=value    part of his state set directly (wealth, anxiety, ...)
  remove=relation    someone taken out of his life (mother, father, partner, a name)
  ablate=part        a part of him switched off: conscience, memory, replay
Each arm is its own run folder (runs/<name>-<arm>) the UI can open. Arms run one after another, because the GPU fits
one life at a time; pass --device cpu to leave the GPU alone. The report (runs/<name>-report.md and .json) compares
wellbeing, mood, personality, his self-model and thoughts, how well he answers about himself, the self-knowledge
probe, the brain map, and what he says.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics as st
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import factors as fx
from . import proc

COPY = ("resume.pt", "events.jsonl", "timeline.jsonl", "brain_nodes.jsonl", "brain_edges.jsonl", "memory.json", "mind.pt")


def parse_arm(spec: str) -> dict:
    name, _, rest = spec.partition(":")
    arm = {"name": name.strip(), "factors": {}, "state": {}, "remove": [], "ablate": []}
    for ch in filter(None, (c.strip() for c in rest.split(","))):
        k, _, v = ch.partition("=")
        k = k.strip()
        if k == "remove":
            arm["remove"].append(v.strip())
        elif k == "ablate":
            arm["ablate"].append(v.strip())
        elif k.startswith("state."):
            arm["state"][k[6:]] = float(v)
        elif k in fx.ALL:
            arm["factors"][k] = float(v)
        else:
            raise SystemExit(f"unknown change {ch!r} in arm {name!r}")
    return arm


def snapshot(src: Path, name: str) -> Path:
    """One frozen copy of the source's saved month, so every arm starts from exactly the same state even if the
    source life is still running and saves again while the arms run."""
    if not (src / "resume.pt").exists():
        raise SystemExit(f"{src} has no resume.pt to fork from (stop the life once, or wait for a checkpoint)")
    snap = src.parent / "_snapshots" / name
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True)
    for f in COPY + ("config.json", "live.json"):
        if (src / f).exists():
            shutil.copy2(src / f, snap / f)
    return snap


def fork(src: Path, arm: dict, name: str, months: int, root: Optional[Path] = None, origin: str = "") -> Path:
    if not (src / "resume.pt").exists():
        raise SystemExit(f"{src} has no resume.pt to fork from (stop the life once, or wait for a checkpoint)")
    dst = (root or src.parent) / f"{name}-{arm['name']}"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in COPY:
        if (src / f).exists():
            shutil.copy2(src / f, dst / f)
    cfg = json.loads((src / "config.json").read_text(encoding="utf-8-sig"))
    live = json.loads((src / "live.json").read_text(encoding="utf-8")) if (src / "live.json").exists() else {}
    import torch
    age_m = int(torch.load(src / "resume.pt", map_location="cpu", weights_only=False)["age"])
    cfg["max_age_years"] = (age_m + months) / 12
    cfg["ablate"] = sorted(set(cfg.get("ablate", [])) | set(arm["ablate"]))
    cfg["experiment"] = {"name": name, "arm": arm, "forked_from": origin or src.name, "fork_age_months": age_m}
    (dst / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    lines = [json.dumps({"key": k, "value": v}) for k, v in arm["factors"].items()]
    if arm["state"]:
        lines.append(json.dumps({"state": arm["state"]}))
    lines += [json.dumps({"remove": r}) for r in arm["remove"]]
    (dst / "interventions.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return dst


def run_arm(dst: Path, device: str) -> int:
    env = dict(os.environ)
    if device:
        env["VEGA_DEVICE"] = device
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run([sys.executable, "-m", "vegalife.trainer", str(dst), "--resume"], env=env,
                          cwd=str(Path(__file__).resolve().parent.parent), creationflags=flags).returncode


def measure(dst: Path) -> dict:
    live = json.loads((dst / "live.json").read_text(encoding="utf-8"))
    fork_m = json.loads((dst / "config.json").read_text(encoding="utf-8"))["experiment"]["fork_age_months"]
    after = lambda curve: [v for a, v in live["curves"].get(curve, []) if a * 12 > fork_m]
    self_q = []
    for line in (dst / "events.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("kind") == "self" and e.get("age", 0) * 12 > fork_m:
            self_q.append(e.get("lived_reward", 0.0))
    st_ = live["state"]
    mean = lambda xs: round(st.mean(xs), 4) if xs else None
    return {"age": live["age_years"], "alive": live["alive"], "cause_of_death": live.get("cause_of_death"),
            "wellbeing": mean(after("wellbeing")), "reward": mean(after("reward")),
            "self_answers": mean(self_q), "self_knowledge": live.get("self_knowledge"),
            "mood": st_["personality"]["mood"],
            "traits": {k: st_["personality"][k] for k in ("openness", "conscientiousness", "extraversion",
                                                           "agreeableness", "neuroticism")},
            "anxiety": st_["mind"]["anxiety"], "grief": st_["mind"].get("grief"),
            "wealth": st_["economy"]["wealth"], "self_model": live["mind"]["self_model"],
            "thoughts": live["mind"]["thoughts"], "inner_voice": live["mind"].get("inner", ""),
            "guilt": live["mind"]["guilt"], "babble": live.get("babble", ""),
            "dreams": [d[1] for d in live.get("dreams", [])[-2:]],
            "brain": live.get("brain"), "ablate": live.get("ablate", [])}


def compare(results: Dict[str, dict]) -> dict:
    base = results.get("control") or next(iter(results.values()))
    out = {}
    for name, r in results.items():
        d = {}
        for k in ("wellbeing", "reward", "self_answers", "self_knowledge", "mood", "anxiety", "wealth", "guilt"):
            if r.get(k) is not None and base.get(k) is not None:
                d[k] = round(r[k] - base[k], 4)
        d["traits"] = {t: round(r["traits"][t] - base["traits"][t], 4) for t in r["traits"]}
        a, b = set(r["self_model"]), set(base["self_model"])
        d["self_model_overlap"] = round(len(a & b) / len(a | b), 3) if a | b else 1.0     # both empty: the same
        out[name] = d
    return out


def report_md(name: str, src: str, months: int, results: Dict[str, dict], diff: dict) -> str:
    rows = ["| arm | age | wellbeing | mood | anxiety | self-answers | self-knowledge | self-model overlap |",
            "|---|---|---|---|---|---|---|---|"]
    for arm, r in results.items():
        rows.append(f"| {arm} | {r['age']} | {r['wellbeing']} | {r['mood']} | {r['anxiety']} | {r['self_answers']} | "
                    f"{r['self_knowledge']} | {diff[arm]['self_model_overlap']} |")
    words = [f"### {arm}\n- self-model: {' '.join(r['self_model']) or '(none)'}\n- thoughts: {' '.join(r['thoughts'])}"
             f"\n- inner voice: {r['inner_voice'] or '(none yet)'}\n- says: {r['babble'][:160]!r}"
             f"\n- trait shifts vs control: {diff[arm]['traits']}" for arm, r in results.items()]
    return (f"# Experiment {name}\n\nForked from {src}, every arm lived {months} more months from the same state "
            f"and the same randomness; only the arm's change differs.\n\n" + "\n".join(rows) + "\n\n"
            + "\n\n".join(words) + "\n")


def main(argv: List[str] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--device", default="")
    a = ap.parse_args(argv)
    src = Path(a.src)
    busy = [d.name for d in src.parent.iterdir() if d.is_dir() and proc.alive(d)]
    if busy and a.device != "cpu":
        raise SystemExit(f"a life is running on the GPU ({', '.join(busy)}); wait, or pass --device cpu")
    arms = [parse_arm(x) for x in (a.arm or ["control"])]
    if not any(x["name"] == "control" for x in arms):
        arms.insert(0, parse_arm("control"))
    results = {}
    snap = snapshot(src, a.name)                       # every arm forks from this one saved month
    for arm in arms:
        dst = fork(snap, arm, a.name, a.months, root=src.parent, origin=src.name)
        print(f"running arm {arm['name']} in {dst} ...", flush=True)
        code = run_arm(dst, a.device)
        if code != 0:
            print(f"arm {arm['name']} exited with code {code}", flush=True)
        results[arm["name"]] = measure(dst)
    shutil.rmtree(snap, ignore_errors=True)
    diff = compare(results)
    out = {"name": a.name, "from": src.name, "months": a.months, "arms": results, "vs_control": diff}
    (src.parent / f"{a.name}-report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (src.parent / f"{a.name}-report.md").write_text(report_md(a.name, src.name, a.months, results, diff),
                                                    encoding="utf-8")
    print(f"report: {src.parent / (a.name + '-report.md')}")


if __name__ == "__main__":
    main()
