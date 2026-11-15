"""The place he grows up in, as doses over years (SURROUNDINGS.md): what the neighbourhood offers, green space, lead,
noise, heat at school, city or countryside, the commute, how a weekday is spent, and the adults around him.

  opportunity  moving to a better area shifts adult earnings by about 4% of the gap per year of childhood spent there,
               linear in age at the move and about 0 after 18 (Chetty & Hendren 2018; Chetty, Hendren & Katz 2016).
               Opportunity here is safety, school quality and the absence of violence, and its dose is summed over
               childhood years; it shifts the pay path of his occupation (economy.py)
  green space  growing up with the least green space carried 15-55% higher risk of adult psychiatric disorders than
               the most (Engemann et al. 2019, ~1M Danes). Correlational: one weak protective pathway, by years of
               childhood exposure (mental.py)
  lead         ~3.9 IQ points lost from 2.4 to 10 ug/dL of blood lead, 6.9 to 30 (Lanphear et al. 2005), log-linear,
               set in early childhood
  noise        aircraft noise slows reading comprehension in a dose-dependent way (RANCH: ~1-2 months of reading age
               per 5 dB); here a slower reading grade above 55 dB
  heat         a 1°F hotter school year costs about 1% of a year's learning, almost fully offset by air conditioning
               (Park et al. 2020); air conditioning follows school quality here
  urbanicity   psychosis risk about 2.4x in the most urban vs the most rural areas in high-income countries (Vassos et
               al. 2012), by childhood years in the city (mental.py)
  income       the poorest gain most from small income differences (Noble et al. 2015): the link from family income to
               early learning is logarithmic, not linear
  commute      a one-hour each-way commute needs about 40% more pay to leave people as satisfied (Stutzer & Frey 2008):
               lost sleep, stress, lower mood
  time use     a typical weekday: sleep, school or work, commute, screens, outdoors, friends, from the rest of his life
  neighbours   a few named adults (a coach, a neighbour, a shopkeeper, a teacher) who can mentor or help him
"""
from __future__ import annotations

import math
import random
from typing import Dict, List

from .factors import FactorSet
from .voice import in_voice

ROLES = [("coach", "his football coach", {"motor": 0.02, "resilience": 0.01},
          ["{n}, his coach, tells him he could go far", "{n} drives him home after training when no one else can"]),
         ("teacher", "a teacher who believes in him", {"academic": 0.02, "goal_horizon": 0.02},
          ["{n} keeps him after class to say his essay was the best in the year", "{n} lends him a book that changes how he sees things"]),
         ("neighbour", "the neighbour", {"community_support": 0.02},
          ["{n} next door takes in his parcels and asks how he really is", "{n} next door shows him how to fix a bike"]),
         ("shopkeeper", "the shopkeeper on the corner", {"community_support": 0.01},
          ["{n} at the corner shop slips him a free bar of chocolate", "{n} at the corner shop remembers his name"])]
