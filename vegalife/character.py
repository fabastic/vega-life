"""Who he becomes: personality formed by what he lives through, sleep, mood, and the ways a human feels outcomes.

Everything here is grounded in published findings, with the caveats noted.

Personality (the Big Five)
  * About half of each trait is innate: twin studies put heritability at roughly 40-60%. Each trait's innate
    seed is a factor you can set; the rest is formed by his life.
  * Traits move toward maturity with age: emotional stability, agreeableness and conscientiousness rise
    (Roberts, Walton & Viechtbauer 2006; Bleidorn et al. 2022, which found emotional stability rising most).
  * Traits are most changeable in childhood and settle by about 25 (rank-order stability plateaus in young
    adulthood, Bleidorn et al. 2022).
  * Life events nudge traits a little, more for work events than for love events (Buhler et al. 2024: small
    effects, strongest for graduation, a first job, a new relationship, marriage and divorce).

How outcomes are felt (used only for his learning signal; the real outcome is always kept separately)
  * Loss aversion: a loss weighs more than an equal gain. lambda runs from 1.5 to 2.1 with neuroticism; the
    meta-analytic mean is about 1.96 (Brown et al. 2024), with wide spread (Walasek et al. 2018: 1.31).
  * Present bias: later consequences count for less (quasi-hyperbolic beta-delta). beta grows with prefrontal
    maturity and conscientiousness, since impulsive choice falls through adolescence (Steinberg et al. 2009).
  * Curiosity: a bonus for choices he has rarely made, scaled by openness and age. It stands in for a drive
    toward learning progress (Gottlieb, Oudeyer & Lopes), which is better established in agents than in people.

Body and mood
  * Sleep: falls with shift work, anxiety, screens and young children. Poor sleep impairs taking in new things
    (encoding) and weakens consolidation, and replay favours salient memories (mostly rodent evidence).
  * Mood adapts: he gets used to his circumstances, but not completely (Diener, Lucas & Scollon 2006: partial
    adaptation, with lasting effects of some events). Mood is relative to an adaptation level that follows his
    wellbeing over about two years.
  * Stress narrows choice toward the familiar (stress promotes overexploitation, Lenow et al. 2017), and lack of
    sleep makes choices noisier. This sets the temperature of the answer he lives, not of his learning samples.
"""
from __future__ import annotations

import math
from typing import Dict

from .factors import FactorSet
from .world import Person

TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


# How a life event nudges personality (key from Person.note). Small, as the evidence says; work events larger.
EVENT_NUDGES: Dict[str, Dict[str, float]] = {
    "work+": {"conscientiousness": 0.03, "neuroticism": -0.01},       # first job, finding work
    "work-": {"neuroticism": 0.03, "conscientiousness": -0.01},       # losing a job
    "study+": {"conscientiousness": 0.02, "openness": 0.02},          # starting or finishing studies
    "home+": {"conscientiousness": 0.01, "neuroticism": -0.01},       # moving out
    "bullied": {"neuroticism": 0.03, "extraversion": -0.02, "agreeableness": -0.01},
    "friend+": {"extraversion": 0.01, "agreeableness": 0.005},
    "friend-": {"neuroticism": 0.01},
    "move": {"neuroticism": 0.015, "openness": 0.005},
    "disaster": {"neuroticism": 0.01},
    "children+": {"agreeableness": 0.02, "conscientiousness": 0.02},
}


