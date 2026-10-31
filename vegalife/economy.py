"""Work and money as one loop: the occupation his education leads to, the household's cash flow, the stress that
comes from it, what that stress takes away (care, a decent home), and leaving for another country.

  occupation   his field (from what he studied) and a tier (elementary, skilled/clerical, associate professional,
               professional, senior). The tier comes from his credential, ability and school record, and is pushed
               down by hiring bias and a criminal record (prejudice.py, hardships.py). It sets his pay path,
               how much say he has at work, how fast he burns out, and how exposed he is to layoffs and automation
  cash flow    pay (and a partner's, if they live together), pension, minus housing, children, debt and care costs.
               A shortfall builds financial stress; a surplus lets it ease. Financial strain is among the
               strongest everyday stressors, and money worries cut access to care where care is paid for
               (about a quarter of US adults delay care because of cost, KFF)
  housing      chronic strain forces a move somewhere cheaper, often louder and more polluted
  migration    about 3.6% of people live outside the country they were born in (UN DESA 2024). He may leave a poorer
               or less stable region for work: a fresh start, a lost homeland, family far away, and years of
               working below his qualifications before things settle
  inheritance  what his parents leave scales with what they had, so advantage and poverty pass down (family.py)

Its own random generator.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .factors import REGION_NAMES, FactorSet

TIERS = ["elementary work", "skilled or clerical work", "an associate professional job", "a professional job",
         "a senior role"]
# field: (pay multiplier, automation exposure, burnout, titles by tier)
FIELDS: Dict[str, tuple] = {
    "health": (1.15, 0.2, 1.3, ["a care assistant", "a healthcare assistant", "a paramedic", "a doctor", "a consultant"]),
    "engineering": (1.15, 0.35, 1.0, ["a labourer", "a technician", "an engineering technologist", "an engineer",
                                      "an engineering lead"]),
    "tech": (1.2, 0.5, 1.1, ["a helpdesk worker", "a junior developer", "a developer", "a software engineer",
                             "an engineering manager"]),
    "law": (1.2, 0.45, 1.3, ["a clerk", "a paralegal", "a legal executive", "a lawyer", "a partner at a firm"]),
    "business": (1.05, 0.55, 1.1, ["a shop worker", "an office administrator", "an account manager", "an analyst",
                                   "a director"]),
    "education": (0.85, 0.15, 1.3, ["a teaching assistant", "a learning support worker", "a tutor", "a teacher",
                                    "a head teacher"]),
    "science": (1.0, 0.3, 1.0, ["a lab assistant", "a lab technician", "a research assistant", "a scientist",
                                "a principal investigator"]),
    "arts": (0.8, 0.4, 1.0, ["a bartender", "a museum assistant", "a writer", "a curator", "a creative director"]),
    "trades": (0.95, 0.25, 1.0, ["a labourer", "an apprentice", "an electrician", "a master tradesman",
                                 "a contractor with a team"]),
    "general": (0.85, 0.6, 1.0, ["a warehouse worker", "a delivery driver", "a supervisor", "an office manager",
                                 "an operations manager"]),
}
COURSE_FIELD = {"medicine": "health", "nursing": "health", "engineering": "engineering", "computer science": "tech",
                "law": "law", "business": "business", "teaching": "education", "natural sciences": "science",
                "humanities": "arts", "art and design": "arts", "a trade apprenticeship": "trades",
                "vocational training": "trades"}
UNIVERSAL_CARE = {"Nordic countries": 1.0, "Western Europe": 0.95, "Oceania": 0.9, "East Asia": 0.85,
                  "Eastern Europe": 0.8, "Latin America": 0.5, "Middle East and North Africa": 0.5,
                  "Southeast Asia": 0.5, "North America": 0.3, "South Asia": 0.3, "Sub-Saharan Africa": 0.2}
DESTINATION = {"South Asia": ["North America", "Western Europe", "Middle East and North Africa"],
               "Southeast Asia": ["Middle East and North Africa", "North America", "Oceania"],
               "Sub-Saharan Africa": ["Western Europe", "North America", "Middle East and North Africa"],
               "Latin America": ["North America", "Western Europe"],
               "Middle East and North Africa": ["Western Europe", "North America"],
               "Eastern Europe": ["Western Europe", "Nordic countries"],
               "East Asia": ["North America", "Oceania"],
               "North America": ["Western Europe", "Oceania"], "Western Europe": ["North America", "Oceania"],
               "Nordic countries": ["Western Europe"], "Oceania": ["Western Europe", "North America"]}
RICH = {"North America", "Western Europe", "Nordic countries", "Oceania"}
PUSH = {"Sub-Saharan Africa": 1.6, "Latin America": 1.3, "South Asia": 1.3, "Middle East and North Africa": 1.3,
        "Eastern Europe": 1.2, "Southeast Asia": 1.1, "East Asia": 0.6, "North America": 0.3,
        "Western Europe": 0.4, "Nordic countries": 0.3, "Oceania": 0.4}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Economy:
    def __init__(self, F: FactorSet, seed: int):
        self.rng = random.Random(seed * 3299 + 101)
        self.field: Optional[str] = None
        self.tier: Optional[int] = None
        self.was_employed = False
        self.stress = 0.0              # 0..1 financial stress (smoothed)
        self.flow = 0.0                # this month's cash flow, in the sim's wealth units
        self.strained = 0              # months of serious strain in a row
        self.cheap_housing = False
        self.emigrated: Optional[dict] = None
        self.deskilled_until = 0
        self.recent: List[list] = []

    # ------------------------------------------------------------------ what others read
    def title(self) -> str:
        if self.tier is None or self.field is None:
            return ""
        return FIELDS[self.field][3][self.tier]

    def income_target(self, p) -> Optional[float]:
        if self.tier is None:
            return None
        pay, *_ = FIELDS[self.field]
        tier = self.tier - (1 if p.age < self.deskilled_until else 0)
        area = p.surroundings.income_shift() if hasattr(p, "surroundings") else 0.0     # where he grew up (Chetty)
        return clip((0.22 + 0.17 * max(0, tier)) * pay + 0.04 * p.work.level + area)

    def layoff_mult(self, F: FactorSet) -> float:
        if self.field is None:
            return 1.0
        return 1.0 + FIELDS[self.field][1] * F["ai_entry_automation"] - 0.08 * (self.tier or 0)

    def burnout_mult(self) -> float:
        return FIELDS[self.field][2] if self.field else 1.0

    def extra_pollution(self) -> float:
        return 0.25 if self.cheap_housing else 0.0

    def line(self) -> str:
        if self.stress > 0.55:
            return "I don't know how we'll pay for everything this month."
        if self.emigrated and self.emigrated.get("homesick", 0) > 0.2:
            return "I miss home: the food, the language, my family."
        return ""

    def to_json(self) -> dict:
        return {"field": self.field, "tier": self.tier, "tier_name": None if self.tier is None else TIERS[self.tier],
                "title": self.title(), "stress": round(self.stress, 3), "flow": round(self.flow, 4),
                "cheap_housing": self.cheap_housing, "emigrated": self.emigrated, "recent": self.recent[-6:]}

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        employed = s["employed"] > 0.5
        # --- an occupation when work begins ------------------------------------------------------------------------
        if employed and not self.was_employed and y >= 16:
            self._place(p, F, out)
        if not employed:
            self.was_employed = False
        else:
            self.was_employed = True
            if self.tier is not None and self.tier < 4 and p.work.level >= 2 + self.tier and r.random() < 0.02:
                self.tier += 1
                self._say(p, f"steps up to {self.title()}", 0.6, out)
        p.s["autonomy"] = clip(p.s["autonomy"] + 0.002 * ((self.tier or 0) - 1.5) * employed)
        # --- the household's money ----------------------------------------------------------------------------------
        if y >= 18:
            pooled = p.family.pooled(m)
            pt = p.family.partner(m)
            pay = 0.006 * s["income"] * employed + 0.004 * (pooled and pt is not None and pt.works) + 0.008 * s["pension"] * (y >= 60)
            kids = sum(1 for x in p.family.people if x.relation == "child" and x.alive and m - x.born < 216)
            housing = (0.003 + 0.004 * F["housing_unaffordable"]) * (0.6 if pooled else 1.0) * (0.5 if self.cheap_housing else 1.0) \
                * (0.6 if s["housing"] < 0.5 and y < 30 else 1.0) * (0.5 if y >= 65 and s["housing"] > 0.5 else 1.0)
            costs = (0.0012 if y >= 65 else 0.002) + housing + 0.0012 * kids + 0.002 * getattr(p.hardships, "debt_crisis", False) \
                + 0.0015 * F["parent_care_costs"] * (40 <= y < 65)
            self.flow = pay - costs
            target = clip(0.25 - 100 * self.flow + 0.25 * (s["wealth"] < 0.05) - 0.45 * s["wealth"])
            self.stress += 0.1 * (target - self.stress)
            s["financial_stress"] = round(self.stress, 4)
            if self.stress > 0.3:
                p.apply({"anxiety": 0.006 * self.stress, "allostatic_load": 0.002 * self.stress}, fades=True)
            self.strained = self.strained + 1 if self.stress > 0.6 else 0
            if self.strained >= 24 and not self.cheap_housing and s["housing"] >= 0.5 and r.random() < 0.04:
                self.cheap_housing = True
                s["wealth"] = clip(s["wealth"] + 0.02)
                self._say(p, "moves somewhere cheaper: a flat by the ring road, damp in the corners", -0.5, out)
            elif self.cheap_housing and self.stress < 0.2 and s["wealth"] > 0.3 and r.random() < 0.02:
                self.cheap_housing = False
                self._say(p, "moves somewhere better, with a park nearby", 0.6, out)
        # --- leaving for another country -------------------------------------------------------------------------------
        if self.emigrated is None and 20 <= y < 45:
            here = REGION_NAMES[int(round(F["region"] * (len(REGION_NAMES) - 1)))]
            push = PUSH.get(here, 0.5) * (1 + self.stress + 0.8 * getattr(p.hardships, "displaced", False)
                                          + 0.4 * (not employed)) * (0.5 + s["openness"])
            if r.random() < 0.00015 * push:
                self._emigrate(p, F, here, out)
        if self.emigrated is not None:
            e = self.emigrated
            e["homesick"] = round(max(0.0, e.get("homesick", 0.6) * 0.985), 3)
            if e["homesick"] > 0.2:
                p.apply({"loneliness": 0.003 * e["homesick"]}, fades=True)
        return out

    def _place(self, p, F: FactorSet, out: List[dict]) -> None:
        """His first job, or a new one after a gap: field from what he studied, tier from credential and ability,
        pushed down by bias he meets in hiring and by a record."""
        r, s = self.rng, p.s
        course = getattr(p.school, "course", None)
        if self.field is None:
            self.field = COURSE_FIELD.get(course or "", "general")
        cred = s["credential"]
        base = 3 if cred >= 0.9 else 2 if cred >= 0.4 else 1
        if self.field == "general" and cred < 0.4:
            base = 0 if r.random() < 0.5 else 1
        z = (p.school.iq - 100) / 15
        score = base + 0.35 * z + 0.8 * (s["academic"] - 0.5) + r.gauss(0, 0.5)
        if r.random() > p.prejudice.callback(F):
            score -= 0.8
        if getattr(p.hardships, "record", False):
            score -= 1.0
        new = int(clip(round(score), 0, 3))
        if self.tier is not None:
            new = max(new, self.tier - 1)            # a new job after a gap is rarely far below the last one
        self.tier = new
        self._say(p, f"starts work as {self.title()}", 0.5, out)

    def _emigrate(self, p, F: FactorSet, here: str, out: List[dict]) -> None:
        r, s = self.rng, p.s
        there = r.choice(DESTINATION.get(here, ["North America"]))
        visible = here not in RICH and there in RICH
        F.set("region", REGION_NAMES.index(there) / (len(REGION_NAMES) - 1), "live")
        F.set("migrant_background", 1.0, "live")
        if visible:
            F.set("minority_status", 1.0, "live")
        p.prejudice.region = there
        from .prejudice import ACCEPT
        p.prejudice.accept = ACCEPT.get(there, 0.5)
        self.emigrated = {"from": here, "to": there, "at": round(p.years, 1), "homesick": 0.6}
        s["wealth"] = clip(s["wealth"] - 0.05)
        s["employed"] = 0.0
        s["community_support"] = clip(s["community_support"] - 0.2)
        self.deskilled_until = p.age + 12 * r.randint(2, 6)        # foreign qualifications, a new language
        p.family.abroad = True
        self._say(p, f"leaves {here} for a new life in {there}, with two suitcases and a lot of hope", 0.2, out)

    def _say(self, p, text: str, valence: float, out: List[dict]) -> None:
        self.recent.append([round(p.years, 1), text])
        self.recent = self.recent[-20:]
        out.append({"text": text, "valence": valence, "arousal": 0.3 + 0.4 * abs(valence), "who": [], "key": "work",
                    "deltas": {}})
