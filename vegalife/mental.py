"""Mental health: his own, and that of the people around him.

Two kinds of condition:

  how he is wired (from birth; present whether or not anyone notices)
    autism   ~1 in 31 US 8-year-olds identified (CDC ADDM 2025), boys ~3.4x girls; girls and poorer children are
             diagnosed later or never. Social life is harder work, school belonging and bullying are worse, routine
             and sensory comfort matter, interests run deep (often maths, science, computing). Masking costs energy.
    ADHD     ~11% of US children ever diagnosed (NSCH 2022), ~5-7% truly affected, boys ~2x; it persists into
             adulthood for roughly half. Attention, school results, impulsive choices and phone habits suffer;
             accidents raise the death rate. Diagnosis and support cut the cost.

  episodes (start, last, end, may come back)
    condition      lifetime    typical onset           course and what drives it
    depression     ~20-25%     adolescence to 30s      stress load, loss, loneliness, unemployment, neuroticism,
                                                      a parent with depression; median episode ~6 months; half
                                                      have another; women ~1.7x
    anxiety        ~30%        childhood/adolescence   temperament, an anxious home, stress; often chronic
    PTSD           ~7%         after trauma            ~1 in 10 after a sudden death, disaster or violence
    OCD            ~2-3%       ~14-20                  mostly temperament and genes
    bipolar        ~1-2%       ~18-25                  genes; episodes of mania and depression
    eating disorder ~3% women  adolescence             social comparison (feeds), perfectionism; ~1% men
                   ~1% men
    alcohol use    ~15-25%     late teens to 30s       men ~1.6x, risk-taking friends, stress
    psychosis      ~0.5%       late teens to 30        genes, cannabis, stress; men earlier

Getting help depends on healthcare access and how much stigma there is where he lives (in high-income countries
roughly half of people with depression get any treatment; in low-income ones far fewer; men seek help less).
Treatment roughly doubles how fast an episode ends. Age-of-onset figures follow Solmi et al. 2021 (192 studies:
a third of disorders start before 14, half before 18).

The people around him have their own conditions at similar rates. A parent's depression or drinking makes his
childhood harder and raises his own risk; an autistic brother takes more of his parents' attention; a friend in a
bad patch is someone he can help.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from .factors import FactorSet

# condition: (base first-onset hazard per month, onset window (from, peak start, peak end, to), chance an episode
# ends each month untreated, treated, death-rate multiplier while active, recurrence hazard after the first)
EPISODIC: Dict[str, tuple] = {
    "depression": (0.00006, (11, 15, 35, 90), 0.11, 0.2, 1.5, 0.0012),
    "anxiety": (0.00016, (6, 10, 30, 90), 0.035, 0.09, 1.1, 0.0008),
    "PTSD": (0.0, (4, 4, 90, 95), 0.04, 0.1, 1.3, 0.0),
    "OCD": (0.00005, (8, 12, 25, 50), 0.02, 0.06, 1.1, 0.002),
    "bipolar": (0.00003, (14, 18, 28, 50), 0.15, 0.22, 1.6, 0.02),
    "eating disorder": (0.0001, (11, 13, 22, 35), 0.035, 0.08, 1.5, 0.004),
    "alcohol use": (0.00017, (15, 18, 35, 70), 0.025, 0.07, 1.8, 0.0015),
    "psychosis": (0.00003, (15, 18, 30, 45), 0.05, 0.12, 2.0, 0.01),
}
STIGMA = {"North America": 0.3, "Latin America": 0.5, "Western Europe": 0.3, "Nordic countries": 0.2,
          "Eastern Europe": 0.55, "Middle East and North Africa": 0.7, "Sub-Saharan Africa": 0.7, "South Asia": 0.75,
          "East Asia": 0.6, "Southeast Asia": 0.6, "Oceania": 0.3}
THOUGHT = {"depression": "I feel flat and heavy, and I do not know why.",
           "anxiety": "I cannot stop worrying about everything.",
           "PTSD": "It keeps coming back to me, especially at night.",
           "OCD": "I have to check things again and again.",
           "bipolar": "My moods swing so far I do not recognise myself.",
           "eating disorder": "I keep thinking about what I eat and how I look.",
           "alcohol use": "I have been drinking more than I should.",
           "psychosis": "Things feel strange, like they are not quite real."}
# what a condition does to someone close to him, by who they are
OTHERS_RATE = {"depression": 0.2, "anxiety": 0.18, "alcohol use": 0.12, "bipolar": 0.015, "PTSD": 0.05,
               "eating disorder": 0.02, "OCD": 0.02, "psychosis": 0.005, "ADHD": 0.05, "autism": 0.02}


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
    return max(0.15, 1 - (y - c) / max(1e-6, d - c))


class MentalHealth:
    def __init__(self, F: FactorSet, seed: int, region: str = "North America"):
        self.rng = random.Random(seed * 9241 + 13)
        r = self.rng
        male = F["sex"] >= 0.5
        g = 0.6 + F["genetic_risk"]
        self.autism = r.random() < (1 / 20 if male else 1 / 71) * g
        self.adhd = r.random() < (0.085 if male else 0.042) * g * (1.3 if self.autism else 1.0)
        self.diagnosed: Dict[str, Optional[int]] = {"autism": None, "ADHD": None}
        self.active: Dict[str, int] = {}               # condition -> month the episode began
        self.treated: Dict[str, bool] = {}
        self.had: Dict[str, int] = {}                  # condition -> number of episodes so far
        self.history: List[list] = []                  # [condition, from_years, to_years or None, treated]
        self.stigma = STIGMA.get(region, 0.4)
        self.mania = False
        self.others: Dict[str, dict] = {}
        self.family_history = 0.0                      # parents' depression: his own risk rises
        self.self_harm = False                         # roughly 1 in 6 adolescents self-harm at some point (UK cohorts)

    def begin(self, cond: str, month: int) -> bool:
        """Something in his life tips him into an episode (a father's postnatal depression, a scam's shame)."""
        if cond in self.active:
            return False
        self.active[cond] = month
        self.had[cond] = self.had.get(cond, 0) + 1
        return True

    # ------------------------------------------------------------------ what other modules read
    def focus(self) -> float:
        f = 1.0
        if self.adhd:
            f *= 0.94 if self.diagnosed["ADHD"] is not None else 0.86
        if "depression" in self.active:
            f *= 0.85
        if "anxiety" in self.active or "PTSD" in self.active:
            f *= 0.94
        return f

    def load(self) -> float:
        return clip(0.45 * ("depression" in self.active) + 0.25 * ("anxiety" in self.active)
                    + 0.35 * any(c in self.active for c in ("PTSD", "bipolar", "psychosis", "eating disorder",
                                                            "alcohol use")) + 0.1 * len(self.active))

    def hazard(self) -> float:
        h = 1.0
        for c in self.active:
            h *= EPISODIC[c][4]
        if self.adhd and self.diagnosed["ADHD"] is None:
            h *= 1.25                                     # accidents, mostly
        return h

    def line(self) -> str:
        if self.active:
            c = max(self.active, key=lambda k: EPISODIC[k][4])
            return "I have so much energy, I barely sleep." if c == "bipolar" and self.mania else THOUGHT[c]
        return ""

    def to_json(self, month: int) -> dict:
        return {"autism": self.autism, "adhd": self.adhd, "self_harm": getattr(self, "self_harm", False),
                "diagnosed": {k: None if v is None else round(v / 12, 1) for k, v in self.diagnosed.items()},
                "active": [{"condition": c, "since_years": round(m / 12, 1), "treated": self.treated.get(c, False)}
                           for c, m in self.active.items()],
                "history": self.history[-12:],
                "others": [{"name": n, "relation": o["relation"], "conditions": o["conditions"],
                            "struggling": o["active"]} for n, o in self.others.items() if o["conditions"]]}

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        male = F["sex"] >= 0.5
        out += self._around(p, F)
        # --- how he is wired: noticed or not ---------------------------------------------------------------------
        care = F["healthcare_access"] * (1 - 0.5 * self.stigma)
        for cond, have, start, rate in (("autism", self.autism, 2, 0.025), ("ADHD", self.adhd, 5, 0.012)):
            if have and self.diagnosed[cond] is None and y >= start:
                girl = 0.5 if not male else 1.0
                late = 0.25 if y >= 18 else 1.0
                if r.random() < rate * care * girl * late * (0.5 + F["ses"]):
                    self.diagnosed[cond] = m
                    late_txt = "; a lot of his life finally makes sense" if y >= 18 else ""
                    out.append({"text": f"is diagnosed with {cond} at {int(y)}{late_txt}", "valence": 0.1 if y < 18 else 0.3,
                                "arousal": 0.6, "who": [], "key": "diagnosis", "deltas": {}})
        if self.autism and 4 <= y < 19:
            supported = self.diagnosed["autism"] is not None
            p.apply({"peer_isolation": 0.002 * (0.5 if supported else 1.0), "school_belonging": -0.002,
                     "anxiety": 0.002}, fades=True)
            if not male and not supported:
                s["allostatic_load"] = clip(s["allostatic_load"] + 0.0008)        # masking all day
        if self.adhd and y >= 6:
            s["peer_risk"] = clip(s["peer_risk"] + 0.03 * (self.diagnosed["ADHD"] is None))
        # --- episodes --------------------------------------------------------------------------------------------
        trauma = 0.6 * any(l.month == m and l.sudden and l.weight > 0.7 and l.kind == "death" for l in p.family.losses) \
            + 0.5 * any("hits the neighbourhood" in e for e in p.events) + 0.15 * any("is bullied" in e for e in p.events)
        unemployed = 19 <= y < 66 and s["employed"] < 0.5 and s["schooling"] < 0.5
        online = getattr(p, "online", None)
        compare = online.comparison if online else 0.0
        ill = getattr(p, "illness", None)
        body = (1.2 * ill.pain_now + 0.8 * ("insomnia" in ill.active)) if ill else 0.0   # pain and no sleep wear you down
        body += 3.0 * getattr(getattr(p, "hormones", None), "mood_drag", 0.0)            # PMDD, winter, low testosterone
        for c, (base, win, end_u, end_t, _, recur) in EPISODIC.items():
            if c in self.active:
                treated = self.treated.get(c, False)
                if not treated and r.random() < 0.07 * F["healthcare_access"] * (1 - self.stigma) * (0.7 if male else 1.0):
                    self.treated[c] = True
                    out.append({"text": f"gets help for his {c}", "valence": 0.3, "arousal": 0.4, "who": [],
                                "key": "help", "deltas": {}})
                if c == "bipolar" and r.random() < 0.2:
                    self.mania = not self.mania
                if r.random() < (end_t if self.treated.get(c) else end_u):
                    began = self.active.pop(c)
                    self.history.append([c, round(began / 12, 1), round(m / 12, 1), self.treated.pop(c, False)])
                    out.append({"text": f"comes out of a long {c} episode" if c in ("depression", "bipolar") else
                                f"his {c} eases", "valence": 0.5, "arousal": 0.4, "who": [], "key": "recover",
                                "deltas": {}})
                continue
            if c == "PTSD":
                h = 0.025 * trauma * (0.6 + s["neuroticism"])
            else:
                w = window(y, win)
                if w == 0:
                    continue
                risk = {"depression": 1.6 * (s["neuroticism"] - 0.5) + 2.2 * s["allostatic_load"] + 1.8 * s.get("grief", 0)
                        + 1.2 * s["felt_loneliness"] + 0.6 * unemployed + 0.7 * self.family_history
                        + 0.4 * (not male) + 0.5 * compare + 0.4 * (s.get("cortisol", 0.3) - 0.3) + body,
                        "anxiety": 1.6 * (s["neuroticism"] - 0.5) + 1.5 * s["anxiety"] + 1.0 * s["allostatic_load"]
                        + 0.5 * (not male) + 0.4 * self.autism + 0.4 * compare + 0.6 * body,
                        "eating disorder": 1.2 * compare + 0.8 * s["conscientiousness"] - 1.1 * male,
                        "alcohol use": 1.4 * s["peer_risk"] + 0.5 * male + 1.0 * s["allostatic_load"]
                        + 0.6 * s.get("grief", 0) + 0.5 * self.adhd - 0.6 * F["cultural_strictness"],
                        "psychosis": 0.5 * male + 1.0 * F["genetic_risk"] + 0.6 * s["allostatic_load"]
                        + 1.2 * getattr(getattr(p, "hardships", None), "cannabis", 0.0) * (y < 25),
                        "bipolar": 1.2 * F["genetic_risk"], "OCD": 0.8 * (s["neuroticism"] - 0.5)}.get(c, 0.0)
                h = (recur if self.had.get(c) else base) * w * math.exp(risk)
            if r.random() < h:
                self.active[c] = m
                self.had[c] = self.had.get(c, 0) + 1
                again = " again" if self.had[c] > 1 else ""
                text = {"depression": f"slides into depression{again}", "anxiety": f"develops an anxiety disorder"
                        if not again else "is overwhelmed by anxiety again", "PTSD": "is left with PTSD after what happened",
                        "OCD": "starts having obsessive, checking thoughts he cannot stop",
                        "bipolar": "has his first manic episode" if not again else "has another bipolar episode",
                        "eating disorder": "develops an eating disorder", "alcohol use": "starts drinking too much"
                        if not again else "starts drinking heavily again",
                        "psychosis": "has a psychotic episode"}[c]
                out.append({"text": text, "valence": -0.7, "arousal": 0.6, "who": [], "key": "mental", "deltas": {}})
        # --- self-harm: a way of coping in adolescence, usually hidden, usually alongside low mood ---------------
        if 12 <= y < 25 and not self.self_harm and ("depression" in self.active or "anxiety" in self.active):
            if r.random() < 0.035 * (1.0 if male else 2.0) * (0.6 + s["neuroticism"]):
                self.self_harm = self.self_harmed = True
                pr = "him" if male else "her"
                out.append({"text": f"starts hurting {pr}self in secret to cope with how bad things feel", "valence": -0.8,
                            "arousal": 0.6, "who": [], "key": "mental", "deltas": {}})
        if self.self_harm and r.random() < 0.04 * (0.4 + F["healthcare_access"]):
            self.self_harm = False
            pr = "him" if male else "her"
            out.append({"text": f"is noticed by someone who cares, gets {pr} help, and slowly stops hurting {pr}self",
                        "valence": 0.5, "arousal": 0.5, "who": [], "key": "help", "deltas": {}})
        # --- what being unwell does, this month ----------------------------------------------------------------
        a = self.active
        d: Dict[str, float] = {}
        if "depression" in a or ("bipolar" in a and not self.mania):
            d.update(anxiety=0.01, goal_horizon=-0.01, nihilism=0.004, community_support=-0.004, loneliness=0.006)
            s["mood"] = clip(s["mood"] - 0.12)
            s["sleep"] = clip(s["sleep"] - 0.05)
            for k in ("serotonin", "dopamine", "joy"):
                if k in s:
                    s[k] = clip(s[k] - 0.05)
        if "bipolar" in a and self.mania:
            s["mood"] = clip(s["mood"] + 0.15)
            s["sleep"] = clip(s["sleep"] - 0.1)
            s["wealth"] = clip(s["wealth"] - 0.01)
            s["peer_risk"] = clip(s["peer_risk"] + 0.2)
        if "anxiety" in a or "OCD" in a:
            d.update(anxiety=d.get("anxiety", 0) + 0.02, allostatic_load=0.002)
        if "PTSD" in a:
            d.update(anxiety=d.get("anxiety", 0) + 0.02, allostatic_load=0.003)
            s["sleep"] = clip(s["sleep"] - 0.08)
        if "eating disorder" in a:
            s["health"] = clip(s["health"] - 0.01)
            d.update(anxiety=d.get("anxiety", 0) + 0.01)
        if "alcohol use" in a:
            s["inflammation"] = clip(s["inflammation"] + 0.003)
            s["wealth"] = clip(s["wealth"] - 0.003)
            d.update(household_friction=0.01)
        if "psychosis" in a:
            d.update(social_isolation=0.01, anxiety=d.get("anxiety", 0) + 0.02)
        if a and 19 <= y < 66 and s["employed"] > 0.5 and r.random() < 0.006 * self.load():
            s["employed"] = 0.0
            out.append({"text": "loses his job while he is unwell", "valence": -0.7, "arousal": 0.6, "who": [],
                        "key": "work", "deltas": {}})
        if d:
            p.apply(d, fades=True)
        return out

    # ------------------------------------------------------------------ the people around him
    def _around(self, p, F: FactorSet) -> List[dict]:
        r, m, y, s = self.rng, p.age, p.years, p.s
        out: List[dict] = []
        people = [(x.name, x.relation) for x in p.family.present(m) if x.relation != "pet"]
        if p.circle:
            people += [(f.name, "friend") for f in p.circle.present(m)]
        for name, rel in people:
            if name not in self.others:
                conds = [c for c, rate in OTHERS_RATE.items()
                         if r.random() < rate * (1.6 if rel == "sibling" and c in ("autism", "ADHD")
                                                 and (self.autism or self.adhd) else 1.0)]
                self.others[name] = {"relation": rel, "conditions": conds, "active": None}
                if rel in ("mother", "father") and "depression" in conds:
                    self.family_history = clip(self.family_history + 0.5)
                for c in conds:
                    if c in ("autism", "ADHD") and rel in ("sibling", "child") and y >= 1:
                        out.append({"text": f"his {rel} {name} is {'autistic' if c == 'autism' else 'diagnosed with ADHD'}",
                                    "valence": -0.05, "arousal": 0.4, "who": [name], "key": "family", "deltas": {}})
            o = self.others[name]
            episodic = [c for c in o["conditions"] if c in EPISODIC]
            if o["active"] is None and episodic and r.random() < 0.005:
                o["active"] = r.choice(episodic)
                who = name if rel in ("mother", "father") else f"his {rel} {name}"
                verb = {"depression": "falls into a depression", "anxiety": "is struggling with anxiety",
                        "alcohol use": "is drinking heavily", "bipolar": "has a bipolar episode",
                        "PTSD": "is struggling after a trauma", "eating disorder": "is struggling with an eating disorder",
                        "OCD": "is caught up in obsessive thoughts", "psychosis": "has a psychotic episode"}[o["active"]]
                out.append({"text": f"{who} {verb}", "valence": -0.5, "arousal": 0.5, "who": [name], "key": "their_health",
                            "deltas": {}})
            elif o["active"] and r.random() < 0.08:
                o["active"] = None
            if o["active"]:
                if rel in ("mother", "father") and y < 18:
                    hit = 1.5 if o["active"] == "alcohol use" else 1.0
                    p.apply({"caregiver_attention": -0.01 * hit, "household_friction": 0.006 * hit, "anxiety": 0.003 * hit},
                            fades=True)
                elif rel in ("partner", "friend", "sibling", "child"):
                    p.apply({"anxiety": 0.002, "allostatic_load": 0.0008}, fades=True)
            if rel == "sibling" and "autism" in o["conditions"] and y < 12:
                s["caregiver_attention"] = clip(s["caregiver_attention"] - 0.01)
        return out
