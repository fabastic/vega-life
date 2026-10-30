"""Diseases that belong to each age, and the struggles that follow them.

Each disease has an age window, a sex difference, risk factors from his life, how long it lasts, what it does to
his sleep, pain, health and mood, how likely it is to be noticed and treated, and the everyday struggles it brings.
Figures used to calibrate (lifetime or prevalence, rough):
  childhood       asthma ~8% of children; eczema ~10-15%; food allergy ~6%; type 1 diabetes ~0.3%;
                  epilepsy ~1% over a life; childhood cancer ~0.3% by 19 (about 85% survive)
  teens/20s       migraine ~15% of adults (women ~3x, worst at 30-40); IBS ~10%; Crohn's/colitis ~0.5%;
                  endometriosis and PCOS ~10% of women each; chlamydia common and curable
  adulthood       chronic insomnia disorder ~10%; moderate-severe sleep apnoea ~10% of men 30-49 and ~17% at 50-70,
                  fewer women, most undiagnosed (Peppard 2013); high blood pressure 7.5% at 18-39, 33% at 40-59,
                  63% at 60+ (CDC); type 2 diabetes ~25% over 65; reflux ~15-20%; gout ~4% (men ~3x);
                  kidney stones ~10% over a life; underactive thyroid ~5% (women ~5x); chronic back pain ~8%
  later life      cancer ~40% over a life; stroke ~1 in 4 from age 25 (GBD 2016); heart attack, often in the 60s;
                  atrial fibrillation ~10% by 80; osteoarthritis ~half of over-65s; osteoporosis fractures in ~1 in 3
                  women over 50; cataracts ~half by 75; enlarged prostate ~half of men at 60; incontinence;
                  Parkinson's ~1% over 60; shingles ~1 in 3 over a life; pneumonia in the oldest
Weight matters to many of these, so he has an `adiposity` (0-1, obese above about 0.6: ~40% of US adults).

The life table (world.py) already contains these diseases, so illness redistributes risk rather than adding it:
the sick carry more of it and the well less, and when he dies the cause is named. Chronic pain and bad sleep raise
the risk of depression and anxiety (mental.py). Its own random generator.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .factors import FactorSet


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def window(y: float, w: tuple) -> float:
    a, b, c, d = w
    if y < a or y > d:
        return 0.0
    if y < b:
        return (y - a) / max(1e-6, b - a)
    if y <= c:
        return 1.0
    return max(0.05, 1 - (y - c) / max(1e-6, d - c))


@dataclass
class Disease:
    key: str
    window: tuple                    # (from, peak start, peak end, to) years
    base: float                      # monthly onset chance at the peak, before risk factors
    male: float = 1.0                # multiplier for men (women 1.0); 0 = only women, -1 = only men
    risk: Callable = lambda p, F, I: 0.0     # log-multiplier from his life
    ends: float = 0.0                # monthly chance it goes away (0 = lifelong); doubled when treated
    sleep: float = 0.0               # what it costs his sleep (0-1)
    pain: float = 0.0                # chronic pain (0-1)
    burden: float = 0.0              # what it takes off his health
    death: float = 1.0               # death-rate multiplier while he has it (untreated)
    fatal: float = 0.0               # chance it kills him within the month it strikes
    silent: bool = False             # often unnoticed until someone checks
    onset: str = ""
    struggles: List[str] = field(default_factory=list)
    acute: bool = False              # an event, not a condition (it passes within the month)
    once: bool = False


def _bmi(p) -> float:
    return p.s.get("adiposity", 0.3)


def _smoked(p) -> float:
    """1 for a current smoker, about half that for a former one (most excess risk fades over 10-20 years)."""
    h = getattr(p, "hardships", None)
    return 0.0 if h is None else 1.0 if h.smoker else 0.4 if h.ever_smoked else 0.0


def _has(I, *keys) -> bool:
    return any(k in I.active for k in keys)


D: List[Disease] = [
    # --- childhood ---------------------------------------------------------------------------------------------------
    Disease("asthma", (0.5, 2, 10, 50), 0.00025, 1.3,
            lambda p, F, I: 1.2 * (1 - p.s["microbiome"]) + 1.0 * F["local_pollution"] + 0.6 * p.s["autoimmune_risk"],
            ends=0.006, sleep=0.05, burden=0.04, death=1.05, onset="is diagnosed with asthma",
            struggles=["wheezes through PE and has to sit out", "spends a night in A&E with an asthma attack",
                       "is never without his inhaler"]),
    Disease("eczema", (0, 0.3, 4, 30), 0.0008, 1.0, lambda p, F, I: 1.0 * (1 - p.s["microbiome"]) + 0.5 * p.s["autoimmune_risk"],
            ends=0.02, sleep=0.08, onset="breaks out in eczema",
            struggles=["scratches until his skin bleeds in his sleep", "has to wear cotton gloves to bed"]),
    Disease("food allergy", (0, 0.5, 3, 8), 0.0008, 1.2, lambda p, F, I: 0.8 * (1 - p.s["microbiome"]),
            ends=0.002, onset="has a frightening allergic reaction and is found to have a food allergy",
            struggles=["checks every label at the shop", "carries an adrenaline pen everywhere",
                       "has to ask about every ingredient at a friend's birthday party"]),
    Disease("type 1 diabetes", (1, 4, 14, 40), 0.000035, 1.1, burden=0.06, death=1.6,
            onset="is rushed to hospital and diagnosed with type 1 diabetes",
            struggles=["pricks his finger before every meal", "has a hypo in the middle of class",
                       "counts the carbohydrates in everything he eats"]),
    Disease("epilepsy", (0, 1, 80, 95), 0.00001, 1.2, lambda p, F, I: 0.6 * F["genetic_risk"], ends=0.002, burden=0.05,
            death=1.6, onset="has a seizure and is diagnosed with epilepsy",
            struggles=["has a seizure in front of everyone", "is not allowed to drive until he has gone a year without a seizure"]),
    Disease("childhood cancer", (1, 2, 6, 19), 0.00003, 1.2, ends=0.06, burden=0.3, death=8.0,
            onset="is diagnosed with leukaemia",
            struggles=["loses his hair to chemotherapy", "spends months on the children's ward",
                       "watches his parents pretend not to be scared"]),
    # --- teens and twenties ------------------------------------------------------------------------------------------
    Disease("migraine", (9, 20, 45, 75), 0.0006, 0.35, lambda p, F, I: 0.8 * p.s["allostatic_load"] + 0.5 * (1 - p.s["sleep"]),
            ends=0.004, pain=0.25, sleep=0.03, onset="gets his first migraine",
            struggles=["lies in a dark room with a migraine for a whole day", "misses work with a migraine",
                       "sees flashing zigzags and knows what is coming"]),
    Disease("IBS", (14, 20, 45, 70), 0.00018, 0.6, lambda p, F, I: 1.2 * p.s["anxiety"] + 0.5 * p.s["allostatic_load"],
            ends=0.004, pain=0.15, onset="is told his stomach problems are irritable bowel syndrome",
            struggles=["plans every trip around where the toilets are", "cancels plans because his stomach is bad"]),
    Disease("Crohn's disease", (14, 20, 35, 70), 0.00003, 1.0, lambda p, F, I: 0.6 * p.s["autoimmune_risk"],
            pain=0.3, burden=0.1, death=1.3, onset="is diagnosed with Crohn's disease after months of pain",
            struggles=["has a flare and cannot leave the house", "goes into hospital for surgery on his bowel"]),
    Disease("endometriosis", (13, 18, 40, 50), 0.0004, 0.0, ends=0.002, pain=0.35, sleep=0.03,
            onset="is finally diagnosed with endometriosis, years after the pain began",
            struggles=["is doubled over with period pain and told it is normal", "misses days of work every month"]),
    Disease("PCOS", (13, 15, 30, 40), 0.0005, 0.0, lambda p, F, I: 1.5 * (_bmi(p) - 0.4), onset="is told she has polycystic ovaries",
            struggles=["has irregular periods and worries about having children"]),
    Disease("chlamydia", (15, 18, 26, 40), 0.0006, 1.0, lambda p, F, I: 1.0 * p.s["peer_risk"], acute=True,
            onset="tests positive for chlamydia and has to tell his last partner"),
    # --- adult conditions --------------------------------------------------------------------------------------------
    Disease("insomnia", (14, 30, 90, 100), 0.0003, 0.7,
            lambda p, F, I: 1.5 * p.s["anxiety"] + 1.0 * p.s.get("grief", 0) + 1.2 * F["shift_work"] * p.s["employed"]
            + 1.0 * _has(p.mind, "depression", "anxiety", "PTSD") + 0.8 * I.pain_now + 0.6 * p.s.get("cortisol", 0.3),
            ends=0.04, sleep=0.35, onset="cannot sleep any more: weeks of lying awake become months",
            struggles=["lies awake until 4 am watching the clock", "dreads going to bed",
                       "drags himself through the day on four hours of sleep"]),
    Disease("sleep apnoea", (20, 40, 90, 100), 0.0002, 2.5,
            lambda p, F, I: 2.0 * (_bmi(p) - 0.4) + 0.4 * (p.s["inflammation"]), sleep=0.3, burden=0.04, death=1.3,
            silent=True, onset="is found to stop breathing dozens of times a night: obstructive sleep apnoea",
            struggles=["snores so loudly his partner sleeps in the spare room", "nods off at the wheel at a red light",
                       "wakes gasping for air", "puts on the CPAP mask and hates it"]),
    Disease("chronic back pain", (20, 35, 90, 100), 0.0006, 1.0,
            lambda p, F, I: 1.2 * (_bmi(p) - 0.4) + 0.8 * (1 - p.s["motor"]) + 0.5 * p.s["allostatic_load"],
            ends=0.01, pain=0.35, sleep=0.05, onset="hurts his back lifting a box, and it never quite gets better",
            struggles=["can't sit through a film without shifting", "puts his socks on lying down"]),
    Disease("high blood pressure", (18, 35, 90, 100), 0.0009, 1.3,
            lambda p, F, I: 2.0 * (_bmi(p) - 0.4) + 1.2 * p.s["allostatic_load"] + 0.04 * (p.years - 45)
            + 0.6 * _has(I, "sleep apnoea") + 0.5 * p.s["insulin_resistance"],
            burden=0.02, death=1.25, silent=True, onset="is told at a routine check that his blood pressure is high",
            struggles=["takes his blood-pressure pill every morning"]),
    Disease("type 2 diabetes", (25, 45, 90, 100), 0.0012, 1.2,
            lambda p, F, I: 4.0 * (p.s["insulin_resistance"] - 0.4) + 1.5 * (_bmi(p) - 0.45),
            burden=0.08, death=1.3, silent=True, onset="is diagnosed with type 2 diabetes",
            struggles=["learns to count carbohydrates at 50", "has a foot wound that will not heal",
                       "notices his eyesight blurring: diabetic eye disease"]),
    Disease("reflux", (20, 35, 90, 100), 0.0007, 1.0, lambda p, F, I: 2.0 * (_bmi(p) - 0.4) + 0.5 * p.s["allostatic_load"],
            ends=0.01, sleep=0.04, onset="gets heartburn every night",
            struggles=["sleeps propped up on three pillows because of heartburn"]),
    Disease("gout", (30, 45, 90, 100), 5e-05, 3.0, lambda p, F, I: 2.0 * (_bmi(p) - 0.4) + 0.8 * _has(p.mind, "alcohol use"),
            pain=0.1, onset="wakes with his big toe on fire: gout",
            struggles=["cannot bear even a bedsheet touching his foot"]),
    Disease("kidney stone", (20, 35, 65, 90), 0.00016, 1.5, lambda p, F, I: 1.0 * (_bmi(p) - 0.4), acute=True,
            onset="has the worst pain of his life: a kidney stone"),
    Disease("underactive thyroid", (25, 40, 90, 100), 7e-05, 0.2, lambda p, F, I: 0.5 * p.s["autoimmune_risk"],
            burden=0.03, onset="is exhausted for a year before a blood test finds an underactive thyroid",
            struggles=["takes his thyroid pill on an empty stomach every morning"]),
    Disease("tinnitus", (25, 50, 90, 100), 0.0003, 1.3, ends=0.004, sleep=0.04,
            onset="hears a ringing in his ears that never stops", struggles=["needs a fan on to fall asleep over the ringing"]),
    # --- later life --------------------------------------------------------------------------------------------------
    Disease("cancer", (20, 85, 100, 100), 0.0019, 1.1,
            lambda p, F, I: 0.055 * (p.years - 70) + 0.6 * p.s["inflammation"] + 0.5 * _has(p.mind, "alcohol use")
            + 0.6 * _smoked(p)
            + 0.4 * p.s["methylation_risk"] + 0.4 * (_bmi(p) - 0.45),
            ends=0.05, pain=0.2, burden=0.3, death=12.0, onset="is diagnosed with cancer",
            struggles=["waits three weeks for scan results", "loses his hair to chemotherapy",
                       "rings the bell on his last day of treatment", "is too tired to get off the sofa after radiotherapy"]),
    Disease("heart attack", (30, 75, 100, 100), 0.0001, 2.0,
            lambda p, F, I: 0.05 * (p.years - 65) + 0.8 * _has(I, "high blood pressure") + 0.8 * _has(I, "type 2 diabetes")
            + 1.0 * p.s["allostatic_load"] + 1.0 * (1 - p.s["cardio"]) + 1.0 * (_bmi(p) - 0.45) + 0.6 * _smoked(p),
            fatal=0.12, acute=True, onset="has a heart attack"),
    Disease("heart disease", (35, 60, 100, 100), 0.0, 1.0, burden=0.12, death=1.6, onset="",
            struggles=["goes to cardiac rehab with men twice his age", "feels every twinge in his chest and wonders",
                       "takes five pills a day for his heart"]),
    Disease("stroke", (25, 70, 100, 100), 0.0003, 1.0,
            lambda p, F, I: 0.06 * (p.years - 75) + 1.2 * _has(I, "high blood pressure") + 1.2 * _has(I, "atrial fibrillation")
            + 0.6 * _has(I, "type 2 diabetes") + 0.8 * p.s["allostatic_load"],
            fatal=0.1, acute=True, onset="has a stroke"),
    Disease("stroke damage", (25, 60, 100, 100), 0.0, 1.0, burden=0.2, death=1.3, onset="",
            struggles=["relearns how to speak, one word at a time", "has a hand that will not do what he tells it",
                       "can no longer manage the stairs"]),
    Disease("atrial fibrillation", (50, 70, 100, 100), 0.0006, 1.4,
            lambda p, F, I: 0.04 * (p.years - 75) + 0.8 * _has(I, "high blood pressure") + 0.8 * (_bmi(p) - 0.4)
            + 0.6 * _has(p.mind, "alcohol use"), death=1.3, silent=True, onset="feels his heart flutter out of rhythm: atrial fibrillation",
            struggles=["takes blood thinners and bruises at the slightest knock"]),
    Disease("COPD", (40, 60, 100, 100), 0.00015, 1.2,
            lambda p, F, I: 1.2 * F["local_pollution"] + 0.8 * (0.5 - F["ses"]) + 2.2 * _smoked(p) - 0.6,
            burden=0.12, death=1.6, sleep=0.05, onset="is told his lungs are damaged: COPD",
            struggles=["has to stop halfway up the stairs to breathe", "carries oxygen to the shops"]),
    Disease("osteoarthritis", (40, 60, 100, 100), 0.0018, 0.8,
            lambda p, F, I: 2.0 * (_bmi(p) - 0.4) + 0.6 * (1 - p.s["motor"]),
            pain=0.3, sleep=0.04, onset="is told the pain in his knees is arthritis",
            struggles=["takes the stairs one at a time", "has a hip replacement and walks again without pain",
                       "can't open jars any more"]),
    Disease("osteoporosis", (45, 60, 100, 100), 0.0011, 0.2, lambda p, F, I: 6.0 * (0.55 - p.s.get("bone_density", 0.6)) - 1.0 * (_bmi(p) - 0.4),
            burden=0.04, silent=True, onset="breaks a wrist in a small fall: osteoporosis",
            struggles=["is frightened of icy pavements", "loses an inch of height"]),
    Disease("cataracts", (50, 70, 100, 100), 0.0028, 1.0, lambda p, F, I: 0.8 * _has(I, "type 2 diabetes"), ends=0.03,
            onset="finds the world going misty: cataracts", struggles=["can't drive at night because of the glare"]),
    Disease("macular degeneration", (55, 75, 100, 100), 0.0004, 0.9, burden=0.04,
            onset="loses the centre of his vision: macular degeneration",
            struggles=["can no longer read faces or the newspaper"]),
    Disease("enlarged prostate", (40, 60, 100, 100), 0.003, -1, sleep=0.06,
            onset="is up three times a night to pee: an enlarged prostate",
            struggles=["plans car journeys around service stations"]),
    Disease("incontinence", (50, 70, 100, 100), 0.0011, 0.5, lambda p, F, I: 1.0 * (_bmi(p) - 0.4),
            onset="starts leaking when he coughs or laughs", struggles=["stops going on long walks in case he can't find a toilet"]),
    Disease("Parkinson's disease", (50, 70, 90, 100), 0.00006, 1.5, lambda p, F, I: 1.0 * p.s["neurodegeneration"],
            burden=0.15, death=1.8, onset="notices a tremor in his hand that will not stop: Parkinson's",
            struggles=["takes ten minutes to do up a shirt", "freezes in doorways", "shuffles where he used to stride"]),
    Disease("shingles", (40, 60, 100, 100), 0.0006, 1.0, acute=True, onset="gets shingles: a burning rash for weeks"),
    Disease("pneumonia", (65, 85, 100, 100), 0.002, 1.2, lambda p, F, I: 1.5 * (1 - p.s["health"]) + 1.0 * _has(I, "COPD"),
            fatal=0.08, acute=True, onset="is taken into hospital with pneumonia"),
    # --- the common things, at their ages ----------------------------------------------------------------------------
    Disease("ear infection", (0, 0.5, 5, 9), 0.03, 1.1, acute=True, onset="has an ear infection and screams all night"),
    Disease("chickenpox", (1, 2, 8, 14), 0.01, 1.0, lambda p, F, I: -1.5 * F["healthcare_access"], acute=True, once=True,
            onset="gets chickenpox and is covered in spots"),
    Disease("tonsillitis", (3, 5, 20, 30), 0.0025, 1.0, acute=True, onset="has tonsillitis and cannot swallow"),
    Disease("stomach bug", (0, 1, 90, 100), 0.008, 1.0, acute=True, onset="is up all night with a stomach bug"),
    Disease("glandular fever", (14, 16, 24, 30), 0.0015, 1.0, acute=True, once=True,
            onset="gets glandular fever and is wiped out for a month"),
    Disease("dental", (4, 10, 90, 100), 0.004, 1.0, acute=True, onset="needs a filling",),
]
BY = {d.key: d for d in D}
FOLLOWS = {"heart attack": "heart disease", "stroke": "stroke damage"}
LINES = {"insomnia": "I can't remember the last time I slept properly.",
         "sleep apnoea": "I'm tired all the time, no matter how long I sleep.",
         "chronic back pain": "My back hurts every single day.", "osteoarthritis": "Everything aches when I get up.",
         "migraine": "I'm scared of the next migraine.", "cancer": "I'm scared of what the next scan will say.",
         "heart disease": "Every twinge in my chest frightens me.", "stroke damage": "My body won't do what I tell it.",
         "type 2 diabetes": "I have to think about everything I eat now.", "COPD": "I can't get my breath.",
         "Parkinson's disease": "My hands won't stay still.", "endometriosis": "The pain comes back every month."}


class Illness:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 4421 + 89)
        self.active: Dict[str, int] = {}          # condition -> month it began
        self.known: Dict[str, bool] = {}          # diagnosed (silent ones often are not)
        self.history: List[list] = []             # [condition, from years, to years or None]
        self.done: set = set()
        self.pain_now = 0.0
        self.sleep_now = 0.0
        self.burden_now = 0.0
        self.fatal: Optional[str] = None          # set when something kills him this month
        self.recent: List[list] = []

    # ------------------------------------------------------------------ what others read
    def sleep_cost(self) -> float:
        return self.sleep_now

    def burden(self) -> float:
        return self.burden_now

    def hazard(self) -> float:
        h = 1.0
        for c in self.active:
            d = BY[c]
            h *= 1 + (d.death - 1) * (0.6 if self.known.get(c) else 1.0)     # treatment softens it
        return h

    def cause(self) -> Optional[str]:
        if self.fatal:
            return self.fatal
        worst = max(self.active, key=lambda c: BY[c].death, default=None)
        return worst if worst and BY[worst].death >= 1.4 else None

    def line(self) -> str:
        for c in sorted(self.active, key=lambda c: -(BY[c].pain + BY[c].sleep + BY[c].burden)):
            if c in LINES and self.known.get(c, True):
                return LINES[c]
        return ""

    def to_json(self, p) -> dict:
        return {"active": [{"condition": c, "since_years": round(m / 12, 1), "diagnosed": self.known.get(c, False)}
                           for c, m in sorted(self.active.items(), key=lambda t: t[1])],
                "history": self.history[-10:], "recent": self.recent[-8:], "pain": round(self.pain_now, 3),
                "sleep_cost": round(self.sleep_now, 3), "adiposity": round(p.s.get("adiposity", 0), 3),
                "obese": p.s.get("adiposity", 0) > 0.6}

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        self.fatal = None
        male = F["sex"] >= 0.5
        self._weight(p, F)
        for d in D:
            if d.base <= 0 or (d.once and d.key in self.done) or d.key in self.active:
                continue
            if (d.male == 0 and male) or (d.male == -1 and not male):
                continue
            w = window(y, d.window)
            if w == 0:
                continue
            sexm = d.male if (male and d.male > 0) else 1.0
            h = d.base * w * sexm * math.exp(max(-4.0, min(3.0, d.risk(p, F, self))))
            if r.random() >= h:
                continue
            self.done.add(d.key)
            if d.acute:
                text = d.onset
                if d.fatal and r.random() < d.fatal * (0.5 + y / 80) * (1.3 - 0.6 * F["healthcare_access"]):
                    self.fatal = d.key
                    self._say(p, f"{text}, and does not survive it", -1.0, out)
                    return out
                self._say(p, text + ("; he survives" if d.fatal else ""), -0.6, out)
                if d.key in FOLLOWS:
                    self._begin(p, FOLLOWS[d.key], m, True)
                continue
            self._begin(p, d.key, m, not d.silent or r.random() < 0.3 * F["healthcare_access"])
            if self.known[d.key]:
                self._say(p, d.onset, -0.5, out)
        # --- living with it ------------------------------------------------------------------------------------------
        pain = sleep = burden = 0.0
        for c in list(self.active):
            d = BY[c]
            if not self.known[c] and r.random() < (0.025 if d.silent else 0.15) * F["healthcare_access"]:
                self.known[c] = True
                self._say(p, d.onset, -0.4, out)
            treated = self.known[c] and F["healthcare_access"] > 0.25
            soft = 0.6 if treated else 1.0
            pain += d.pain * soft
            sleep += d.sleep * soft
            burden += d.burden * soft
            if d.struggles and r.random() < 0.04:
                self._say(p, r.choice(d.struggles), -0.3, out)
            if d.ends and r.random() < d.ends * (2.0 if treated else 1.0):
                began = self.active.pop(c)
                self.history.append([c, round(began / 12, 1), round(m / 12, 1)])
                self._say(p, {"cancer": "is told he is in remission", "childhood cancer": "finishes treatment and is cancer-free",
                              "cataracts": "has cataract surgery and sees colour again"}.get(c, f"is free of his {c}"),
                          0.6, out)
        self.pain_now, self.sleep_now, self.burden_now = clip(pain), clip(sleep), clip(burden)
        if self.pain_now > 0.2:
            p.apply({"anxiety": 0.004 * self.pain_now, "allostatic_load": 0.002 * self.pain_now}, fades=True)
            s["motor"] = clip(s["motor"] - 0.002 * self.pain_now)
        if "stroke damage" in self.active or "Parkinson's disease" in self.active:
            s["autonomy"] = clip(s["autonomy"] - 0.004)
        return out

    def _begin(self, p, key: str, month: int, known: bool) -> None:
        self.active[key] = month
        self.known[key] = known

    def _say(self, p, text: str, valence: float, out: List[dict]) -> None:
        self.recent.append([round(p.years, 1), text])
        self.recent = self.recent[-20:]
        out.append({"text": text, "valence": valence, "arousal": 0.4 + 0.4 * abs(valence), "who": [], "key": "illness",
                    "deltas": {}})

    def _weight(self, p, F: FactorSet) -> None:
        """Adiposity: inborn metabolism, activity, screens, money, midlife, low mood. ~20% of children and ~40% of
        US adults are above the obesity line (0.6 here)."""
        s, y = p.s, p.years
        mid = math.exp(-((y - 55) / 18) ** 2)
        dep = 1.0 if "depression" in p.mind.active else 0.0
        target = (0.45 + 0.08 * clip((y - 12) / 30) + 0.3 * (p.metabolic - 1) + 0.12 * (0.6 - s["cardio"])
                  + 0.08 * F["screen_time"]
                  + 0.12 * (0.5 - F["ses"]) + 0.05 * mid * (y >= 20) - 0.08 * clip((y - 72) / 15) + 0.06 * dep + 0.05 * (self.sleep_now > 0.2)
                  - 0.12 * ("cancer" in self.active))
        rate = 0.01 if y >= 2 else 0.05
        s["adiposity"] = round(clip(s.get("adiposity", 0.3) + rate * (clip(target) - s.get("adiposity", 0.3))), 4)


# Average disease multiplier in the population by age (measured over simulated lives), so that naming diseases moves
# risk onto the sick without changing how long people live on average.
NORM = [(0, 1.0), (25, 1.03), (45, 1.24), (55, 1.43), (65, 1.7), (75, 2.12), (85, 2.23), (95, 1.9), (105, 1.7)]


def mortality_norm(y: float) -> float:
    for (a, x), (b, z) in zip(NORM, NORM[1:]):
        if a <= y < b:
            return x + (z - x) * (y - a) / (b - a)
    return NORM[-1][1]
