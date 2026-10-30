"""The friends around him: named people with their own traits who arrive, stay close or drift away.

You can list them yourself (name, when they meet, when they leave, how close, how kind, how risk-taking, how
studious). If you do not, they are seeded from the friend factors. Friends are what the world, his language and
his situations draw on: a risk-taking friend dares him, a studious one drags him to study group, a kind one
notices when he is low.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

from .factors import FactorSet

NAMES = ["Maya", "Jonas", "Priya", "Tariq", "Elena", "Kofi", "Noor", "Luca", "Imani", "Sven", "Aiko", "Mateo",
         "Zara", "Dev", "Hana", "Omar", "Lucia", "Ben", "Yuki", "Amara"]


def clip(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


@dataclass
class Friend:
    name: str
    joined: int                       # month he meets them
    left: Optional[int] = None        # month they leave, or None
    closeness: float = 0.5
    kindness: float = 0.6
    risk: float = 0.3
    studiousness: float = 0.5
    online: bool = False
    seeded: bool = True
    died: bool = False

    def present(self, age: int) -> bool:
        return self.joined <= age and (self.left is None or age < self.left)

    def weight(self) -> float:
        return self.closeness * (0.5 if self.online else 1.0)

    def to_json(self, age: int) -> dict:
        return {"name": self.name, "since_years": round(self.joined / 12, 1),
                "until_years": None if self.left is None else round(self.left / 12, 1),
                "closeness": round(self.closeness, 2), "kindness": round(self.kindness, 2),
                "risk": round(self.risk, 2), "studiousness": round(self.studiousness, 2), "online": self.online,
                "present": self.present(age), "listed_by_user": not self.seeded, "died": self.died}


class Circle:
    def __init__(self, F: FactorSet, seed: int, listed: Optional[List[dict]] = None, seed_friends: bool = True):
        self.rng = random.Random(seed * 6151 + 29)
        self.friends: List[Friend] = []
        self.used = set()
        for d in listed or []:
            self.add(d, seeded=False)
        if seed_friends and not listed:
            self._seed(F)

    # ------------------------------------------------------------------ building the circle
    def _name(self) -> str:
        free = [n for n in NAMES if n not in self.used] or NAMES
        n = self.rng.choice(free)
        self.used.add(n)
        return n

    def add(self, d: dict, seeded: bool = True) -> Friend:
        name = str(d.get("name") or self._name())
        self.used.add(name)
        left = d.get("left_years")
        f = Friend(name=name, joined=int(round(float(d.get("joined_years", 0)) * 12)),
                   left=None if left in (None, "", "null") else int(round(float(left) * 12)),
                   closeness=clip(float(d.get("closeness", 0.5))), kindness=clip(float(d.get("kindness", 0.6))),
                   risk=clip(float(d.get("risk", 0.3))), studiousness=clip(float(d.get("studiousness", 0.5))),
                   online=bool(d.get("online", False)), seeded=seeded)
        self.friends.append(f)
        return f

    def _seed(self, F: FactorSet) -> None:
        r = self.rng
        n = round(8 * F["friend_count"] * (0.6 + 0.8 * F["extracurriculars"]))
        for i in range(n):
            early = r.random() < 0.8
            joined = int(r.uniform(40, 200)) if early else int(r.uniform(230, 480))
            self.friends.append(Friend(
                name=self._name(), joined=joined,
                closeness=clip(r.gauss(F["friend_closeness"], 0.15)),
                kindness=clip(r.gauss(0.6 + 0.2 * (F["friend_diversity"] - 0.5), 0.2)),
                risk=clip(r.gauss(F["peer_risk_culture"] * (1 - 0.4 * F["cultural_strictness"]), 0.2)),
                studiousness=clip(r.gauss(F["peer_academic_culture"], 0.2)),
                online=r.random() < F["online_friend_share"] * (1.0 if joined > 150 else 0.4)))

    # ------------------------------------------------------------------ month by month
    def step(self, age: int, F: FactorSet) -> List[tuple]:
        """Friends drift away or move; close friendships fade without effort. Listed friends leave only when you say.
        Returns (text, valence, arousal, [names]) for each thing that happened."""
        out = []
        r = self.rng
        for f in self.friends:
            if not f.present(age):
                continue
            if age == f.joined:
                out.append((f"meets {f.name}", 0.4, 0.4, [f.name]))
            if f.seeded:
                if age < 228:
                    hazard = 0.0025 * (1 - f.closeness) + 0.004 * F["housing_instability"]
                else:
                    hazard = 0.0015 * (1 - f.closeness) + 0.0015 * (1 - F["community_ties"])
                if r.random() < hazard:
                    f.left = age
                    out.append((f"{f.name} {r.choice(['moves away', 'drifts away', 'goes to a different school'])}", -0.5, 0.5, [f.name]))
            if age > 228 and f.seeded:
                f.closeness = max(0.1, f.closeness - 0.0012 * (1 - F["community_ties"]))
        return out

    def present(self, age: int) -> List[Friend]:
        return [f for f in self.friends if f.present(age)]

    def support(self, age: int) -> float:
        """0 to 1: how much everyday support his friends give."""
        return 1 - math.exp(-1.2 * sum(f.weight() * f.kindness for f in self.present(age)))

    def _mean(self, age: int, attr: str) -> float:
        fs = self.present(age)
        w = sum(f.weight() for f in fs)
        return sum(f.weight() * getattr(f, attr) for f in fs) / w if w > 0 else 0.0

    def risk(self, age: int) -> float:
        return self._mean(age, "risk")

    def study(self, age: int) -> float:
        return self._mean(age, "studiousness")

    def pick(self, age: int, rng: random.Random, trait: Optional[str] = None) -> Optional[Friend]:
        fs = self.present(age)
        if not fs:
            return None
        if trait:
            return max(fs, key=lambda f: getattr(f, trait) + rng.random() * 0.2)
        return rng.choice(fs)

    def to_json(self, age: int) -> List[dict]:
        return [f.to_json(age) for f in sorted(self.friends, key=lambda f: f.joined)]
