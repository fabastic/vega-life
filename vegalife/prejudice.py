"""Stereotypes and prejudice: what he faces for who he is, and what he picks up and may act out himself.

Facing it. Who he is decides what comes at him, and how prejudiced the society around him is decides how often:
  ethnicity     field experiments: white US applicants get ~36% more callbacks than Black and ~24% more than Latino
                applicants with the same CV, unchanged since 1989 (Quillian et al. 2017); discrimination against
                non-white natives appears in all nine countries studied (Quillian et al. 2019)
  migrant       accent and "where are you really from"; a family that often pushes education hard
  sexuality     comes out in his late teens or twenties, or stays closeted where it is dangerous; acceptance
                varies hugely by region (Pew global attitudes)
  sex           being talked over, paid less, harassed (for a woman); for a man, "boys don't cry" makes asking
                for help harder (mental.py: men seek treatment less)
  class         teased for being poor, told "people like you" do not go to university
  weight, age,  mocked for weight; passed over as "not a culture fit" or for "fresh energy" after 50; called
  neurodivergence  "weird" for being autistic
Each incident adds stress: perceived discrimination is reliably linked to worse mental health (r about -0.2) and
physical health (Pascoe & Richman 2009, 134 studies). Hiring bias cuts his chance of being called back.

Absorbing it. Prejudice is learned: from a strict or closed home, a prejudiced society, a hardening identity and
outrage-ranked feeds. It is unlearned through contact: friends from other backgrounds reduce prejudice
(Pettigrew & Tropp 2006, 515 studies: r about -0.21; smaller in pre-registered trials), and through openness and
education. When his own bias is high he sometimes acts on it (a joke at someone's expense, an assumption about a
colleague), and his conscience may catch it. When it is low he sometimes stands up for someone.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .factors import FactorSet

ACCEPT = {"North America": 0.75, "Latin America": 0.6, "Western Europe": 0.85, "Nordic countries": 0.9,
          "Eastern Europe": 0.35, "Middle East and North Africa": 0.15, "Sub-Saharan Africa": 0.2, "South Asia": 0.3,
          "East Asia": 0.45, "Southeast Asia": 0.4, "Oceania": 0.8}
FACED = {
    "ethnicity": {"school": ["a classmate makes a joke about where his family is from",
                             "a teacher expects less of him than of the others"],
                  "street": ["a security guard follows him around a shop", "a stranger tells him to go back where he came from"],
                  "work": ["is passed over for an interview that goes to someone with a local-sounding name",
                           "is asked where he is really from at a job interview"],
                  "online": ["gets a stream of hateful replies about his background"]},
    "migrant": {"school": ["kids mock his accent", "a teacher assumes he cannot keep up in the language"],
                "street": ["someone mimics his accent back at him"],
                "work": ["is told his qualifications from abroad do not count"], "online": []},
    "sexuality": {"school": ["hears 'gay' used as an insult every day at school"],
                  "street": ["is shouted at in the street for holding his partner's hand"],
                  "work": ["hides who he is at work after hearing colleagues' jokes"],
                  "online": ["gets abuse online after posting a photo with his partner"]},
    "sex": {"school": ["is told maths and engineering are not really for girls"],
            "street": ["is followed and commented on by a stranger on the way home"],
            "work": ["is talked over in meetings and paid less than a colleague doing the same job"], "online": []},
    "class": {"school": ["is teased about his second-hand clothes", "is told people from his area do not go to university"],
              "street": [], "work": ["is told he does not have the right 'polish' for client work"], "online": []},
    "weight": {"school": ["is mocked about his weight in PE"], "street": ["a stranger comments on his body"],
               "work": ["is passed over for a client-facing role because of how he looks"], "online": []},
    "neurodivergence": {"school": ["is called weird for how he talks", "is left out of group work"],
                        "street": [], "work": ["is told he is not a 'culture fit' after an interview"], "online": []},
    "age": {"school": [], "street": [], "work": ["is told the role needs 'fresh energy' and loses out to someone younger"],
            "online": []},
    "disability": {"school": ["is left out of a school trip because 'it isn't accessible'"],
                   "street": ["is spoken over to the person pushing his wheelchair", "can't get into a shop with a step"],
                   "work": ["is turned down after the interviewer sees the wheelchair"], "online": []},
}
ACTS = ["laugh at a joke about a classmate's accent", "mock the new kid for how they dress",
        "laugh at a joke about a colleague's background", "mock a colleague he assumes got the job to fill a quota"]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Prejudice:
    def __init__(self, F: FactorSet, seed: int, region: str = "North America"):
        self.rng = random.Random(seed * 6379 + 71)
        r = self.rng
        self.region = region
        self.accept = ACCEPT.get(region, 0.5)
        self.queer = r.random() < 0.1
        self.out_at = int(12 * clip(r.gauss(18 + 6 * (1 - self.accept), 3), 13, 45)) if self.queer else None
        self.out = False
        self.closeted = False
        self.bias = 0.0
        self.faced: Dict[str, int] = {}
        self.recent: List[str] = []
        self.acted = 0
        self.stood_up = 0

    def callback(self, F: FactorSet) -> float:
        """How much hiring bias cuts his chance of a callback (1 = none)."""
        c = F["prejudice_climate"] / 0.4
        cut = 0.27 * (F["minority_status"] >= 1) + 0.12 * (F["minority_status"] == 0.5) + 0.1 * (F["migrant_background"] >= 1)
        return clip(1 - cut * c, 0.4, 1.0)

    def to_json(self) -> dict:
        return {"faced": self.faced, "recent": self.recent[-6:], "bias": round(self.bias, 3), "acted_on_bias": self.acted,
                "stood_up": self.stood_up, "out": self.out, "closeted": self.closeted}

    def line(self) -> str:
        if self.recent and self.rng.random() < 0.4:
            return "Some people decide who I am before I say a word."
        if self.closeted:
            return "I cannot tell anyone who I really am here."
        return ""

    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        if y < 5:
            return out
        online = getattr(p, "online", None)
        # --- what he absorbs, and what unlearns it -----------------------------------------------------------------
        diverse = F["friend_diversity"] + 0.3 * (F["minority_status"] > 0)
        target = clip(0.12 + 0.35 * F["prejudice_climate"] + 0.2 * F["cultural_strictness"] + 0.3 * s["identity_rigidity"]
                      + 0.3 * (online.outrage if online else 0.0) - 0.3 * diverse - 0.2 * (s["openness"] - 0.5)
                      - 0.1 * s["credential"] - 0.15 * (F["minority_status"] > 0))
        self.bias += 0.008 * (target - self.bias)
        # --- coming out ----------------------------------------------------------------------------------------------
        if self.queer and not self.out and self.out_at is not None and m >= self.out_at:
            if r.random() < 0.3 + 0.7 * self.accept:
                self.out, self.closeted = True, False
                strict = F["cultural_strictness"] * (1 - self.accept)
                rejected = r.random() < 0.15 + 0.6 * strict
                if rejected:
                    for b in getattr(p, "bonds").bonds.values():
                        if b.relation in ("mother", "father"):
                            b.conflict, b.trust = clip(b.conflict + 0.35), clip(b.trust - 0.25)
                    d = {"anxiety": 0.1, "household_friction": 0.2}
                    out.append({"text": "comes out to his family, and they do not take it well", "valence": -0.6,
                                "arousal": 0.9, "who": [], "key": "out", "deltas": d})
                else:
                    d = {"anxiety": -0.06}
                    out.append({"text": "comes out to his family, and they hug him", "valence": 0.8, "arousal": 0.9,
                                "who": [], "key": "out", "deltas": d})
                p.apply(d, fades=True)
            else:
                self.closeted = True
                self.out_at = m + 12 * r.randint(3, 10)              # maybe later, maybe somewhere safer
        if self.closeted:
            s["allostatic_load"] = clip(s["allostatic_load"] + 0.001)
        # --- what he faces ---------------------------------------------------------------------------------------------
        mind = getattr(p, "mind", None)
        who = {"ethnicity": 1.0 * (F["minority_status"] >= 1) + 0.5 * (F["minority_status"] == 0.5),
               "migrant": 0.7 * (F["migrant_background"] >= 1) + 0.3 * (F["migrant_background"] == 0.5),
               "sexuality": 0.8 * (1 - self.accept) * (self.out and y >= 12),
               "sex": 0.5 * (F["sex"] < 0.5) * (y >= 10),
               "class": 0.6 * max(0.0, 0.45 - F["ses"]) * 2 * (y < 30),
               "weight": 0.4 * (s["insulin_resistance"] > 0.45 or s["cardio"] < 0.35),
               "neurodivergence": 0.5 * bool(mind and mind.autism),
               "age": 0.6 * (52 <= y < 66) * (s["employed"] < 0.5 or r.random() < 0.3),
               "disability": 0.8 * getattr(getattr(p, "hardships", None), "disabled", False)}
        total = sum(who.values())
        if total and r.random() < 0.035 * total * (F["prejudice_climate"] / 0.4) * (1 - 0.3 * s["community_support"]):
            kinds = [k for k, v in who.items() if v > 0]
            kind = r.choices(kinds, [who[k] for k in kinds])[0]
            settings = [st for st, opts in FACED[kind].items() if opts and (
                (st == "school" and 5 <= y < 19) or (st == "work" and 18 <= y < 70)
                or (st == "online" and online and online.has_phone) or st == "street")]
            if settings:
                st = r.choice(settings)
                text = r.choice(FACED[kind][st])
                self.faced[kind] = self.faced.get(kind, 0) + 1
                self.recent.append(text)
                d = {"anxiety": 0.04, "allostatic_load": 0.01}
                if st == "school":
                    d["school_belonging"] = -0.04
                p.apply(d, fades=True)
                out.append({"text": text, "valence": -0.6, "arousal": 0.6, "who": [], "key": "prejudice", "deltas": d})
        # --- what he does with his own bias ------------------------------------------------------------------------------
        if y >= 8:
            if self.bias > 0.3 and r.random() < 0.02 * self.bias:
                act = r.choice(ACTS[:2] if y < 19 else ACTS[2:])
                self.acted += 1
                p.conscious.after(p, F, act)
                out.append({"text": f"chooses to {act}", "valence": -0.1, "arousal": 0.3, "who": [], "key": "bias",
                            "deltas": {}})
                if p.conscious.guilt > 0.3 and r.random() < 0.3 + 0.4 * s["openness"]:
                    self.bias = clip(self.bias - 0.1)
                    out.append({"text": "realises the joke hurt someone, and it stays with him", "valence": -0.2,
                                "arousal": 0.4, "who": [], "key": "bias", "deltas": {}})
            elif self.bias < 0.2 and r.random() < 0.006 * F["prejudice_climate"] * (0.5 + p.conscious.moral_sense(p, F)):
                self.stood_up += 1
                p.conscious.after(p, F, "stand up for someone being picked on")
                out.append({"text": "stands up for someone being picked on for who they are", "valence": 0.5,
                            "arousal": 0.6, "who": [], "key": "stood_up", "deltas": {}})
        return out
