"""What he believes about the world: propositions with a confidence, the experiences behind them, and where they came
from (expansion plan 1.1).

Not traits. Each belief is a sentence he could agree or disagree with ("people can be trusted"), held with a
confidence in 0..1 (0.5: no view). It changes when something that bears on it happens:

  evidence      every happening and every lived choice is read for what it says about each belief (EVIDENCE); its
                weight is how strongly it was felt (|valence|, arousal)
  plasticity    a child's beliefs move fast, an adult's slowly (the same shape as his network's critical periods), and
                a belief backed by a lot of evidence resists one more piece of it (entrenchment)
  origin        the first source that moved it: his parents (seeded at birth from how he is raised), his peers, his
                feed, or his own experience
  dependencies  beliefs lean on each other: losing trust in people drags down "the world is fair" a little

How they act on him: when he weighs a choice, a belief adds to how good it feels (bias), so what he believes shapes
what he learns to choose. They never change the world's numbers directly, so calibration is untouched.
Ablation: "beliefs" in the config's ablate list freezes them at the seeded priors and removes the bias.
Its own random generator: it never shifts his world.
"""
from __future__ import annotations

import math
import random
import re
from typing import Dict, List, Optional, Tuple

BELIEFS = {
    "people_trustworthy": "people can be trusted",
    "world_fair": "the world is generally fair",
    "effort_pays": "hard work leads to success",
    "failure_recoverable": "failure is recoverable",
    "compromise_needed": "relationships need compromise",
    "self_worth": "I am worth something",
    "future_good": "the future will be good",
    "authority_just": "the police and courts are on my side",
    "violence_works": "sometimes you have to hurt people to put things right",
}

# event key -> [(belief, sign)]: the sign is multiplied by the event's valence, so a good exam result is evidence
# that effort pays and a bad one that it does not.
EVIDENCE: Dict[str, List[Tuple[str, float]]] = {
    "friend": [("people_trustworthy", 1.0)], "bond": [("people_trustworthy", 1.0)],
    "bullied": [("people_trustworthy", 1.0), ("world_fair", 1.0), ("self_worth", 1.0)],
    "cyberbullied": [("people_trustworthy", 1.0), ("self_worth", 1.0)],
    "scam": [("people_trustworthy", 1.0)], "affair": [("people_trustworthy", 1.0)],
    "prejudice": [("world_fair", 1.0), ("authority_just", 0.5)], "bias": [("world_fair", 1.0)],
    "stood_up": [("people_trustworthy", -1.0), ("violence_works", -0.3)],
    "exam": [("effort_pays", 1.0)], "school": [("effort_pays", 0.6)], "study": [("effort_pays", 0.6)],
    "work": [("effort_pays", 1.0), ("future_good", 0.5)], "retire": [("future_good", 0.5)],
    "burnout": [("effort_pays", 0.6)], "repair": [("compromise_needed", -1.0), ("failure_recoverable", -1.0)],
    "fight": [("compromise_needed", -0.6)], "divorce": [("compromise_needed", -0.5)],
    "breakup": [("compromise_needed", -0.5)], "own_divorce": [("compromise_needed", -0.8), ("failure_recoverable", 0.5)],
    "recover": [("failure_recoverable", 1.0)], "help": [("failure_recoverable", 1.0), ("people_trustworthy", 0.5)],
    "death": [("world_fair", 0.5), ("future_good", 0.4)], "disaster": [("world_fair", 1.0), ("future_good", 1.0)],
    "mental": [("self_worth", 0.6)], "joy": [("future_good", 0.6), ("self_worth", 0.4)],
    "good": [("future_good", 0.6)], "wedding": [("people_trustworthy", 0.6), ("future_good", 0.6)],
    "child": [("future_good", 0.8)], "mentor": [("people_trustworthy", 0.8), ("effort_pays", 0.5)],
    "there_for": [("people_trustworthy", 1.0)], "absent": [("people_trustworthy", 1.0)],
    "assault": [("world_fair", 1.0), ("people_trustworthy", 0.6), ("authority_just", 0.5), ("violence_works", -0.4)],
    "offence": [("authority_just", 0.6)], "prison": [("authority_just", 1.0), ("failure_recoverable", 0.5)],
    "release": [("failure_recoverable", -0.6)], "debt": [("world_fair", 0.6), ("future_good", 0.6)],
    "consequence": [("effort_pays", 0.5)], "vigilante": [("violence_works", -1.0), ("authority_just", 0.4)],
    "justice": [("authority_just", 1.0), ("world_fair", 0.6)],
    # abuse and chaos at home teach that people, even close ones, are not safe (ace.py)
    "ace": [("people_trustworthy", 1.0), ("self_worth", 0.8), ("world_fair", 0.6), ("violence_works", -0.3)],
    "recession": [("effort_pays", 0.6), ("world_fair", 0.6), ("future_good", 0.6)],          # timeline.py
    "war": [("world_fair", 1.0), ("authority_just", 0.6), ("violence_works", -0.3)],
}

