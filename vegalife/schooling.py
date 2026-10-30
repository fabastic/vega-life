"""His education, as it actually runs where he lives: when school starts, the move up to secondary, the subjects he
is drawn to, the big exam, whether he can get into and pay for what he wants to study, and whether he finishes.

Where he grows up sets the system (REGIONS, rough figures):
  start       age school starts (5 in the UK and Oceania, 6 in most places, 7 in the Nordics)
  pressure    how much rides on one exam: the gaokao and the CSAT (East Asia), JEE/NEET and board exams (South Asia)
  tutoring    share of children in paid after-school tutoring: 80% in South Korea in 2024 (Statistics Korea),
              very common in South and East Asia, far less in Europe
  entry       share who go on to university: about 7 in 10 in Korea and Canada, ~48% of young adults in the OECD hold
              a tertiary degree (Education at a Glance 2025), far fewer in South Asia and Sub-Saharan Africa
  tuition     what a degree costs against family income: close to free in the Nordics and much of continental Europe,
              very expensive in the US
  push        how strongly families steer children toward medicine, engineering and law
  gendered    how strongly subjects are seen as for boys or girls (a girl in engineering, a boy in nursing)

How he does depends on what he brings: intelligence (IQ explains roughly a quarter of the spread in school results),
how hard he works, his home and his school; and how well he adapts sets how long each transition (a new school,
university) unsettles him.

Subjects: from about 8 he is drawn to some subjects more than others. Interest comes from temperament and ability,
and grows where he does well and is encouraged (interest and achievement feed each other). Around 15-16 he picks his
subjects; at 18 he wants a particular course. Whether he gets it depends on three things, all visible in the UI:
  academic    his exam result against how selective the course is
  economic    what it costs where he lives against what his family has (and whether he can borrow)
  social      what his family expects and what people think is "for someone like him"
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .factors import REGION_NAMES, FactorSet

# name: start, pressure, tutoring, entry, tuition, push, gendered, exam name
REGIONS: Dict[str, tuple] = {
    "North America": (6, 0.35, 0.25, 0.62, 0.9, 0.3, 0.3, "final exams and the SAT"),
    "Latin America": (6, 0.45, 0.3, 0.5, 0.5, 0.4, 0.5, "the university entrance exam"),
    "Western Europe": (6, 0.45, 0.25, 0.55, 0.35, 0.3, 0.3, "his final school exams"),
    "Nordic countries": (7, 0.25, 0.1, 0.55, 0.05, 0.2, 0.2, "his final school exams"),
    "Eastern Europe": (7, 0.45, 0.4, 0.55, 0.35, 0.4, 0.45, "the state exams"),
    "Middle East and North Africa": (6, 0.6, 0.45, 0.42, 0.45, 0.6, 0.65, "the national secondary exam"),
    "Sub-Saharan Africa": (6, 0.55, 0.3, 0.1, 0.75, 0.55, 0.6, "the national school-leaving exam"),
    "South Asia": (6, 0.8, 0.65, 0.28, 0.55, 0.8, 0.65, "the board exams and the entrance tests"),
    "East Asia": (6, 0.9, 0.8, 0.7, 0.55, 0.6, 0.45, "the national university entrance exam"),
    "Southeast Asia": (6, 0.6, 0.5, 0.35, 0.5, 0.55, 0.5, "the national exam"),
    "Oceania": (5, 0.35, 0.2, 0.55, 0.6, 0.3, 0.3, "his final school exams"),
}

SUBJECTS = ["maths", "science", "computing", "literature", "history", "languages", "art", "music", "sport",
            "business", "technical"]
# course: (subjects it builds on, selectivity 0..1, cost x, payoff to skill, gendered toward: 1 boys / -1 girls)
COURSES: Dict[str, tuple] = {
    "medicine": (("science", "maths"), 0.9, 1.4, 0.9, 0),
    "engineering": (("maths", "science", "technical"), 0.72, 1.1, 0.8, 1),
    "computer science": (("computing", "maths"), 0.68, 1.0, 0.85, 1),
    "law": (("history", "literature"), 0.75, 1.1, 0.75, 0),
    "business": (("business", "maths"), 0.5, 1.0, 0.65, 0),
    "nursing": (("science", "sport"), 0.5, 0.8, 0.6, -1),
    "teaching": (("literature", "history", "languages"), 0.4, 0.8, 0.5, -1),
    "natural sciences": (("science", "maths"), 0.6, 1.0, 0.65, 0),
    "humanities": (("history", "literature", "languages"), 0.45, 0.9, 0.45, 0),
    "art and design": (("art", "music"), 0.45, 1.0, 0.4, 0),
    "a trade apprenticeship": (("technical", "sport"), 0.2, 0.3, 0.55, 1),
}
PUSHED = ("medicine", "engineering", "law", "computer science")


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def region_of(F: FactorSet) -> str:
    return REGION_NAMES[int(round(F["region"] * (len(REGION_NAMES) - 1)))]


class Schooling:
    def __init__(self, F: FactorSet, seed: int):
        self.rng = random.Random(seed * 5381 + 7)
        r = self.rng
        self.region = region_of(F)
        self.stage = "home"                       # home, primary, secondary, upper, tertiary, done
        self.unsettled = 0.0                      # the dip after a transition; adaptability shortens it
        self.interest: Dict[str, float] = {k: clip(r.gauss(0.4, 0.12)) for k in SUBJECTS}
        self.grades: Dict[str, float] = {k: 0.5 for k in SUBJECTS}
        self.chosen: List[str] = []               # his subjects from ~16
        self.wanted: Optional[str] = None         # the course he wants at 18
        self.course: Optional[str] = None         # what he actually studies
        self.why: List[str] = []                  # why he got (or did not get) what he wanted
        self.exam: Optional[float] = None         # 0..1 percentile in the big exam
        self.tutored = False
        self.dropped_out = False
        self.iq = 70 + 75 * F["iq"]

    # ------------------------------------------------------------------ helpers
    def sys(self) -> tuple:
        return REGIONS[self.region]

    def top(self, k: int = 3) -> List[str]:
        return [n for n, _ in sorted(self.interest.items(), key=lambda t: -t[1])[:k]]

    def to_json(self) -> dict:
        start, pressure, tutoring, entry, tuition, push, gendered, exam = self.sys()
        return {"region": self.region, "stage": self.stage, "iq": round(self.iq), "unsettled": round(self.unsettled, 3),
                "favourite": self.top(3), "chosen": self.chosen, "wanted": self.wanted, "course": self.course,
                "why": self.why, "exam_percentile": None if self.exam is None else round(100 * self.exam),
                "exam_name": exam, "tutored": self.tutored, "dropped_out": self.dropped_out,
                "system": {"start": start, "pressure": pressure, "tutoring": tutoring, "entry": entry,
                           "tuition": tuition}}

    def _move(self, p, stage: str, text: str, F: FactorSet) -> dict:
        """A transition: new place, new people. How long it unsettles him depends on his adaptability."""
        self.stage = stage
        self.unsettled = clip(0.6 - 0.5 * F["adaptability"] + 0.2 * p.s["anxiety"] + self.rng.gauss(0, 0.08), 0.05, 0.9)
        d = {"school_belonging": -0.15 * self.unsettled, "anxiety": 0.06 * self.unsettled}
        p.apply(d, fades=True)
        return {"text": text, "valence": 0.3 - 0.5 * self.unsettled, "arousal": 0.6, "who": [], "key": "school",
                "deltas": d}

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        start, pressure, tutoring, entry, tuition, push, gendered, exam_name = self.sys()
        out: List[dict] = []
        self.unsettled *= 0.88 + 0.08 * (1 - F["adaptability"])        # adaptable children settle faster
        if self.stage == "home" and m == start * 12:
            out.append(self._move(p, "primary", "starts school", F))
        elif self.stage == "primary" and m == (start + 6) * 12:
            out.append(self._move(p, "secondary", "moves up to secondary school", F))
        elif self.stage == "secondary" and m == 16 * 12:
            self.chosen = self.top(3)
            self.stage = "upper"
            out.append({"text": "chooses his subjects: " + ", ".join(self.chosen), "valence": 0.3, "arousal": 0.4,
                        "who": [], "key": "school", "deltas": {}})
        if self.stage not in ("primary", "secondary", "upper"):
            if self.stage == "tertiary":
                out += self._tertiary(p, F)
            return out
        # --- ability, effort and help become grades ---------------------------------------------------------
        z = (self.iq - 100) / 15
        effort = 0.5 * s["conscientiousness"] + 0.3 * s["goal_horizon"] + 0.2 * s["school_belonging"]
        if y < 8:
            self.tutored = False
        elif self.tutored:
            self.tutored = r.random() > 0.01
        elif r.random() < 0.04 * tutoring * (0.4 + s["wealth"] + 0.5 * F["tutoring_access"]):
            self.tutored = True
        mind = getattr(p, "mind", None)
        focus = mind.focus() if mind else 1.0               # ADHD and depression cost attention
        level = clip(0.5 + 0.11 * z + 0.15 * (effort - 0.5) + 0.06 * self.tutored - 0.12 * self.unsettled
                     + 0.08 * (s["academic"] - 0.5), 0.02, 0.98) * focus
        s["academic"] = clip(s["academic"] + 0.01 * z * (0.5 + 0.5 * F["school_quality"])
                             - 0.008 * self.unsettled - 0.006 * (1 - focus))
        for k in SUBJECTS:
            apt = {"maths": 0.06 * z, "science": 0.05 * z, "computing": 0.04 * z, "sport": 0.1 * (s["motor"] - 0.5),
                   "art": 0.05 * (s["openness"] - 0.5), "music": 0.05 * (s["openness"] - 0.5)}.get(k, 0.03 * z)
            self.grades[k] += 0.05 * (clip(level + apt + 0.15 * (self.interest[k] - 0.4)) - self.grades[k])
            # interest follows success and encouragement, and temperament
            o, e = s["openness"] - 0.5, s["extraversion"] - 0.5
            pull = 0.02 * (self.grades[k] - 0.5) + 0.01 * {"art": o, "music": o, "literature": o, "business": e,
                                                          "sport": e, "maths": z / 3, "science": z / 3,
                                                          "computing": z / 3 + 0.1 * (mind is not None and mind.autism),
                                                          "technical": 0.1 * (s["motor"] - 0.5)}.get(k, 0.0)
            pull -= 0.004 * (self.interest[k] - 0.4)                       # tastes do not run away by themselves
            self.interest[k] = clip(self.interest[k] + pull + r.gauss(0, 0.01))
        # --- exam years: pressure where much rides on one exam -----------------------------------------------
        if 15 <= y < 18:
            load = pressure * (0.4 + 0.6 * (y - 15) / 3) * (1 - 0.3 * F["adaptability"])
            p.apply({"anxiety": 0.004 * load, "allostatic_load": 0.002 * load}, fades=True)
            s["sleep"] = clip(s["sleep"] - 0.02 * load * self.tutored)
            if m == 18 * 12 - 2:
                g = sum(self.grades[k] for k in (self.chosen or self.top(3))) / 3
                nerves = 0.08 * (s["anxiety"] - 0.4) * pressure
                self.exam = clip(g + 0.1 * z + 0.05 * self.tutored - nerves + r.gauss(0, 0.07), 0.01, 0.99)
                pct = round(100 * self.exam)
                good = self.exam > 0.6
                out.append({"text": f"sits {exam_name} and scores better than {pct}% of students", "valence":
                            0.6 if good else -0.4, "arousal": 0.8, "who": [], "key": "exam",
                            "deltas": {"dopamine": 0.1 if good else -0.05}})
        return out

    # ------------------------------------------------------------------ after school
    def decide(self, p, F: FactorSet) -> float:
        """At 19: what he wants, and what he gets. Returns 1.0 university, 0.5 vocational, 0 straight to work."""
        r, s = self.rng, p.s
        start, pressure, tutoring, entry, tuition, push, gendered, exam_name = self.sys()
        male = F["sex"] >= 0.5
        exam = self.exam if self.exam is not None else s["academic"]
        fav = self.top(3)
        best, score = None, -9.0
        for c, (subs, sel, cost, pay, sexed) in COURSES.items():
            fit = sum(self.interest[k] for k in subs) / len(subs) + 0.15 * (c == "a trade apprenticeship") * (exam < 0.4)
            if fit > score:
                best, score = c, fit
        self.wanted = best
        plan = F["higher_ed_path"]                 # what his family has in mind
        why: List[str] = []
        subs, sel, cost, pay, sexed = COURSES[best]
        if best == "a trade apprenticeship":
            self.course = best
            self.why = ["he wanted to work with his hands"]
            self.stage = "done"
            return 0.5
        # social: families steer toward the prestige courses, and some courses are "not for someone like him"
        if best not in PUSHED and r.random() < push * (0.3 + 0.7 * F["cultural_strictness"]) * 0.6:
            alt = max(PUSHED, key=lambda c: sum(self.grades[k] for k in COURSES[c][0]))
            why.append(f"his family wanted him to do {alt}, not {best}")
            best = alt
        if sexed and (sexed > 0) != male and r.random() < 0.5 * gendered:
            why.append(f"people told him {best} was not for {'a girl' if not male else 'a boy'}")
            p.apply({"anxiety": 0.03}, fades=True)
        # academic: is his result good enough for how selective it is (more selective where few get in)
        bar = clip(sel * (1.15 - 0.6 * entry))
        if exam < bar:
            why.append(f"his exam result was not high enough for {best}")
            fallback = [c for c, v in COURSES.items() if COURSES[c][1] * (1.15 - 0.6 * entry) <= exam
                        and c != "a trade apprenticeship"]
            best = max(fallback, key=lambda c: sum(self.interest[k] for k in COURSES[c][0])) if fallback else None
        # economic: what it costs where he lives against what his family has
        if best:
            price = tuition * COURSES[best][2]
            can = s["wealth"] + 0.5 * F["student_debt"] + (0.3 if self.exam and self.exam > 0.9 else 0.0)  # loans, scholarships
            if price > can + 0.15 and r.random() < 0.8:
                why.append(f"his family could not afford {best}")
                best = None
        if plan < 0.4 and best and r.random() < 0.6:
            why.append("he needed to start earning")
            best = None
        if best is None:
            self.course = "vocational training" if plan >= 0.4 or r.random() < 0.4 else None
            self.why = why or ["he chose to work"]
            self.stage = "done" if self.course is None else "tertiary"
            if why:
                p.apply({"goal_horizon": -0.06, "anxiety": 0.04}, fades=True)
            return 0.5 if self.course else 0.0
        self.course = best
        self.why = why or [f"he got into {best}"]
        self.stage = "tertiary"
        got_wish = best == self.wanted
        p.apply({"goal_horizon": 0.05 if got_wish else -0.03}, fades=True)
        return 1.0

    def _tertiary(self, p, F: FactorSet) -> List[dict]:
        """Studying: a mismatch with what he wanted, money and his health make dropping out more likely (roughly a
        third of US students who start a degree do not finish within six years)."""
        r, s = self.rng, p.s
        if p.age >= p.tertiary_until or self.dropped_out:
            return []
        mismatch = self.course not in (self.wanted, "vocational training")
        risk = 0.004 * (1 + 1.5 * mismatch + 2 * (s["wealth"] < 0.2) + 2 * (1 - s["academic"])
                        + 2 * getattr(getattr(p, "mind", None), "load", lambda: 0.0)())
        s["school_belonging"] = clip(s["school_belonging"] - 0.004 * mismatch)
        if r.random() < risk:
            self.dropped_out = True
            p.tertiary_until = p.age
            p.tertiary_degree = 0.0
            return [{"text": f"drops out of {self.course}", "valence": -0.6, "arousal": 0.7, "who": [], "key": "study",
                     "deltas": {"goal_horizon": -0.05}}]
        return []

    def line(self) -> str:
        """For his thoughts: what school is like right now."""
        if self.stage == "upper" and self.exam is None:
            return "My exams are coming and everyone keeps talking about them."
        if self.stage == "tertiary" and self.course and self.course != self.wanted and self.wanted:
            return f"I am studying {self.course}, but I wanted to do {self.wanted}."
        if self.unsettled > 0.35:
            return "Everything at the new school is strange."
        return ""