NAMES = ["Mr Okafor", "Mrs Lindqvist", "Mr Haddad", "Ms Ferreira", "Mr Tanaka", "Mrs Novak", "Ms Adeyemi", "Mr Kowalski"]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Surroundings:
    def __init__(self, F: FactorSet, seed: int):
        self.rng = random.Random(seed * 5119 + 43)
        r = self.rng
        self.opportunity_dose = 0.0     # years of childhood x how much better (or worse) than average the area is
        self.green_dose = 0.0           # years of childhood x green space
        self.urban_dose = 0.0           # years of childhood x urbanicity
        self.iq_lost = 0.0
        self.mood_drag = 0.0
        self.neighbours = [{"role": role, "name": r.choice(NAMES), "what": what, "met": round(r.uniform(4, 12), 1)}
                           for role, what, _, _ in r.sample(ROLES, 2 + int(F["community_ties"] > 0.5))]
        self.day: Dict[str, float] = {}
        self.days: Dict[int, Dict[str, float]] = {}     # his weekday at each birthday, for the time-use view
        self.recent: List[list] = []

    def opportunity(self, F: FactorSet) -> float:
        return (F["neighbourhood_safety"] + F["school_quality"] + (1 - F["structural_violence"])) / 3

    def income_shift(self) -> float:
        """What his childhood area does to his adult pay (economy.py): ~4% of the gap per year of exposure."""
        return clip(0.006 * self.opportunity_dose, -0.12, 0.12)

    def mental_risk(self) -> Dict[str, float]:
        """Log-risk shifts for mental.py: green space protects a little; a city childhood raises psychosis risk."""
        green = self.green_dose / 18 if self.green_dose else 0.5
        return {"depression": -0.4 * (green - 0.5), "anxiety": -0.3 * (green - 0.5),
                "psychosis": 0.88 * self.urban_dose / 18}

    def to_json(self) -> dict:
        return {"opportunity_dose": round(self.opportunity_dose, 2), "green_dose": round(self.green_dose, 2),
                "urban_dose": round(self.urban_dose, 2), "iq_lost": round(self.iq_lost, 1),
                "income_shift": round(self.income_shift(), 3), "day": self.day, "neighbours": self.neighbours,
                "days": getattr(self, "days", {}),
                "recent": self.recent[-6:]}

    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, out = self.rng, p.s, p.years, []
        # --- childhood doses ------------------------------------------------------------------------------------
        if y < 18:
            self.opportunity_dose += (self.opportunity(F) - 0.5) * 2 / 12
            self.green_dose += F["green_space"] / 12
            self.urban_dose += F["urbanicity"] / 12
        # --- lead: early childhood, log-linear ----------------------------------------------------------------------
        if p.age == 72:
            lead = 1 + 29 * F["lead_exposure"]                  # ug/dL
            if lead > 2.4:
                self.iq_lost = round(2.7 * math.log(lead / 2.4), 1)
                p.school.iq -= self.iq_lost
        # --- at school: noise and heat ------------------------------------------------------------------------------
        if s["schooling"] > 0.5 and y < 19:
            db = 40 + 35 * F["noise"]
            if db > 55:
                for k in ("literature", "languages"):
                    p.school.grades[k] = clip(p.school.grades[k] - 0.0005 * (db - 55) / 5)
            hot = F["extreme_weather"] * (1 - F["school_quality"])          # no air conditioning in poorer schools
            s["academic"] = clip(s["academic"] - 0.0008 * hot)
            if 3 <= y < 12:                                                  # income acts on early learning on a log scale
                logged = math.log(1 + 9 * F["ses"]) / math.log(10)
                s["academic"] = clip(s["academic"] + 0.0015 * (logged - F["ses"]))
        # --- the commute --------------------------------------------------------------------------------------------
        minutes = 120 * F["commute"] if s["employed"] > 0.5 and y >= 18 else 0.0
        self.mood_drag = 0.03 * minutes / 60
        if minutes > 30:
            s["sleep"] = clip(s["sleep"] - 0.0006 * minutes / 10)
            p.apply({"allostatic_load": 0.0008 * minutes / 30}, fades=True)
        # --- a weekday --------------------------------------------------------------------------------------------
        work = p.work.hours / 5 if s["employed"] > 0.5 else 0.0
        school = 6.5 if s["schooling"] > 0.5 and y < 19 else 0.0
        screens = min(10.0, p.online.hours)
        outdoors = max(0.0, (1.6 - F["low_walkability"] - 0.1 * screens + F["green_space"]) * (1.2 if y < 12 else 0.7))
        self.day = {"sleep": round(6 + 3 * s["sleep"], 1), "school": school, "work": round(work, 1),
                    "commute": round(2 * minutes / 60, 1), "screens": round(screens, 1), "outdoors": round(outdoors, 1),
                    "friends": round(1.5 * s["peer_support"] + 0.5 * s["community_support"], 1)}
        if p.age % 12 == 0 and y >= 3:
            if not hasattr(self, "days"):
                self.days = {}
            self.days[int(y)] = dict(self.day)
        # --- the adults around him ----------------------------------------------------------------------------------
        if 4 <= y < 25:
            for nb in self.neighbours:
                if y >= nb["met"] and r.random() < 0.01:
                    role = next(x for x in ROLES if x[0] == nb["role"])
                    p.apply(role[2], fades=False)
                    text = in_voice(r.choice(role[3]), getattr(p, "female", False)).format(n=nb["name"])
                    self.recent.append([round(y, 1), text])
                    out.append({"text": text, "valence": 0.6, "arousal": 0.4, "who": [nb["name"]], "key": "mentor",
                                "deltas": dict(role[2])})
        return out