class Character:
    def __init__(self, p: Person, F: FactorSet):
        self.innate = {t: F[f"trait_{t}"] for t in TRAITS}
        for t in TRAITS:                          # a newborn's temperament is its innate seed
            p.s[t] = self.innate[t]
        p.s["sleep"] = 0.8
        p.s["mood"] = 0.5
        p.s["mood_baseline"] = p.wellbeing()

    # ------------------------------------------------------------------ month by month
    def step(self, p: Person, F: FactorSet) -> None:
        s, y = p.s, p.years
        # Sleep this month.
        adult_kids = s["children"] if 22 <= y < 45 else 0.0
        work_nights = F["shift_work"] * s["employed"] if y >= 18 else 0.0
        teen_screens = F["screen_time"] * (1.3 if 12 <= y < 25 else 1.0)
        target = 0.92 - 0.4 * work_nights - 0.3 * s["anxiety"] - 0.15 * teen_screens - 0.15 * adult_kids \
            - 0.1 * s["neuroticism"] - (0.15 if y < 0.5 else 0.0) - 0.15 * (1 - s["health"]) \
            - 0.6 * getattr(getattr(p, "illness", None), "sleep_now", 0.0) \
            - 0.6 * getattr(getattr(p, "hormones", None), "sleep_now", 0.0)  # illness, teen body clock, flushes
        s["sleep"] = clip(0.6 * s["sleep"] + 0.4 * clip(target))

        # Personality: half innate, half formed by his circumstances, moving toward maturity with age.
        maturity = clip((y - 15) / 35)
        env = {
            "neuroticism": 0.25 + 0.5 * s["allostatic_load"] + 0.4 * s["anxiety"] - 0.25 * s["attachment"]
            - 0.2 * s["community_support"] + 0.15 * s["felt_loneliness"],
            "extraversion": 0.25 + 0.45 * s["peer_support"] + 0.3 * s["community_support"] - 0.3 * s["social_isolation"],
            "openness": 0.25 + 0.3 * s["academic"] + 0.15 * F["curr_arts_play"] + 0.2 * F["friend_diversity"]
            + 0.15 * F["extracurriculars"] - 0.2 * F["cultural_strictness"],
            "conscientiousness": 0.25 + 0.3 * s["academic"] + 0.25 * s["employed"] * (y > 18) + 0.2 * s["school_belonging"]
            + 0.1 * s["goal_horizon"],
            "agreeableness": 0.3 + 0.35 * s["attachment"] + 0.25 * s["community_support"] - 0.3 * s["household_friction"]
            - 0.15 * s["peer_risk"],
        }
        # Emotional stability rises most across the lifespan (Bleidorn et al. 2022), so neuroticism drifts furthest.
        drift = {"neuroticism": -0.3, "conscientiousness": 0.1, "agreeableness": 0.1, "extraversion": 0.0, "openness": -0.03}
        # Changeable in childhood, settling by about 25 to a lower plateau.
        rate = 0.02 if y < 12 else 0.02 * max(0.25, 1 - (y - 12) / 13)
        for t in TRAITS:
            target = 0.5 * self.innate[t] + 0.5 * clip(env[t]) + drift[t] * maturity
            s[t] = clip(s[t] + rate * (clip(target) - s[t]))
        # Neuroticism makes him more reactive to stress.
        s["anxiety"] = clip(s["anxiety"] + 0.003 * (s["neuroticism"] - 0.5))

        # Mood: relative to what he has got used to (partial adaptation over about two years).
        w = p.wellbeing()
        s["mood_baseline"] += (w - s["mood_baseline"]) / 24
        # ...and coloured by this month's chemistry: the good moments, closeness, daylight, stress (chemistry.py).
        season = getattr(getattr(p, "seasons", None), "shape", 0.0)      # midlife dip, late-life regret (seasons.py)
        season += getattr(getattr(p, "hormones", None), "mood_drag", 0.0)   # PMS, winter, low testosterone
        s["mood"] = clip(0.5 + 1.4 * (w - s["mood_baseline"]) + 0.6 * (w - 0.45) + 0.75 * (s.get("joy", 0.5) - 0.62)
                         - season)

    def nudge(self, p: Person, key: str, valence: float) -> Dict[str, float]:
        """A life event shifts his personality a little (bigger shifts while young). Returns the shifts made."""
        k = {"work": "work+" if valence > 0 else "work-", "study": "study+", "home": "home+",
             "friend": "friend+" if valence > 0 else "friend-"}.get(key, key)
        scale = 1.0 if p.years < 25 else 0.6
        done = {}
        for t, d in EVENT_NUDGES.get(k, {}).items():
            before = p.s[t]
            p.s[t] = clip(before + d * scale)
            done[t] = p.s[t] - before
        return done

    # ------------------------------------------------------------------ how outcomes are felt
    @staticmethod
    def loss_aversion(p: Person) -> float:
        return 1.5 + 0.6 * p.s["neuroticism"]

    @staticmethod
    def present_bias(p: Person) -> tuple:
        """(beta, monthly delta). beta near 0.5 for an impulsive child, near 0.95 for a mature, conscientious adult."""
        c = p.s["conscientiousness"]
        beta = 0.5 + 0.45 * p.s["pfc_maturity"] * (0.6 + 0.4 * c)
        delta = 0.97 + 0.025 * c
        return beta, delta

    @staticmethod
    def curiosity(p: Person) -> float:
        y = p.years
        age = 1.0 if y < 18 else max(0.35, 1.0 - (y - 18) / 60)
        return p.s["openness"] * age

    @staticmethod
    def decision_temperature(p: Person, base: float = 1.0) -> float:
        """How noisy the answer he actually lives is: stress narrows it, lack of sleep loosens it."""
        stress = max(p.s["anxiety"], p.s["allostatic_load"])
        return base * (1 - 0.4 * stress) * (1 + 0.6 * (1 - p.s["sleep"]))

    def felt(self, p: Person, now: float, later: float, delay: int) -> float:
        """The outcome as he feels it: losses weigh more, and later consequences are discounted."""
        lam = self.loss_aversion(p)
        beta, delta = self.present_bias(p)
        f = lambda x: x if x >= 0 else lam * x
        return f(now) + (beta * delta ** max(1, delay) * f(later) if delay else f(later))


def learning_plasticity(age_years: float) -> float:
    """How easily new language and skills are taken in. Grammar learning stays strong to about 17, then declines
    (Hartshorne, Tenenbaum & Pinker 2018); learning keeps slowing through adult life."""
    y = age_years
    if y < 17:
        return 1.0
    return max(0.25, 1.0 - 0.45 * min(1.0, (y - 17) / 13) - max(0.0, y - 30) / 100)
