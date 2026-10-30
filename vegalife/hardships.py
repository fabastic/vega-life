"""Hardships that can come at any age, and faith: substances, accidents, crime (suffered and committed), debt, war and
displacement, a pandemic, and belief.

Rough figures used:
  smoking       most smokers start before 18; about 11% of US adults smoke now, about 20% worldwide; teen vaping about
                1 in 10 at high school. Smoking raises lung cancer, COPD, heart attack and stroke risk (illness.py);
                quitting before 40 gives back most of the lost years
  cannabis      common in teens and twenties; about 3 in 10 users develop some use disorder; heavy teenage use raises
                psychosis risk (mental.py)
  gambling      problem gambling in about 1-2% of adults, mostly young men, now mostly on phones
  opioids       misuse in a few percent; overdose deaths concentrated at 25-54, by far highest in North America
  roads         the leading cause of death at 5-29 worldwide; young men about 3x women; most crashes injure, few kill
  crime         violent victimisation about 1-2% a year in the US, more in unsafe neighbourhoods; sexual assault over a
                lifetime for about 1 in 5 women and a smaller share of men; offending peaks at 15-25 (the age-crime
                curve) with risk-taking friends, poverty, untreated ADHD and leaving school; about 1 in 17 US men are
                imprisoned at some point; prison scars later employment
  debt          a debt crisis (bailiffs, payday loans, bankruptcy) for roughly 1 in 10 over a life, mostly the poor
  war           rare in most regions, real in some; displacement turns a life upside down
  pandemic      one in a lifetime is likely: months of lockdown, loneliness for the young and old, lost schooling
  faith         religiosity varies hugely by region; regular attendance goes with more community support and
                lower mortality in cohort studies; many lose faith in their teens and twenties, some find it in a crisis

Its own random generator. A fatal overdose or crash names the cause of death (world.py).
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .factors import FactorSet

FAITH = {"Middle East and North Africa": 0.85, "Sub-Saharan Africa": 0.85, "South Asia": 0.8, "Southeast Asia": 0.7,
         "Latin America": 0.65, "North America": 0.5, "Eastern Europe": 0.45, "Oceania": 0.35, "Western Europe": 0.3,
         "East Asia": 0.2, "Nordic countries": 0.2}
WAR = {"Middle East and North Africa": 0.00012, "Sub-Saharan Africa": 0.0001, "Eastern Europe": 0.00005,
       "South Asia": 0.00003, "Southeast Asia": 0.00002, "Latin America": 0.00002}
OPIOIDS = {"North America": 1.0, "Western Europe": 0.3, "Oceania": 0.3, "Eastern Europe": 0.3}
PRISON = {"North America": 1.0, "Latin America": 0.6, "Eastern Europe": 0.5, "Sub-Saharan Africa": 0.4,
          "Oceania": 0.4, "Western Europe": 0.25, "Nordic countries": 0.15}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Hardships:
    def __init__(self, F: FactorSet, seed: int, region: str = "North America"):
        self.rng = random.Random(seed * 1531 + 83)
        r = self.rng
        self.region = region
        self.smoker = False
        self.ever_smoked = False
        self.vapes = False
        self.cannabis = 0.0          # 0 none .. 1 daily
        self.gambling = 0.0
        self.opioids = False
        self.in_prison_until = 0
        self.record = False
        self.debt_crisis = False
        self.displaced = False
        self.pandemic_at = int(12 * r.uniform(5, 80))     # roughly one in a lifetime
        self.faith = clip(r.gauss(FAITH.get(region, 0.5) * (0.6 + 0.8 * F["cultural_strictness"]), 0.15))
        self.attends = False
        self.fatal: Optional[str] = None
        self.disabled = False
        self.counts: Dict[str, int] = {}
        self.recent: List[list] = []

    def to_json(self) -> dict:
        return {"smoker": self.smoker, "ever_smoked": self.ever_smoked, "vapes": self.vapes,
                "cannabis": round(self.cannabis, 2), "gambling": round(self.gambling, 2), "opioids": self.opioids,
                "in_prison": self.in_prison_until > 0, "record": self.record, "debt_crisis": self.debt_crisis,
                "displaced": self.displaced, "faith": round(self.faith, 2), "attends": self.attends,
                "disabled": getattr(self, "disabled", False),
                "counts": self.counts, "recent": self.recent[-8:]}

    def hiring(self) -> float:
        """A criminal record roughly halves callbacks (Pager 2003)."""
        return 0.5 if self.record else 1.0

    def line(self) -> str:
        if self.in_prison_until:
            return "Every day in here is the same."
        if self.gambling > 0.5:
            return "One more win and I can pay it all back."
        if self.debt_crisis:
            return "I'm scared every time the post comes."
        if self.smoker and self.rng.random() < 0.2:
            return "I keep meaning to quit smoking."
        return ""

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        self.fatal = None
        risky = s["peer_risk"]
        stress = clip(0.5 * s["allostatic_load"] + 0.3 * s["anxiety"] + 0.3 * s.get("grief", 0))
        adhd = p.mind.adhd and p.mind.diagnosed["ADHD"] is None
        poor = clip(0.5 - F["ses"]) * 2
        # --- smoking and vaping ----------------------------------------------------------------------------------
        if not self.ever_smoked and 12 <= y < 26 and r.random() < 0.004 * (0.4 + risky + 0.5 * poor + 0.3 * adhd) \
                * (1 - 0.6 * F["cultural_strictness"]):
            self.ever_smoked = self.smoker = True
            self._say(p, "smokes his first cigarette behind the school and keeps going", -0.1, "smoking", out)
        if not self.vapes and 13 <= y < 25 and p.online.has_phone and r.random() < 0.003 * (0.4 + risky):
            self.vapes = True
            self._say(p, "starts vaping and can't stop reaching for it", -0.1, "vaping", out)
        if (self.smoker or self.vapes) and y >= 20 and r.random() < 0.006 * (0.4 + s["conscientiousness"] + s["children"]):
            quit_what = "smoking" if self.smoker else "vaping"
            self.smoker = self.vapes = False
            self._say(p, f"finally quits {quit_what}, on the fifth try", 0.7, "quit", out)
        # --- cannabis, gambling, opioids ---------------------------------------------------------------------------
        if 14 <= y < 40 and self.cannabis == 0 and r.random() < 0.003 * (0.3 + risky) * (1 - 0.5 * F["cultural_strictness"]):
            self.cannabis = 0.2
            self._say(p, "tries cannabis at a party", 0.1, "cannabis", out)
        if self.cannabis > 0:
            self.cannabis = clip(self.cannabis + 0.01 * (stress + risky - 0.6) + r.gauss(0, 0.01))
            if self.cannabis > 0.7 and "daily" not in self.counts:
                self.counts["daily"] = 1
                self._say(p, "is smoking cannabis every day and losing whole months to it", -0.4, "", out)
        if 18 <= y < 70 and self.gambling == 0 and p.online.has_phone and r.random() < 0.0008 * (0.5 + risky + 0.5 * (F["sex"] >= 0.5)):
            self.gambling = 0.2
            self._say(p, "puts a bet on the football through an app", 0.2, "gambling", out)
        if self.gambling > 0:
            self.gambling = clip(self.gambling + 0.01 * (risky + stress + 0.4 * adhd - 0.85) + r.gauss(0, 0.015))
            if self.gambling > 0.6:
                s["wealth"] = clip(s["wealth"] - 0.006)
                if r.random() < 0.03:
                    self._say(p, "chases his losses until three in the morning", -0.6, "chasing", out)
        if not self.opioids and 18 <= y < 60 and r.random() < 0.0002 * OPIOIDS.get(self.region, 0.1) \
                * (0.5 + 2 * p.illness.pain_now + risky + poor):
            self.opioids = True
            self._say(p, "is prescribed painkillers after an injury and finds he can't stop", -0.6, "opioids", out)
        if self.opioids:
            s["employed"] = s["employed"] if r.random() > 0.01 else 0.0
            if r.random() < 0.0015 * OPIOIDS.get(self.region, 0.1):
                self.fatal = "an overdose"
                self._say(p, "dies of an overdose", -1.0, "", out)
                return out
            if r.random() < 0.01 * F["healthcare_access"]:
                self.opioids = False
                self._say(p, "gets into treatment and comes off opioids", 0.7, "", out)
        # --- the road --------------------------------------------------------------------------------------------
        if 16 <= y < 85:
            young = 3.0 if 16 <= y < 30 else 1.0
            crash = 0.0006 * young * (1 + 1.2 * (F["sex"] >= 0.5) * (y < 30)) * (0.5 + risky + 0.5 * (s["sleep"] < 0.4))
            if r.random() < crash:
                if r.random() < 0.02:
                    self.fatal = "a car crash"
                    self._say(p, "is killed in a car crash", -1.0, "", out)
                    return out
                bad = r.random() < 0.2
                s["motor"] = clip(s["motor"] - (0.1 if bad else 0.0))
                if bad and not self.disabled and r.random() < 0.15:
                    self.disabled = True
                    s["motor"] = clip(s["motor"] - 0.3)
                    s["autonomy"] = clip(s["autonomy"] - 0.15)
                    self._say(p, "is left using a wheelchair after the crash, and has to learn his life again", -0.9,
                              "disabled", out)
                self._say(p, "is badly hurt in a car crash and spends weeks in hospital" if bad else
                          "walks away from a car crash shaking", -0.6, "crash", out)
        # --- crime: suffered ---------------------------------------------------------------------------------------
        if y >= 10:
            unsafe = 1.4 - F["neighbourhood_safety"]
            if r.random() < 0.0005 * unsafe * (1.5 if 15 <= y < 30 else 1.0):
                self._say(p, r.choice(["is mugged at knifepoint on the way home", "is punched by a stranger outside a bar",
                                       "is threatened and robbed in the street"]), -0.7, "assault", out)
                p.apply({"anxiety": 0.06}, fades=True)
                if r.random() < 0.15 * (0.6 + s["neuroticism"]):
                    p.mind.begin("PTSD", m)
            female = F["sex"] < 0.5
            if 14 <= y < 45 and r.random() < (0.0006 if female else 0.00012):
                self._say(p, "is sexually assaulted, and it takes years before he can tell anyone" if not female else
                          "is sexually assaulted, and it takes years before she can tell anyone", -0.9, "sexual_assault", out)
                p.apply({"anxiety": 0.1, "attachment": -0.05}, fades=True)
                if r.random() < 0.35:
                    p.mind.begin("PTSD", m)
        # --- crime: committed, and prison --------------------------------------------------------------------------
        if self.in_prison_until:
            s["employed"] = 0.0
            s["community_support"] = clip(s["community_support"] - 0.004)
            if m >= self.in_prison_until:
                self.in_prison_until = 0
                self._say(p, "walks out of prison with a bag of his things and nowhere obvious to go", -0.2, "release", out)
        elif 14 <= y < 50:
            curve = 1.0 if 15 <= y < 26 else 0.3
            off = 0.0018 * curve * (0.2 + risky + poor + 0.6 * adhd + 0.4 * (s["schooling"] < 0.5 and s["employed"] < 0.5)) \
                * (1.6 if F["sex"] >= 0.5 else 0.4) * (1 - 0.5 * p.conscious.moral_sense(p, F))
            if r.random() < off:
                caught = r.random() < 0.45
                self._say(p, r.choice(["shoplifts with friends and gets caught" if caught else "shoplifts with friends",
                                       "gets into a fight and the police come" if caught else "gets into a fight",
                                       "is caught dealing" if caught else "sells some weed to friends"]), -0.3, "offence", out)
                p.conscious.after(p, F, "steal from a shop")
                if caught and y >= 16 and r.random() < 0.6 * PRISON.get(self.region, 0.3) * (1 + self.record):
                    self.record = True
                    self.in_prison_until = m + r.randint(3, 30)
                    self._say(p, "is sent to prison", -0.9, "prison", out)
                    p.apply({"anxiety": 0.1, "identity_crisis": 0.1}, fades=True)
                elif caught and y >= 16:
                    self.record = True
        # --- debt ----------------------------------------------------------------------------------------------------
        if y >= 20 and not self.debt_crisis and s["wealth"] < 0.03 and r.random() < 0.003 * (1 + 3 * self.gambling):
            self.debt_crisis = True
            self._say(p, "can't pay the bills any more; letters from debt collectors pile up unopened", -0.7, "debt", out)
            p.apply({"anxiety": 0.08, "financial_paranoia": 0.1}, fades=True)
        if self.debt_crisis and s["wealth"] > 0.15:
            self.debt_crisis = False
            self._say(p, "pays off the last of his debts", 0.7, "", out)
        # --- war and displacement --------------------------------------------------------------------------------------
        if not self.displaced and r.random() < WAR.get(self.region, 0.00001):
            self.displaced = True
            s["wealth"] = clip(s["wealth"] * 0.3)
            s["housing"] = 0.0
            s["community_support"] = clip(s["community_support"] - 0.3)
            self._say(p, "flees the fighting with what he can carry; home is gone", -1.0, "war", out)
            if r.random() < 0.4:
                p.mind.begin("PTSD", m)
        # --- a pandemic ----------------------------------------------------------------------------------------------
        if self.pandemic_at <= m < self.pandemic_at + 14:
            if m == self.pandemic_at:
                self._say(p, "watches the world shut down: a pandemic, lockdowns, empty streets", -0.6, "pandemic", out)
            lonely = 1.5 if (15 <= y < 25 or y >= 70) else 1.0
            p.apply({"loneliness": 0.006 * lonely, "anxiety": 0.004}, fades=True)
            if s["schooling"] > 0.5:
                s["academic"] = clip(s["academic"] - 0.004)
            if y >= 70 and r.random() < 0.002:
                self.fatal = "the pandemic virus"
                self._say(p, "catches the virus and dies in hospital", -1.0, "", out)
                return out
        # --- faith ---------------------------------------------------------------------------------------------------
        self.attends = self.faith > 0.55 and y >= 3
        if self.attends:
            s["community_support"] = clip(s["community_support"] + 0.002)
            if r.random() < 0.01:
                self._say(p, r.choice(["sings with the congregation and feels held", "finds peace in prayer",
                                       "is brought food by people from his place of worship when things are hard"]),
                          0.6, "faith", out)
        if 14 <= y < 30 and self.faith > 0.3 and r.random() < 0.002 * (1 - FAITH.get(self.region, 0.5)) * (0.5 + s["openness"]):
            self.faith = clip(self.faith - 0.4)
            self._say(p, "stops believing what he was raised to believe", -0.2, "lost_faith", out)
        if self.faith < 0.5 and (s.get("grief", 0) > 0.3 or p.mind.active) and r.random() < 0.002:
            self.faith = clip(self.faith + 0.4)
            self._say(p, "finds faith in the worst year of his life", 0.5, "found_faith", out)
        if r.random() < 0.003 * (0.4 + s["openness"]):
            self._say(p, r.choice(["stands under a sky full of stars and feels very small, in a good way",
                                   "reaches the top of a mountain and goes quiet", "hears a piece of music that stops him in his tracks"]),
                      0.8, "awe", out)
        return out

    def _say(self, p, text: str, valence: float, key: str, out: List[dict]) -> None:
        if key:
            self.counts[key] = self.counts.get(key, 0) + 1
        self.recent.append([round(p.years, 1), text])
        self.recent = self.recent[-20:]
        out.append({"text": text, "valence": valence, "arousal": 0.4 + 0.5 * abs(valence), "who": [],
                    "key": "hardship" if valence < 0 else "good", "deltas": {}})
