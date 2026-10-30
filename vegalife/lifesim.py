"""A whole life without the network: the same world, memory, present, character and brain map as the trainer, but
he chooses at random. A 90-year brain map in about a minute on the CPU, without touching the GPU.

    python -m vegalife.lifesim runs/<name> [years]      (the folder needs a config.json, as for the trainer)
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

from . import brainmap as bmod
from . import factors as fx
from .brainmap import BrainMap
from .character import Character
from .lifecore import live_choice, world_month
from .memory import Memory
from .people import Circle
from .present import Present
from .rlvr import score_scenario
from .scenarios import Scenario, draw, render_scenario_ex
from .speech import Speech
from .world import Person


class SimLife:
    def __init__(self, run_dir: Path, cfg: dict):
        self.dir = run_dir
        seed = int(cfg.get("seed", 1))
        self.F = fx.sample(seed, cfg.get("factors", {}), cfg.get("timeline", []))
        self.circle = Circle(self.F, seed, cfg.get("friends", []), bool(cfg.get("friend_seed", True)))
        self.p = Person(self.F, seed, self.circle, cfg.get("family") or None)
        self.character = Character(self.p, self.F)
        self.mem = Memory(self.F, seed)
        self.mem.state = self.p.s
        self.present = Present(self.F, seed, Speech(self.F, seed).kin)
        self.brain = BrainMap(run_dir)
        bmod.backbone(self.brain)
        self.r = random.Random(seed * 7 + 3)
        self.log = []

    def say(self, text: str) -> None:
        self.log.append({"age": round(self.p.years, 2), "text": text})

    def month(self) -> None:
        for change in self.F.apply_timeline(self.p.age):
            self.say(f"scheduled: {change}")
        world_month(self)
        if not self.p.alive:
            return
        for item in draw(self.p, self.F, self.r, 6):
            if not isinstance(item, Scenario):
                continue
            now = self.present.moment(self.p, self.F, self.r, item.key).line()
            prompt, sit, recs = render_scenario_ex(item, self.p, self.F, self.r, self.mem, rehearse=True, now=now)
            choice = self.r.randrange(len(item.choices))
            real = score_scenario(item, self.p, self.F, choice, random.Random(self.r.random()))
            live_choice(self, item, sit, choice, real, real, recs, "ABCD"[choice])

    def run(self, years: float) -> dict:
        t0 = time.time()
        while self.p.alive and self.p.age < years * 12:
            self.month()
        bmod.flush_estimates(self.brain, self.p.age)
        self.brain.close()
        stats = self.brain.stats()
        live = {"status": "finished (simulated, no network)", "age_years": round(self.p.years, 2),
                "age_months": self.p.age, "alive": self.p.alive, "cause_of_death": self.p.cause_of_death,
                "profile": "simulated", "optimizer": "none (random choices)", "model": {"params": 0},
                "brain": stats, "log": self.log[-60:], "elapsed_s": round(time.time() - t0, 1)}
        (self.dir / "live.json").write_text(json.dumps(live), encoding="utf-8")
        return live


def main() -> None:
    run_dir = Path(sys.argv[1])
    years = float(sys.argv[2]) if len(sys.argv) > 2 else 90
    cfg = json.loads((run_dir / "config.json").read_text(encoding="utf-8-sig"))
    out = SimLife(run_dir, cfg).run(years)
    print(json.dumps({k: out[k] for k in ("age_years", "brain", "elapsed_s")}))


if __name__ == "__main__":
    main()
