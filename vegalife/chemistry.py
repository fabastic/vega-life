"""His body chemistry, and the ordinary good moments that make most of a life bearable, often happy.

Seven signals, each 0-1 for "how much of this month it coloured":
  dopamine    wanting and reward. Fires for the unexpected (reward prediction error, Schultz): a joy he has had a
              lot lately lifts him less; something new or surprising lifts him more.
  oxytocin    closeness: hugs, a partner, holding his baby, a pet. The firmest evidence is that affectionate touch
              lowers cortisol and stress (Ditzen 2007; Dreisoerner 2021); that oxytocin carries it is less certain,
              so here the touch itself does the buffering.
  serotonin   steadiness. Brain serotonin turnover tracks daylight and is lowest in winter (Lambert et al. 2002);
              sleep, exercise and being outdoors raise it.
  endorphins  the lift after exercise, laughing, music. (Mostly the endocannabinoid system, in fact; the name is
              the familiar one.) Being active ~150 min a week goes with ~20% lower depression risk.
  cortisol    the stress hormone: anxiety, stress load, grief, fights at home, a hard job. Chronic stress flattens
              its daily rhythm; a flatter rhythm carries ~1.3x mortality per SD (Whitehall II, MIDUS). Touch and
              closeness damp it.
  adrenaline  acute alarm: exams, danger, a fight, a disaster. Up fast, gone fast.
  melatonin   the night signal: good, regular, dark sleep. Late screens and night shifts suppress it.

They add up to `joy` (positive affect). People feel more positive than negative on most days (74% of people
'yesterday' across 160 countries, Gallup; Diener & Diener 1996: most people are mildly happy), and the simulation is
calibrated to that: tools/moodcal.py. Joy feeds his mood (character.py) and his wellbeing, and the brightest moment of
a month can become a memory, so he remembers good things too.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .factors import FactorSet

HORMONES = ["dopamine", "oxytocin", "serotonin", "endorphins", "cortisol", "adrenaline", "melatonin", "joy"]
TONIC = {"dopamine": 0.35, "oxytocin": 0.3, "serotonin": 0.45, "endorphins": 0.25, "cortisol": 0.3,
         "adrenaline": 0.1, "melatonin": 0.6}
# How much of last month's level carries over: fast signals settle within a month, slow ones over a few.
KEEP = {"dopamine": 0.3, "oxytocin": 0.4, "serotonin": 0.7, "endorphins": 0.3, "cortisol": 0.6, "adrenaline": 0.1,
        "melatonin": 0.6}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class Joy:
    key: str
    ages: tuple                                # (from, to) years
    rate: Callable                             # (p, F, fam) -> expected times per month
    release: Dict[str, float]
    texts: List[str]
    valence: float = 0.5


def _friends(p) -> float:
    return sum(f.closeness for f in p.circle.present(p.age)) if p.circle else 0.0


def _has(fam, rel: str, month: int) -> bool:
    return any(x.relation == rel and x.present(month) for x in fam.people) if fam else False


def _infant(fam, month: int) -> float:
    return 1.0 if fam and any(x.relation == "child" and x.alive and 0 <= month - x.born < 18 for x in fam.people) else 0.0


def _kids(fam, month: int) -> int:
    return sum(1 for x in fam.people if x.relation == "child" and x.present(month)) if fam else 0


JOYS: List[Joy] = [
    Joy("cuddle", (0, 12), lambda p, F, fam: 6 * F["caregiver_warmth"] * (0.4 + 0.6 * p.s["caregiver_attention"]),
        {"oxytocin": 0.08, "serotonin": 0.02}, ["is held close by {carer}", "falls asleep on {carer}'s shoulder"]),
    Joy("play", (1, 13), lambda p, F, fam: 4 * (0.4 + 0.6 * F["curr_arts_play"]) * (1 - 0.5 * F["frictionless_tech"]),
        {"endorphins": 0.06, "dopamine": 0.04}, ["builds a fort out of cushions", "plays hide and seek", "splashes in puddles"]),
    Joy("laugh_friends", (4, 90), lambda p, F, fam: 1.5 * _friends(p) * (0.5 + p.s["extraversion"]),
        {"endorphins": 0.06, "oxytocin": 0.04, "dopamine": 0.03}, ["laughs until it hurts with {friend}", "stays up talking with {friend}"]),
    Joy("praise", (3, 19), lambda p, F, fam: 2 * F["teacher_warmth"] * (0.3 + p.s["academic"]),
        {"dopamine": 0.07}, ["is told his work is really good", "gets a gold star"]),
    Joy("achievement", (6, 70), lambda p, F, fam: 0.8 * (0.3 + p.s["conscientiousness"]) * (0.3 + p.s["skill_value"] + p.s["academic"]) ,
        {"dopamine": 0.1, "serotonin": 0.02}, ["finally gets something hard right", "finishes what he set out to do"]),
    Joy("exercise", (5, 85), lambda p, F, fam: 3 * (0.3 + 0.7 * p.s["motor"]) * (1 - 0.5 * F["low_walkability"]) * (0.5 + 0.5 * F["extracurriculars"] if p.years < 19 else 0.6),
        {"endorphins": 0.08, "serotonin": 0.03}, ["goes for a long run", "plays football in the park", "swims in the cold sea"]),
    Joy("outdoors", (0, 95), lambda p, F, fam: 3 * (1 - 0.6 * F["low_walkability"]) * (1 - 0.4 * F["local_pollution"]),
        {"serotonin": 0.05, "endorphins": 0.02}, ["walks in the sun", "watches the sunset", "sits under a tree"]),
    Joy("music", (2, 95), lambda p, F, fam: 2 * (0.3 + p.s["openness"]) * (0.5 + 0.5 * F["curr_arts_play"]),
        {"dopamine": 0.05, "endorphins": 0.04}, ["loses himself in a song", "sings loudly in the shower", "dances in the kitchen"]),
    Joy("food", (0, 95), lambda p, F, fam: 3 * (0.4 + 0.6 * (1 - p.s["household_friction"])),
        {"dopamine": 0.03, "oxytocin": 0.02}, ["eats his favourite meal", "shares a big dinner with family"]),
    Joy("pet", (0, 95), lambda p, F, fam: 5 if _has(fam, "pet", p.age) else 0.0,
        {"oxytocin": 0.05, "serotonin": 0.02}, ["is greeted by {pet} at the door", "naps with {pet}"]),
    Joy("partner", (16, 95), lambda p, F, fam: 4 * (0.5 + 0.5 * F["partner_support"]) if _has(fam, "partner", p.age) else 0.0,
        {"oxytocin": 0.08, "dopamine": 0.04}, ["is held by {partner}", "laughs with {partner} over nothing", "makes love with {partner}"]),
    Joy("child", (18, 95), lambda p, F, fam: 2.5 * min(2, _kids(fam, p.age)),
        {"oxytocin": 0.08, "dopamine": 0.03}, ["hears {child} laugh", "reads {child} a story", "watches {child} learn something new"]),
    Joy("community", (6, 95), lambda p, F, fam: 1.5 * F["community_ties"] * (1 - 0.6 * F["third_space_erosion"]),
        {"oxytocin": 0.04, "serotonin": 0.03}, ["helps a neighbour", "goes to a festival", "is welcomed at the community hall"]),
    Joy("novelty", (5, 90), lambda p, F, fam: 0.4 * (0.3 + p.s["openness"]) * (0.4 + p.s["wealth"]),
        {"dopamine": 0.12}, ["travels somewhere new", "tries something he has never done"], 0.7),
    Joy("work_win", (19, 68), lambda p, F, fam: 1.0 * p.s["employed"] * (0.3 + p.s["skill_value"]),
        {"dopamine": 0.07, "serotonin": 0.02}, ["is thanked by his team", "ships something he is proud of"]),
    Joy("screens", (3, 95), lambda p, F, fam: 8 * F["screen_time"],
        {"dopamine": 0.03}, ["scrolls late into the night"], 0.1),
]


class Chemistry:
    """Monthly levels, and the moments behind them. Its own random generator, so it never shifts the world's."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed * 2953 + 41)
        self.level = dict(TONIC)
        self.recent: Dict[str, float] = {}          # how often each joy came lately (for reward prediction error)
        self.birth_month = self.rng.randrange(12)
        self.screen_tolerance = 0.0
        self.scar = 0.0                              # lasting dent from long unemployment (Lucas 2004)
        self.joy = 0.5

    def daylight(self, month: int) -> float:
        """0 deep winter .. 1 high summer (northern hemisphere, moderate latitude)."""
        cal = (self.birth_month + month) % 12
        return 0.5 + 0.5 * math.cos((cal - 6) / 12 * 2 * math.pi)

    def step(self, p, F: FactorSet, fam=None, work=None) -> Optional[dict]:
        """One month. Updates p.s's chemistry and joy, applies their pull on his state, and returns the month's
        brightest moment as an event (or None)."""
        r, s, y, m = self.rng, p.s, p.years, p.age
        pulse = {k: 0.0 for k in TONIC}
        best = None
        for j in JOYS:
            if not (j.ages[0] <= y < j.ages[1]):
                continue
            lam = max(0.0, j.rate(p, F, fam))
            if lam <= 0:
                continue
            n = sum(1 for _ in range(int(lam * 2) + 1) if r.random() < lam / (int(lam * 2) + 1))
            if n == 0:
                self.recent[j.key] = 0.9 * self.recent.get(j.key, 0.0)
                continue
            seen = self.recent.get(j.key, 0.0)
            surprise = 1.0 / (1.0 + 0.25 * seen)      # the more expected, the less it lifts (dopamine)
            self.recent[j.key] = 0.9 * seen + n
            for k, v in j.release.items():
                gain = v * n * (surprise if k == "dopamine" else 1.0)
                if k == "dopamine" and hasattr(p, "hormones"):
                    gain *= p.hormones.dopamine_gain(y)          # peaks in the teens, fades with age
                if j.key == "screens":
                    gain *= 1 - self.screen_tolerance
                pulse[k] += gain
            score = j.valence * n * surprise
            if best is None or score > best[0]:
                best = (score, j)
        if F["screen_time"] > 0.5 and y >= 10:
            self.screen_tolerance = clip(self.screen_tolerance + 0.002 * (F["screen_time"] - 0.5))
        # tonic levels from his circumstances
        light = self.daylight(m)
        tone = {
            "dopamine": 0.25 + 0.2 * s["goal_horizon"] + 0.1 * s["autonomy"] - 0.15 * self.screen_tolerance - 0.1 * self.scar,
            "oxytocin": 0.15 + 0.2 * s["attachment"] + 0.15 * s["community_support"] - 0.15 * s["felt_loneliness"],
            "serotonin": 0.25 + 0.2 * light + 0.15 * s["sleep"] + 0.1 * s["community_support"] - 0.1 * s["allostatic_load"],
            "endorphins": 0.15 + 0.2 * s["motor"] * (1 - 0.5 * F["low_walkability"]),
            "cortisol": 0.1 + 0.35 * s["anxiety"] + 0.3 * s["allostatic_load"] + 0.25 * s.get("grief", 0.0)
            + 0.2 * s["household_friction"] + 0.1 * s["financial_paranoia"] + (0.15 * work.strain if work else 0.0)
            + 0.15 * _infant(fam, m),                    # a baby in the house: broken nights, worry
            "adrenaline": 0.05 + 0.4 * s["anxiety"] * r.random(),
            "melatonin": 0.3 + 0.4 * s["sleep"] - 0.2 * F["screen_time"] * (y >= 8) - 0.25 * F["shift_work"] * s["employed"],
        }
        touch = pulse["oxytocin"]
        tone["cortisol"] -= 0.6 * touch                  # affectionate touch damps the stress response
        for k in TONIC:
            new = clip(tone[k] + pulse[k])
            self.level[k] = clip(KEEP[k] * self.level[k] + (1 - KEEP[k]) * new)
            s[k] = round(self.level[k], 4)
        L = self.level
        joy = clip(0.15 + 0.35 * L["dopamine"] + 0.35 * L["serotonin"] + 0.3 * L["oxytocin"] + 0.25 * L["endorphins"]
                   - 0.45 * L["cortisol"] - 0.1 * L["adrenaline"] - 0.15 * self.scar)
        self.joy = joy
        s["joy"] = round(joy, 4)
        # their pull on how he is
        p.apply({"anxiety": -0.02 * (L["oxytocin"] + L["endorphins"] + L["serotonin"] - 1.0) + 0.02 * (L["cortisol"] - 0.35),
                 "allostatic_load": 0.004 * (L["cortisol"] - 0.35) - 0.002 * (L["endorphins"] + L["oxytocin"] - 0.5),
                 "loneliness": -0.015 * (L["oxytocin"] - 0.3)}, fades=True)
        s["sleep"] = clip(s["sleep"] + 0.05 * (L["melatonin"] - 0.5))
        if best is None or r.random() > 0.35 + 0.4 * best[1].valence:
            return None
        j = best[1]
        text = r.choice(j.texts)
        names = []
        fill = {"carer": "his mother", "friend": "a friend", "pet": "the dog", "partner": "his partner", "child": "his child"}
        if fam:
            for x in fam.people:
                if x.present(m):
                    key = {"mother": "carer", "pet": "pet", "partner": "partner", "child": "child"}.get(x.relation)
                    if key and fill[key].startswith(("his ", "the ", "a ")):
                        fill[key] = x.name
        if p.circle:
            close = sorted(p.circle.present(m), key=lambda f: -f.closeness)
            if close:
                fill["friend"] = close[0].name
        for k, v in fill.items():
            if "{" + k + "}" in text:
                text = text.replace("{" + k + "}", v)
                if v[0].isupper():
                    names.append(v)
        return {"text": text, "valence": round(0.3 + 0.5 * j.valence, 2), "arousal": 0.3 + 0.3 * j.valence,
                "who": names, "key": "joy", "deltas": {k: round(v, 3) for k, v in j.release.items()}}
