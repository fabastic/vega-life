"""What pushes him from inside (expansion plan 1.5): needs, urges, wants, and where they can lead: crime, revenge
and taking justice into his own hands.

  needs     how unmet each basic need is this month, from his state (after Maslow; Deci & Ryan for autonomy):
            survival (money, housing, health), safety, belonging, esteem, autonomy, meaning. 0 met .. 1 unmet.
  urges     short-lived pulls: thrill (sensation seeking, peaking in adolescence: Steinberg 2008, with puberty ahead
            of the prefrontal cortex), aggression (frustration and testosterone, damped by maturity), and grudge
            (wanting to get even with whoever hurt him or his people; it builds with victimisation and fades slowly).
  wants     what he is after right now, the most unmet need turned into a goal ("money", "to belong", "respect").
  pressure  how much the drives push toward offending this month. It scales the calibrated offending rate in
            hardships.py (it does not add a second crime path), and it sets how often the situations below arise.

Situations (scenarios.py, DRIVE_SCENARIOS): a chance to steal when broke, being provoked, wanting what he cannot
afford, witnessing a crime, the person who hurt someone he loves walking free (vigilantism), and a chance to get
even. Choices that break the law carry a chance of being caught, shown by `police_contact` in the outcome; when he
lives one, after_choice gives him a record and sometimes prison, by the same rules as hardships.py.

New states (world.GROUPS "drives"): thrill, aggression, grudge, police_contact. They are not part of wellbeing.
Ablation: "drives" in the config's ablate list sets pressure to 1 and stops the drive situations.
Its own random generator: it never shifts his world.
"""
from __future__ import annotations

import random
from typing import Dict, List

NEEDS = ("survival", "safety", "belonging", "esteem", "autonomy", "meaning")
WANT = {"survival": "money to live on", "safety": "to feel safe", "belonging": "to belong somewhere",
        "esteem": "respect", "autonomy": "to run his own life", "meaning": "something worth doing"}
VICTIM = {"assault": 0.25, "bullied": 0.12, "cyberbullied": 0.08, "sexual_assault": 0.3, "scam": 0.1, "affair": 0.15,
          "prejudice": 0.06, "bias": 0.04}


def clip(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


class Drives:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 6007 + 13)
        self.off = False
        self.need: Dict[str, float] = {k: 0.0 for k in NEEDS}
        self.want = ""
        self.offences = 0
        self.vigilante = 0
        self.recent: List[list] = []

    def step(self, p, F) -> None:
        s, y = p.s, p.years
        n = self.need
        n["survival"] = clip(1 - 0.5 * s["wealth"] - 0.3 * s["housing"] - 0.2 * s["health"] + 0.3 * s["financial_stress"])
        n["safety"] = clip(0.7 * (1 - F["neighbourhood_safety"]) + 0.4 * s["anxiety"] - 0.2)
        n["belonging"] = clip(0.5 * s["loneliness"] + 0.4 * s["peer_isolation"] + 0.3 * (1 - s["community_support"]))
        n["esteem"] = clip(0.6 * (1 - s["resilience"]) + 0.3 * s["identity_crisis"] + 0.2 * (y >= 18) * (1 - s["employed"]) - 0.1)
        n["autonomy"] = clip(1 - s["autonomy"] - 0.2 * (y < 12))
        n["meaning"] = clip(0.6 * s["nihilism"] + 0.4 * (1 - s["goal_horizon"]))
        top = max(NEEDS, key=n.__getitem__) if y >= 3 else ""
        self.want = WANT[top] if top and n[top] > 0.45 else ""
        # urges
        gap = max(0.0, s["puberty"] - s["pfc_maturity"])
        age_curve = 1.0 if 13 <= y < 25 else 0.5 if 25 <= y < 40 else 0.25
        s["thrill"] = clip(0.85 * s["thrill"] + 0.15 * clip(0.2 + 0.6 * gap + 0.3 * s["openness"] + 0.3 * s["peer_risk"]) * age_curve)
        frustration = 0.4 * n["survival"] + 0.3 * n["esteem"] + 0.3 * s["household_friction"]
        s["aggression"] = clip(0.85 * s["aggression"] + 0.15 * clip(frustration + 0.3 * s.get("testosterone", 0.0)
                                                                     - 0.4 * s["pfc_maturity"] - 0.3 * s["agreeableness"] + 0.2))
        s["grudge"] = clip(s["grudge"] * 0.97)
        s["police_contact"] = clip(s["police_contact"] * 0.9)

    def victimised(self, p, key: str) -> None:
        """Something was done to him (or his people): it can leave a grudge."""
        if key in VICTIM:
            p.s["grudge"] = clip(p.s["grudge"] + VICTIM[key])

    def pressure(self, p) -> float:
        """Multiplies the calibrated offending rate: about 1 for an ordinary month, up to ~1.8 when needs, urges and a
        grudge all push, down to ~0.6 when he is settled."""
        if self.off:
            return 1.0
        s = p.s
        push = 0.35 * self.need["survival"] + 0.25 * s["thrill"] + 0.25 * s["aggression"] + 0.15 * s["grudge"]
        return max(0.6, min(1.8, 1.0 + 1.6 * (push - 0.3)))

    def after_choice(self, p, F, key: str, choice_text: str, deltas: Dict[str, float]) -> str:
        """A lived choice that broke the law: caught or not, a record, maybe prison. Returns what happened, or ''."""
        caught = deltas.get("police_contact", 0) > 0
        unlawful = key in UNLAWFUL and UNLAWFUL[key] and any(w in choice_text for w in UNLAWFUL[key])
        if not unlawful:
            return ""
        self.offences += 1
        if key in ("vigilante", "get_even"):
            self.vigilante += 1
            p.s["grudge"] = clip(p.s["grudge"] - 0.3)      # getting even spends the grudge
        hs = p.hardships
        out = ""
        if caught and p.years >= 16:
            from .hardships import PRISON
            hs.record = True
            if self.rng.random() < (0.5 if key in ("vigilante", "get_even") else 0.25) * PRISON.get(hs.region, 0.3):
                hs.in_prison_until = p.age + self.rng.randint(3, 36)
                out = "is sent to prison for it"
            else:
                out = "is arrested and now has a record"
        elif caught:
            out = "is caught and brought home by the police"
        self.recent.append([round(p.years, 2), key, choice_text[:50], out or "got away with it"])
        del self.recent[:-10]
        return out

    def to_json(self, p) -> dict:
        return {"off": self.off, "needs": {k: round(v, 2) for k, v in self.need.items()}, "want": self.want,
                "urges": {k: round(p.s[k], 3) for k in ("thrill", "aggression", "grudge")},
                "pressure": round(self.pressure(p), 2), "offences": self.offences, "vigilante": self.vigilante,
                "recent": self.recent[-6:]}


# scenario key -> words in a choice that make it unlawful
UNLAWFUL = {"steal_chance": ("take",), "want_it": ("steal",), "provoked": ("hit",), "witness_crime": (),
            "vigilante": ("hit", "burn"), "get_even": ("smash", "hit")}