# Which source an event key comes from, for the belief's origin.
SOURCE = {"friend": "peers", "bullied": "peers", "bond": "peers", "cyberbullied": "feed", "phone": "feed",
          "scam": "feed", "mentor": "a mentor"}

# a belief -> [(another belief it pulls on, how much)]
DEPENDS = {"people_trustworthy": [("world_fair", 0.25), ("authority_just", 0.1)],
           "world_fair": [("future_good", 0.25), ("effort_pays", 0.15)],
           "failure_recoverable": [("future_good", 0.2), ("self_worth", 0.15)],
           "authority_just": [("violence_works", -0.3)]}

# How a belief colours a choice, by what the choice says: (pattern, belief, how it feels when the belief is held).
BIAS = [
    (re.compile(r"\b(ask|tell|trust|share|talk|confide|lend|help|call|meet|join|invite|forgive)\b", re.I),
     "people_trustworthy", 0.06),
    (re.compile(r"\b(study|practi[sc]e|work|learn|train|write it yourself|apply|save|plan)\b", re.I), "effort_pays", 0.06),
    (re.compile(r"\b(try again|keep going|start over|apologi[sz]e|repair|retake|get help)\b", re.I),
     "failure_recoverable", 0.05),
    (re.compile(r"\b(listen|compromise|talk it out|meet halfway|ask why)\b", re.I), "compromise_needed", 0.05),
    (re.compile(r"\b(report|police|court|teacher|complain|official)\b", re.I), "authority_just", 0.06),
    (re.compile(r"\b(hit|hurt|beat|fight|punch|teach (?:him|her|them) a lesson|get even|revenge)\b", re.I),
     "violence_works", 0.08),
    (re.compile(r"\b(give up|decide .* pointless|skip|quit)\b", re.I), "future_good", -0.05),
]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def logit(p: float) -> float:
    p = clip(p, 1e-4, 1 - 1e-4)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def plasticity(years: float) -> float:
    """How far one piece of evidence moves a belief at this age: high in childhood, falling through adolescence,
    low but never zero in adulthood."""
    return 0.25 + 0.75 * math.exp(-max(0.0, years - 3) / 10)


class Belief:
    __slots__ = ("key", "confidence", "origin", "support", "contra", "n", "updated", "prior")

    def __init__(self, key: str, confidence: float, origin: str):
        self.key, self.confidence, self.origin, self.prior = key, confidence, origin, confidence
        self.support: List[list] = []        # [age_years, what happened, weight], newest last, a few kept
        self.contra: List[list] = []
        self.n = 0.0                         # how much evidence it has taken in: it entrenches
        self.updated = 0

    def to_json(self) -> dict:
        return {"key": self.key, "text": BELIEFS[self.key], "confidence": round(self.confidence, 3),
                "prior": round(self.prior, 3), "origin": self.origin, "evidence": round(self.n, 2),
                "updated_years": round(self.updated / 12, 2), "support": self.support[-4:], "contra": self.contra[-4:]}


