"""Adverse childhood experiences (round 3, C5): the eight ACE categories of the CDC's BRFSS module, counted before 18.

  abuse      emotional, physical, sexual
  household  a parent's substance misuse, a parent's mental illness, violence between the adults,
             a household member in prison, parents separating (taken from family.py's real divorce event)

Rates follow BRFSS 2011-2020 (Swedo et al. 2023, MMWR 72(26)): about 64% of US adults report at least one ACE and
about 17% report four or more. Categories cluster: poverty, household friction and cold caregiving raise all of them
together (Felitti et al. 1998), so each child gets one shared adversity level and every category scales with it.

Each experience lands at a random age before 18 as a memorable event with lasting weight. The score then carries
forward: in adulthood it raises the hazard of depression and of alcohol misuse. Four or more ACEs go with roughly
4-5 times the odds of depression and 4-7 times the odds of alcoholism in Felitti 1998; here that is a log-hazard
step per ACE (DEP_PER_ACE, ALC_PER_ACE), checked by the population report (ace_4plus, ace_depression_ratio).

Its own random generator: it never shifts his world.
"""
from __future__ import annotations

import random
from typing import Dict, List

# category: (base share of children, text, deltas when it lands)
CATS: Dict[str, tuple] = {
    "emotional_abuse": (0.30, "is told again and again at home that he is worthless",
                        {"neuroticism": 0.02, "anxiety": 0.05, "attachment": -0.05}),
    "physical_abuse": (0.16, "is hit at home, hard enough to leave marks",
                       {"anxiety": 0.07, "attachment": -0.06, "aggression": 0.03}),
    "sexual_abuse": (0.10, "is sexually abused by an adult he should have been safe with",
                     {"anxiety": 0.09, "attachment": -0.08, "neuroticism": 0.02}),
    "parent_substance": (0.23, "lives with a parent whose drinking or drugs rule the house",
                         {"household_friction": 0.08, "anxiety": 0.04}),
    "parent_mental_illness": (0.17, "lives with a parent too unwell in their mind to look after him",
                              {"caregiver_attention": -0.06, "anxiety": 0.04}),
    "domestic_violence": (0.16, "sees one of the adults at home hurt the other",
                          {"household_friction": 0.1, "anxiety": 0.07}),
    "household_prison": (0.07, "sees someone from his home sent to prison",
                         {"household_friction": 0.05, "wealth": -0.02, "anxiety": 0.03}),
}
SEPARATION = "parental_separation"            # counted from family.py's "divorce" happening, not sampled here
DEP_PER_ACE = 0.75                             # log-hazard per ACE, tuned so 4+ vs none gives an ever-depressed OR near 3
ALC_PER_ACE = 0.38                             # log-hazard per ACE for alcohol misuse
# Share of children by ACE score in this model (0, 1, 2, 3, 4, 5, 6+), measured on 400 lives; it matches BRFSS.
SCORE_SHARE = (0.37, 0.215, 0.145, 0.13, 0.07, 0.04, 0.03)


def _norm(per: float) -> float:
    """log of the population-average hazard multiplier, so ACEs spread risk between people without raising the
    calibrated average in mental.py: subtract it and the mean multiplier is 1."""
    import math
    return math.log(sum(w * math.exp(per * n) for n, w in enumerate(SCORE_SHARE)))


def clip(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


class Ace:
    def __init__(self, F, seed: int, start_month: int = 0):
        self.rng = random.Random(seed * 7919 + 31)
        r = self.rng
        # one shared adversity level: poorer, colder, more crowded homes carry more of every category
        lvl = 1.0 + 1.3 * (0.5 - F["ses"]) + 1.4 * (0.65 - F["caregiver_warmth"]) + r.gauss(0, 0.95)
        self.adversity = max(0.0, lvl)
        self.plan: Dict[str, int] = {}             # category -> month it lands
        for k, (base, _, _) in CATS.items():
            if r.random() < clip(0.88 * base * self.adversity ** 1.6):
                self.plan[k] = r.randint(12, 17 * 12)
        self.had: List[str] = []
        self.off = False
        # A life saved before this module existed: its childhood already happened without these, so nothing earlier
        # than now is replayed and the score only counts what is still ahead.
        self.partial = start_month > 0
        self.plan = {k: m for k, m in self.plan.items() if m >= start_month}

    @property
    def score(self) -> int:
        return len(self.had)

    def step(self, p) -> None:
        """Before 18: land any planned experience this month, and count a real parental separation."""
        if self.off or p.age >= 18 * 12:
            return
        if SEPARATION not in self.had and any(h.get("key") == "divorce" for h in p.happenings):
            self.had.append(SEPARATION)
        for k, m in list(self.plan.items()):
            if p.age >= m:
                del self.plan[k]
                _, text, d = CATS[k]
                p.apply(d, fades=True)          # the lasting part is in the score and its hazard
                self.had.append(k)
                p.note(text, -0.8, 0.85, key="ace", deltas=d)

    def hazard(self, condition: str) -> float:
        """Extra log-hazard for an adult condition, from how many ACEs he carries."""
        if self.off:
            return 0.0
        per = {"depression": DEP_PER_ACE, "alcohol use": ALC_PER_ACE}.get(condition, 0.0)
        n = self.score
        if condition == "depression" and "parent_mental_illness" in self.had:
            n -= 1                       # mental.py's family_history already carries a parent's illness
        # relative to the average child: the base rates in mental.py were already calibrated on everyone
        return per * n - _norm(per)

    def to_json(self) -> dict:
        return {"off": self.off, "score": self.score, "had": list(self.had), "partial": self.partial}


def odds_ratio(a: float, b: float) -> float:
    """Odds ratio of two shares, used by the population report."""
    a, b = min(max(a, 1e-6), 1 - 1e-6), min(max(b, 1e-6), 1 - 1e-6)
    return (a / (1 - a)) / (b / (1 - b))

