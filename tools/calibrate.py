"""Does the simulated world behave like the real one? Lives without the network, compared with published numbers.

    python tools/calibrate.py [lives per condition] [--no-choices]      (default 300 lives)

By default he faces his situations each month and picks at random, so their effects and delayed consequences
are part of the check; --no-choices checks the world with nobody choosing.

Each check simulates many lives with paired seeds and compares one outcome against a published target. The
targets and their sources are in CALIBRATION.md. A mismatch means the world model needs adjusting, not the network.
"""
import math
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vegalife import factors as fx                  # noqa: E402
from vegalife.character import Character            # noqa: E402
from vegalife.people import Circle                  # noqa: E402
from vegalife.scenarios import Scenario, draw       # noqa: E402
from vegalife.world import Person                   # noqa: E402

_args = [a for a in sys.argv[1:] if not a.startswith("--")] if __name__ == "__main__" else []
N = int(_args[0]) if _args else 300


CHOICES = "--no-choices" not in sys.argv


def live_choices(p, F, r):
    """He faces this month's situations and picks at random (a stand-in for a network that has learned nothing),
    so their effects and delayed consequences count, as in a real life."""
    for item in draw(p, F, r, 6):
        if not isinstance(item, Scenario):
            continue
        c = r.choice(item.choices)
        p.apply(c.effect(p, F, r), fades=True)
        if c.later:
            p.schedule(c.delay, c.later, f"consequence: {c.text}", 0.0)


def life(seed, over=None, max_years=105):
    F = fx.sample(seed, over or {})
    p = Person(F, seed, Circle(F, seed))
    ch = Character(p, F)
    r = random.Random(seed * 17 + 5)
    track = {"unemployed_months": 0, "employed_months": 0, "unemployed_deaths": 0, "employed_deaths": 0,
             "unemployed_hazard": 0.0, "employed_hazard": 0.0, "insulin60": None, "anxiety30": None,
             "loghaz": 0.0, "loghaz_n": 0}
    while p.alive and p.age < max_years * 12:
        working_age = 25 <= p.years < 60
        was_employed = p.s["employed"] > 0.5
        p.step_month(F)
        if CHOICES and p.alive:
            live_choices(p, F, r)
        ch.step(p, F)
        for m in p.pending:
            ch.nudge(p, m["key"], m["valence"])
        p.pending.clear()
        if working_age:
            k = "employed" if was_employed else "unemployed"
            track[f"{k}_months"] += 1
            track[f"{k}_hazard"] += p.hazard
            if not p.alive:
                track[f"{k}_deaths"] += 1
        if track["insulin60"] is None and p.years >= 60:
            track["insulin60"] = p.s["insulin_resistance"]
        if track["anxiety30"] is None and p.years >= 30:
            track["anxiety30"] = p.s["anxiety"]
        if 30 <= p.years < 80 and p.alive and p.hazard > 0:
            track["loghaz"] += math.log(p.hazard)
            track["loghaz_n"] += 1
    return p.years, track


def lifespans(over=None, seeds=None):
    seeds = seeds or range(1, N + 1)
    return [life(s, over) for s in seeds]


def mean_age(rows):
    return st.mean(a for a, _ in rows)


def risk(x, centre, width):
    """State values are risk levels, not diagnoses: turn one into a probability with a wide logistic that stands
    for everything the model leaves out (other causes, chance), instead of a hard cut-off."""
    return 1 / (1 + math.exp(-(x - centre) / width))


def years_from_hazard(a, b):
    """Life-years between two groups from their average log hazard over ages 30-80 (Gompertz slope 0.085/y).
    Much less noisy than comparing ages at death."""
    la = st.mean(t["loghaz"] / t["loghaz_n"] for _, t in a if t["loghaz_n"])
    lb = st.mean(t["loghaz"] / t["loghaz_n"] for _, t in b if t["loghaz_n"])
    return (lb - la) / 0.085


def report(name, value, target, ok):
    print(f"{'OK  ' if ok else 'OFF '} {name}: {value}   (target {target})")
    return ok