class Beliefs:
    KEEP = 6

    def __init__(self, F, seed: int):
        self.rng = random.Random(seed * 7919 + 41)
        self.off = False
        warm, ses = F["caregiver_warmth"], F["ses"]
        safe, strict = F["neighbourhood_safety"], F["cultural_strictness"]
        r = self.rng
        prior = {  # what his parents hand him, before he has any experience of his own
            "people_trustworthy": 0.35 + 0.3 * warm + 0.1 * safe, "world_fair": 0.3 + 0.25 * ses + 0.15 * safe,
            "effort_pays": 0.45 + 0.2 * ses + 0.1 * strict, "failure_recoverable": 0.4 + 0.25 * warm,
            "compromise_needed": 0.45 + 0.2 * warm, "self_worth": 0.4 + 0.35 * warm,
            "future_good": 0.4 + 0.2 * ses + 0.1 * warm, "authority_just": 0.35 + 0.2 * ses + 0.25 * safe,
            "violence_works": 0.25 + 0.2 * (1 - safe) + 0.1 * (1 - warm),
        }
        self.b: Dict[str, Belief] = {k: Belief(k, clip(v + r.gauss(0, 0.05), 0.05, 0.95), "parents")
                                     for k, v in prior.items()}
        self.recent: List[list] = []          # [age_years, belief, before, after, why]

    # ------------------------------------------------------------------ evidence
    def evidence(self, p, key: str, valence: float, arousal: float, text: str, source: Optional[str] = None) -> Dict[str, float]:
        """Something happened that bears on his beliefs. Returns {belief: change in confidence}."""
        if self.off or key not in EVIDENCE or abs(valence) < 0.05:
            return {}
        out: Dict[str, float] = {}
        weight = abs(valence) * (0.5 + arousal)
        for bk, sign in EVIDENCE[key]:
            d = self._move(p, bk, sign * (1 if valence > 0 else -1) * weight, text, source or SOURCE.get(key, "his own life"))
            if d:
                out[bk] = d
        return out

    def choice(self, p, judged: float, valence: float, text: str) -> Dict[str, float]:
        """He did something. Hurting someone that turned out well for him is evidence that violence works; hurting
        someone and paying for it, evidence that it does not. Helping and being thanked: people can be trusted."""
        if self.off or abs(valence) < 0.05 or not judged:
            return {}
        bk = "violence_works" if judged < 0 else "people_trustworthy"
        d = self._move(p, bk, valence * 0.8, text, "his own life")
        return {bk: d} if d else {}

    def _move(self, p, bk: str, push: float, text: str, source: str, depth: int = 0) -> float:
        b = self.b[bk]
        step = 0.6 * plasticity(p.years) * push / (1 + 0.04 * b.n)
        if abs(step) < 1e-4:
            return 0.0
        before = b.confidence
        b.confidence = clip(sigmoid(logit(before) + step), 0.02, 0.98)
        b.n += abs(push)
        b.updated = p.age
        if b.origin == "parents" and depth == 0 and abs(step) > 0.15 and p.years > 6:
            b.origin = source                  # his own life (or his peers, or his feed) has taken this one over
        if depth == 0:
            row = [round(p.years, 2), text[:80], round(push, 2)]
            (b.support if push > 0 else b.contra).append(row)
            del b.support[:-self.KEEP], b.contra[:-self.KEEP]
            if abs(b.confidence - before) > 0.01:
                self.recent.append([round(p.years, 2), bk, round(before, 3), round(b.confidence, 3), text[:60]])
                del self.recent[:-20]
            for other, w in DEPENDS.get(bk, []):
                self._move(p, other, push * w, text, source, depth + 1)
        return b.confidence - before

    # ------------------------------------------------------------------ acting on him
    def bias(self, choice_text: str) -> float:
        """How his beliefs colour a choice: holding 'people can be trusted' makes confiding feel better, doubting it
        makes it feel worse. Centred on 0.5, so having no view adds nothing."""
        if self.off:
            return 0.0
        total = 0.0
        for pat, bk, w in BIAS:
            if pat.search(choice_text):
                total += w * (self.b[bk].confidence - 0.5) * 2
        return max(-0.15, min(0.15, total))

    def line(self, k: int = 2) -> str:
        """His strongest views, short enough for a prompt: 'Believe: people can be trusted; not: the world is fair.'"""
        ranked = sorted(self.b.values(), key=lambda b: -abs(b.confidence - 0.5))[:k]
        parts = [("" if b.confidence >= 0.5 else "not ") + BELIEFS[b.key] for b in ranked if abs(b.confidence - 0.5) > 0.1]
        return ("Believe: " + "; ".join(parts) + ".") if parts else ""

    def vector(self) -> Dict[str, float]:
        return {k: round(b.confidence, 3) for k, b in self.b.items()}

    def to_json(self) -> dict:
        return {"off": self.off, "beliefs": [b.to_json() for b in self.b.values()], "recent": self.recent[-10:],
                "line": self.line()}
