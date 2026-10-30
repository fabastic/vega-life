"""How each of his relationships actually goes: day-to-day warmth and friction, how it goes wrong, how it is mended.

Every person close to him (parents, siblings, partner, children, friends) has a bond with its own trust, conflict
and balance of good to bad moments. What the research says, and how it is used:

  balance      stable couples keep about five positive moments to every negative one in conflict; couples heading
               for divorce fall to about 0.8 to 1 (Gottman). `ratio` tracks this for every bond.
  horsemen     when the balance goes, conflict sours in a typical order: criticism (attacking the person, not the
               problem), defensiveness, contempt (the strongest single predictor of divorce), stonewalling
               (shutting down). Gottman predicted divorce from these with ~85-90% accuracy.
  pursue-      one presses, the other withdraws, each making the other worse; an anxious attachment pursues, an
  withdraw     avoidant one withdraws
  when         parent-child conflict peaks in early adolescence and eases after (Laursen et al. 1998); siblings fight
               most in childhood; couples' satisfaction dips in the first year with a baby and under money stress
  repair       a quick repair after a fight is what lasting couples do: an apology, talking it out, a joke, them
               reaching out, time, or counselling. Rupture followed by repair can leave a bond stronger.
  estrangement about 27% of US adults are estranged from a relative (Pillemer 2020): ~10% from a parent or child,
               ~8% from a sibling. Most rifts follow long contempt and broken trust; many are later mended.
  drift        friendships fade without time together, and end after a falling-out

His side of it comes from who he is: agreeableness, how stressed and unwell he is, his attachment, his conscience.
Bonds feed back: closeness follows how a bond is going (so grief later follows it too), conflict adds stress,
contempt in a partnership can end it, and a mended rift is one of the good moments of a life.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from .factors import FactorSet

STEPS = ["steady", "criticism", "defensiveness", "contempt"]
TOPICS = {
    "mother": ["his curfew", "his phone", "his grades", "his friends", "how he never calls", "his choices"],
    "father": ["his curfew", "his grades", "money", "his future", "politics", "how he never calls"],
    "sibling": ["borrowing things without asking", "who the favourite is", "an old grudge", "looking after their parents"],
    "partner": ["money", "chores", "the kids", "time together", "jealousy", "his work hours", "where to live"],
    "child": ["their curfew", "their phone", "their grades", "their choices", "how they never call"],
    "friend": ["a broken promise", "a joke that went too far", "a secret that got out", "being let down"],
    "grandparent": ["politics", "old-fashioned views"],
}
REPAIRS = {"apology": "apologises to {n} and means it", "talk": "talks it out with {n}",
           "they": "{n} reaches out first and they make up", "time": "lets things cool down with {n}",
           "counselling": "goes to couples counselling with {n}"}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def bump(y: float, a: float, b: float) -> float:
    """1 inside [a, b], easing to 0 two years either side."""
    if a <= y <= b:
        return 1.0
    d = a - y if y < a else y - b
    return max(0.0, 1 - d / 2)


@dataclass
class Bond:
    name: str
    relation: str
    trust: float = 0.7
    conflict: float = 0.1
    ratio: float = 5.0
    pattern: str = "steady"         # steady, criticism, defensiveness, contempt, pursue-withdraw, estranged
    months_bad: int = 0
    ruptures: int = 0
    repairs: int = 0
    estranged_at: Optional[int] = None
    last: str = ""
    fit: float = 1.0                # some people simply clash: how much friction there is between these two
    base: float = 0.6               # how close they were to begin with

    def to_json(self) -> dict:
        return {"name": self.name, "relation": self.relation, "trust": round(self.trust, 2),
                "conflict": round(self.conflict, 2), "ratio": round(self.ratio, 1), "pattern": self.pattern,
                "ruptures": self.ruptures, "repairs": self.repairs, "last": self.last,
                "estranged_years": None if self.estranged_at is None else round(self.estranged_at / 12, 1)}


class Bonds:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 2207 + 53)
        self.bonds: Dict[str, Bond] = {}
        self.recent: Optional[str] = None          # who he last fought with, for his thoughts
        self.recent_at = -99

    def to_json(self) -> List[dict]:
        return [b.to_json() for b in sorted(self.bonds.values(), key=lambda b: (b.pattern == "steady", -b.conflict))]

    def line(self, month: int) -> str:
        est = [b for b in self.bonds.values() if b.pattern == "estranged" and month - (b.estranged_at or 0) > 24]
        if self.recent and month - self.recent_at < 2:
            return f"I am still upset about the fight with {self.recent}."
        if est and self.rng.random() < 0.3:
            return f"I have not spoken to {est[0].name} in years. I think about it more than I say."
        return ""

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        people = [(x, x.relation) for x in p.family.present(m) if x.relation != "pet"]
        if p.circle:
            people += [(f, "friend") for f in p.circle.present(m)]
        if y < 3:
            return out
        mind = getattr(p, "mind", None)
        unwell = mind.load() if mind else 0.0
        irritable = clip(0.35 * s["anxiety"] + 0.3 * s.get("cortisol", 0.3) + 0.3 * unwell + 0.2 * s["allostatic_load"]
                         + 0.25 * (1 - s["agreeableness"]) - 0.1)
        anxious = s["attachment"] < 0.45 and s["neuroticism"] > 0.5
        avoidant = s["attachment"] < 0.45 and not anxious
        moral = p.conscious.moral_sense(p, F)
        felt = 0.0
        for who, rel in people:
            b = self.bonds.get(who.name)
            if b is None:
                b = self.bonds[who.name] = Bond(who.name, rel, trust=clip(0.45 + 0.4 * who.closeness), conflict=0.1,
                                                fit=r.lognormvariate(0.0, 0.7), base=who.closeness)
            if b.pattern == "estranged":
                out += self._estranged(p, b, who)
                continue
            # how much time together, and the friction in it
            home = (rel in ("mother", "father", "sibling") and (y < 19 or s["housing"] < 0.5)) or rel == "partner" \
                or (rel == "child" and m - who.born < 216)
            contact = (1.0 if home else 0.35) * (0.5 + 0.5 * who.closeness)
            if rel == "friend":
                contact = who.closeness * (0.5 if getattr(who, "online", False) else 1.0)
            base = {"mother": 0.12 + 0.3 * bump(y, 12, 16), "father": 0.12 + 0.3 * bump(y, 12, 16),
                    "sibling": 0.3 if y < 12 else 0.1, "grandparent": 0.05, "friend": 0.06,
                    "partner": 0.12 + 0.2 * (p.family.expecting is not None or any(
                        x.relation == "child" and m - x.born < 12 for x in p.family.people)) + 0.15 * (1 - s["wealth"]),
                    "child": 0.08 + 0.25 * bump((m - who.born) / 12 if rel == "child" else 0, 13, 17)}.get(rel, 0.08)
            if rel in ("mother", "father", "grandparent", "sibling"):
                base += 0.25 * s["household_friction"]
            theirs = mind.others.get(who.name, {}).get("active") if mind else None     # they are struggling too
            neg = contact * base * b.fit * (0.6 + irritable) * (1.3 if b.pattern != "steady" else 1.0) \
                * (2.0 if theirs == "alcohol use" else 1.4 if theirs else 1.0)
            pos = contact * (0.35 + 0.4 * who.closeness + 0.2 * s["agreeableness"] - 0.25 * unwell) * (0.6 if b.pattern == "contempt" else 1.0)
            b.ratio += 0.25 * (pos / max(0.02, neg) - b.ratio)
            b.ratio = min(b.ratio, 12.0)
            b.conflict += 0.15 * (neg / max(0.01, pos + neg) - b.conflict)
            if b.pattern == "steady":                       # good months rebuild trust between the rows
                b.trust = clip(b.trust + 0.006 * min(b.ratio, 5) / 5 * (0.9 - b.trust) / 0.9)
            # a fight
            if r.random() < 0.6 * neg:
                b.ruptures += 1
                b.trust = clip(b.trust - 0.03 - 0.05 * (b.pattern == "contempt"))
                topic = r.choice(TOPICS.get(rel, TOPICS["friend"]))
                b.last = f"a row about {topic}"
                self.recent, self.recent_at = who.name, m
                if r.random() < 0.35 or b.pattern != "steady":
                    whom = self._who(rel, who.name)
                    out.append({"text": f"has a row with {whom} about {topic}", "valence": -0.4, "arousal": 0.6,
                                "who": [who.name], "key": "fight", "deltas": {}})
                felt += 0.5
            # the balance tips, and conflict sours in its usual order
            if b.ratio < 2.0 and b.conflict > 0.25:
                b.months_bad += 1
                if b.months_bad % 6 == 0:
                    nxt = "pursue-withdraw" if rel == "partner" and (anxious or avoidant) and b.pattern == "defensiveness" \
                        else STEPS[min(len(STEPS) - 1, STEPS.index(b.pattern) + 1)] if b.pattern in STEPS else b.pattern
                    if nxt != b.pattern:
                        b.pattern = nxt
                        txt = {"criticism": f"he and {who.name} start picking at each other, not the problem",
                               "defensiveness": f"every talk with {who.name} turns into who is to blame",
                               "contempt": f"he and {who.name} start treating each other with contempt",
                               "pursue-withdraw": f"the more {who.name} presses, the more he shuts down"}[nxt]
                        out.append({"text": txt, "valence": -0.5, "arousal": 0.5, "who": [who.name], "key": "bond",
                                    "deltas": {}})
            else:
                b.months_bad = max(0, b.months_bad - 1)
            # repair
            if b.pattern != "steady" or b.conflict > 0.25:
                kind = r.choices(["apology", "talk", "they", "time", "counselling"],
                                 [0.3 * (s["agreeableness"] + moral), 0.3 * s["pfc_maturity"], 0.25, 0.2,
                                  0.4 * (rel == "partner" and b.pattern in ("contempt", "pursue-withdraw"))
                                  * F["healthcare_access"] * (0.3 + s["wealth"])])[0]
                chance = 0.05 * (0.4 + s["agreeableness"] + 0.5 * moral + 0.5 * s["pfc_maturity"]) \
                    * (0.4 if b.pattern == "contempt" else 1.0) * (2.0 if kind == "counselling" else 1.0)
                if r.random() < chance:
                    b.repairs += 1
                    b.conflict *= 0.5
                    b.trust = clip(b.trust + 0.06)
                    b.ratio = max(b.ratio, 3.0)
                    b.months_bad = 0
                    b.pattern = "steady" if kind in ("counselling", "apology") or b.pattern in ("criticism", "steady") \
                        else STEPS[max(0, STEPS.index(b.pattern) - 1)] if b.pattern in STEPS else "defensiveness"
                    b.last = REPAIRS[kind].format(n=who.name)
                    if kind == "apology":
                        p.conscious.after(p, F, f"apologise to {who.name}")
                    if kind != "time":
                        out.append({"text": b.last, "valence": 0.5, "arousal": 0.4, "who": [who.name], "key": "repair",
                                    "deltas": {"oxytocin": 0.08}})
            # endings: estrangement, break-up, falling out
            if rel in ("mother", "father", "sibling", "child") and y >= 18 and b.pattern == "contempt" \
                    and b.trust < 0.35 and r.random() < 0.07:
                b.pattern, b.estranged_at = "estranged", m
                out.append({"text": f"stops speaking to {self._who(rel, who.name)}", "valence": -0.7, "arousal": 0.7,
                            "who": [who.name], "key": "estranged", "deltas": {"loneliness": 0.05}})
                p.apply({"loneliness": 0.05, "anxiety": 0.04}, fades=True)
            elif rel == "partner" and getattr(who, "seeded", True) and b.pattern in ("contempt", "pursue-withdraw") \
                    and b.months_bad >= 12 and r.random() < 0.04:
                who.gone = True
                out.append(p.family._lose(p, who, "breakup", False))
                del self.bonds[who.name]
                continue
            elif rel == "friend" and b.trust < 0.25 and r.random() < 0.05:
                who.left = m
                out.append({"text": f"falls out with {who.name}", "valence": -0.5, "arousal": 0.5, "who": [who.name],
                            "key": "friend", "deltas": {}})
            # closeness follows how the bond is going
            quality = clip(1.2 * b.trust - b.conflict + 0.05 * min(b.ratio, 5))     # 1 for a good bond
            target = b.base * (0.6 + 0.4 * quality)
            who.closeness = clip(who.closeness + 0.01 * (target - who.closeness))
            felt += b.conflict * contact - 0.15 * (b.ratio > 4) * contact
        if felt > 0:
            p.apply({"anxiety": 0.004 * min(felt, 3), "allostatic_load": 0.0015 * min(felt, 3)}, fades=True)
        elif "oxytocin" in s:
            s["oxytocin"] = clip(s["oxytocin"] + 0.01 * min(-felt, 2))
        return out

    def _who(self, rel: str, name: str) -> str:
        return {"mother": f"his mother {name}", "father": f"his father {name}", "sibling": f"his sibling {name}",
                "partner": name, "child": f"his child {name}", "grandparent": f"his grandparent {name}"}.get(rel, name)

    def _estranged(self, p, b: Bond, who) -> List[dict]:
        """No contact. Rifts do mend, more often when someone is old or ill, a baby is born, or enough time passes."""
        r, m = self.rng, p.age
        old = who.age(m) > 75 if hasattr(who, "age") else False
        if r.random() < 0.004 * (1 + 2 * old + 0.5 * p.s["agreeableness"]) * min(1.0, (m - b.estranged_at) / 24):
            yrs = max(1, round((m - b.estranged_at) / 12))
            b.pattern, b.conflict, b.trust, b.ratio, b.estranged_at = "steady", 0.2, 0.45, 3.0, None
            b.repairs += 1
            b.last = "they started talking again"
            return [{"text": f"after {yrs} years of silence, he and {who.name} start talking again", "valence": 0.8,
                     "arousal": 0.8, "who": [who.name], "key": "repair", "deltas": {"oxytocin": 0.15}}]
        return []