def main():
    results = []
    base = lifespans()
    ages = [a for a, _ in base]
    results.append(report("life expectancy at birth", f"{st.mean(ages):.1f} y (median {st.median(ages):.1f})",
                          "about 76-81 (US 2023: 78.4; men 75.8)", 74 <= st.mean(ages) <= 82))

    poor = lifespans({"ses": 0.05})
    rich = lifespans({"ses": 0.95})
    gap = mean_age(rich) - mean_age(poor)
    results.append(report("income gap, poorest vs richest family", f"{gap:.1f} y",
                          "a few years up to 10-15 between the extreme 1% (Chetty 2016)", 4 <= gap <= 15))

    lonely = {"community_ties": 0.05, "friend_count": 0.05, "partner_support": 0.05, "friend_closeness": 0.1}
    social = {"community_ties": 0.95, "friend_count": 0.9, "partner_support": 0.95, "friend_closeness": 0.9}
    a, b = lifespans(lonely), lifespans(social)
    surv = lambda rows, age: sum(x >= age for x, _ in rows) / len(rows)
    odds = lambda q: q / max(1e-9, 1 - q)
    orr = odds(surv(b, 80)) / max(1e-9, odds(surv(a, 80)))
    results.append(report("social ties, odds of surviving to 80 (strong vs weak)", f"OR {orr:.2f}",
                          "about 1.5 (Holt-Lunstad 2010: OR 1.50)", 1.2 <= orr <= 2.2))

    adverse = {"household_stress": 0.95, "structural_violence": 0.9, "housing_instability": 0.9, "bullying": 0.9,
               "caregiver_warmth": 0.15}
    gentle = {"household_stress": 0.05, "structural_violence": 0.05, "housing_instability": 0.05, "bullying": 0.05,
              "caregiver_warmth": 0.85}
    hard, soft = lifespans(adverse), lifespans(gentle)
    early = lambda rows: sum(x < 65 for x, _ in rows) / len(rows)
    rr = early(hard) / max(1e-9, early(soft))
    results.append(report("childhood adversity, risk of death before 65", f"RR {rr:.2f} ({early(hard):.0%} vs {early(soft):.0%})",
                          "about 1.45 for 4+ ACEs (NICHD cohort); 1.8 in family data", 1.2 <= rr <= 2.5))
    dep = lambda rows: st.mean(risk(t["anxiety30"], 0.6, 0.12) for _, t in rows if t["anxiety30"] is not None)
    rr_dep = dep(hard) / max(1e-9, dep(soft))
    results.append(report("childhood adversity, distress at 30", f"RR {rr_dep:.2f} ({dep(hard):.0%} vs {dep(soft):.0%})",
                          "mental ill health OR 3-6 for 4+ ACEs (Hughes 2017)", 2.0 <= rr_dep <= 8.0))

    # Deaths in working age are rare, so compare the average monthly hazard instead of counting deaths.
    um, uh = sum(t["unemployed_months"] for _, t in base), sum(t["unemployed_hazard"] for _, t in base)
    em, eh = sum(t["employed_months"] for _, t in base), sum(t["employed_hazard"] for _, t in base)
    hr = (uh / max(1, um)) / max(1e-12, eh / max(1, em))
    results.append(report("unemployment, working-age death rate ratio", f"HR {hr:.2f}",
                          "1.63 adjusted (Roelfs 2011); this is unadjusted, so somewhat higher", 1.3 <= hr <= 2.5))

    clean, dirty = lifespans({"local_pollution": 0.0}), lifespans({"local_pollution": 1.0})
    loss = years_from_hazard(clean, dirty)
    results.append(report("air pollution, clean vs heavily polluted zip code", f"{loss:.1f} y (from hazards)",
                          "about 1 y per 10 ug/m3 PM2.5 (AQLI); 0.5-3 y across a realistic range", 0.5 <= loss <= 3.5))

    day, night = lifespans({"shift_work": 0.0}), lifespans({"shift_work": 1.0})
    ins = lambda rows: st.mean(risk(t["insulin60"], 0.4, 0.1) for _, t in rows if t["insulin60"] is not None)
    rr_sw = ins(night) / max(1e-9, ins(day))
    results.append(report("night shift work, metabolic disease by 60", f"RR {rr_sw:.2f} ({ins(night):.0%} vs {ins(day):.0%})",
                          "about 1.1-1.4 for type 2 diabetes (OR 1.09 pooled; 1.44 usual nights)", 1.05 <= rr_sw <= 1.8))
    print(f"\n{sum(results)}/{len(results)} within range ({N} lives per condition)")
    return results


if __name__ == "__main__":
    main()
