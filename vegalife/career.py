"""His working life, beyond employed or not: looking for work, the grind, getting on, burning out, stopping.

  job hunting   months of applications; most are rejected. Each rejection is a small hit (cortisol up, dopamine
                down); a long spell leaves a lasting dent that re-employment does not fully lift (Lucas et al. 2004:
                life satisfaction does not fully recover after unemployment).
  hours         how hard he grinds, from conscientiousness, ambition, money worries and how secure the job is.
                Long hours speed promotions and pay, and cost sleep and stress: 55+ hours a week carries stroke risk
                x1.33 and coronary risk x1.13 (Kivimäki et al. 2015, 600,000 people).
  level         0 starting out .. 4 senior. Promotions come with skill, hours and time in the job.
  burnout       builds with long hours and strain, eases with rest; past a point he burns out: time off, a
                drop in mood, sometimes quitting.
  retirement    from about 60; on average lowers depression risk by ~20% (meta-analysis of 557,000 people), but
                losing the role can sting for someone who lived for work.
The world's labour market (world.py) still decides when work is found or lost; this layer lives the months between.
"""
from __future__ import annotations

import random
from typing import List

from .factors import FactorSet

TITLES = ["a junior job", "a steady job", "a senior role", "a lead role", "running the team"]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Career:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 1663 + 97)
        self.searching = 0            # months looking for work in this spell
        self.applications = 0
        self.rejections = 0
        self.hours = 40.0
        self.level = 0
        self.tenure = 0
        self.burnout = 0.0
        self.off_until = 0            # on leave after burning out
        self.retired = False
        self.was_employed = False
        self.strain = 0.0             # 0..1, for cortisol (chemistry.py)
        self.history: List[tuple] = []
        self.ambition = self.rng.gauss(0, 0.18)   # some people simply grind harder

    def to_json(self) -> dict:
        return {"searching_months": self.searching, "applications": self.applications, "rejections": self.rejections,
                "hours": round(self.hours, 1), "level": self.level, "title": TITLES[self.level], "tenure_years":
                round(self.tenure / 12, 1), "burnout": round(self.burnout, 3), "retired": self.retired,
                "on_leave": self.off_until > 0}

    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        self.strain = 0.0
        if y < 18 or s["schooling"] > 0.5:
            return out
        employed = s["employed"] > 0.5
        # --- retiring -------------------------------------------------------------------------------------------
        if employed and not self.retired and y >= 60 and r.random() < 0.012 * (1 + (y - 60) / 3) * (0.5 + s["pension"] + s["wealth"]):
            self.retired = True
            s["employed"] = 0.0
            lived_for_work = clip(self.hours / 60) * s["conscientiousness"]
            d = {"anxiety": -0.08, "allostatic_load": -0.05, "identity_crisis": 0.15 * lived_for_work}
            p.apply(d, fades=True)
            out.append({"text": "retires", "valence": 0.4 - 0.5 * lived_for_work, "arousal": 0.5, "who": [], "key": "retire",
                        "deltas": d})
            return out
        if self.retired:
            return out
        # --- looking for work -----------------------------------------------------------------------------------
        if not employed:
            if self.was_employed or y < 66:
                self.searching += 1
                effort = 2 + 8 * s["conscientiousness"] * (1 - 0.5 * s["nihilism"])
                apps = sum(1 for _ in range(int(effort)) if r.random() < 0.7)
                no = sum(1 for _ in range(apps) if r.random() < 0.9 + 0.05 * F["algorithmic_hiring"])
                self.applications += apps
                self.rejections += no
                p.apply({"anxiety": 0.003 * no, "goal_horizon": -0.002 * no}, fades=True)
                # Applications are how work is found: each one a small chance, better with skills and a credential.
                hit = 0.07 * (0.4 + 0.6 * s["skill_value"] + 0.4 * s["credential"] + 0.3 * s["academic"]) \
                    * (1 - 0.4 * F["algorithmic_hiring"]) * (1 - 0.5 * F["ai_entry_automation"] * (y < 26))                     * (p.prejudice.callback(F) if hasattr(p, "prejudice") else 1.0) \
                    * (p.hardships.hiring() if hasattr(p, "hardships") else 1.0)       # bias, and a criminal record
                if y < 66 and any(r.random() < hit for _ in range(apps)):
                    s["employed"] = 1.0
                self.strain = clip(0.1 + 0.03 * no + 0.02 * self.searching)
                if self.searching == 6:
                    out.append({"text": f"has been looking for work for six months ({self.rejections} rejections)",
                                "valence": -0.6, "arousal": 0.5, "who": [], "key": "work", "deltas": {}})
                if self.searching > 6:
                    p.chem.scar = clip(p.chem.scar + 0.004)   # a long spell leaves a mark (Lucas 2004)
            self.was_employed = False
            return out
        # --- in work --------------------------------------------------------------------------------------------
        if not self.was_employed:                         # just started
            if self.searching:
                out.append({"text": f"gets a job after {self.searching} months and {self.applications} applications",
                            "valence": 0.7, "arousal": 0.7, "who": [], "key": "work", "deltas": {"dopamine": 0.15}})
            self.searching = self.applications = self.rejections = 0
            self.tenure = 0
            self.level = max(0, self.level - 1) if self.level else 0
        self.was_employed = True
        self.tenure += 1
        if self.off_until:
            if m >= self.off_until:
                self.off_until = 0
                out.append({"text": "goes back to work after burning out", "valence": 0.1, "arousal": 0.4, "who": [],
                            "key": "work", "deltas": {}})
            else:
                self.hours = 0.0
                return out
        # how hard he grinds
        drive = (0.3 * s["conscientiousness"] + 0.2 * s["goal_horizon"] + 0.2 * (1 - s["wealth"])
                 + 0.15 * (1 - F["workplace_security"]) - 0.1 * s["children"] * (y < 45) - 0.15 * s.get("grief", 0.0)
                 + self.ambition)
        target = 30 + 30 * clip(drive) + (3 if y < 35 else 0)
        self.hours += 0.25 * (target + r.gauss(0, 2) - self.hours)
        h = self.hours
        self.strain = clip((h - 38) / 30 + 0.3 * (1 - F["workplace_security"]))
        s["sleep"] = clip(s["sleep"] - 0.004 * max(0.0, h - 45))
        s["income"] = clip(s["income"] + 0.0006 * max(0.0, h - 40) + 0.002 * self.level / 4)
        # getting on
        if self.level < 4 and r.random() < 0.011 * (0.4 + s["skill_value"]) * (h / 42) * min(2.0, self.tenure / 24) \
                * (1 - 0.18 * self.level):
            self.level += 1
            s["income"] = clip(s["income"] + 0.06)
            out.append({"text": f"is promoted to {TITLES[self.level]}", "valence": 0.7, "arousal": 0.6, "who": [],
                        "key": "work", "deltas": {"dopamine": 0.12, "income": 0.06}})
        # burning out
        self.burnout = clip(self.burnout + max(0.0, h - 48) / 700 + 0.002 * self.strain - (0.03 if h < 45 else 0.0))
        if self.burnout > 0.7 and r.random() < 0.06:
            self.burnout = 0.3
            self.off_until = m + r.randint(2, 6)
            d = {"anxiety": 0.12, "allostatic_load": 0.08, "identity_crisis": 0.06}
            p.apply(d, fades=True)
            quits = r.random() < 0.25
            if quits:
                s["employed"] = 0.0
                self.off_until = 0
            out.append({"text": "burns out and " + ("quits his job" if quits else "has to stop working for a while"),
                        "valence": -0.7, "arousal": 0.7, "who": [], "key": "burnout", "deltas": d})
        return out

    def hazard(self) -> float:
        """Long hours: stroke x1.33 and coronary disease x1.13 at 55+ a week (Kivimäki 2015), a blended multiplier."""
        h = self.hours
        return 1.0 + (0.18 if h >= 55 else 0.12 if h >= 49 else 0.04 if h >= 41 else 0.0)
