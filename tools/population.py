"""Population validation: live many lives with no network (choices at random), then compare what happens across them
with published rates. Every line has a target range and a source, so a change that pushes a rate out of range shows.

    python tools/population.py 200            # 200 lives, all cores, writes runs/_population/report.{json,md}
    python tools/population.py 60 --quick     # stop lives at 90

The UI's Lab tab shows the last report (/api/population)."""
from __future__ import annotations

import collections
import json
import multiprocessing as mp
import statistics as st
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vegalife import factors as fx           # noqa: E402
from vegalife.character import Character    # noqa: E402
from vegalife.people import Circle          # noqa: E402
from vegalife.world import Person           # noqa: E402
from vegalife.ace import odds_ratio         # noqa: E402

OUT = ROOT / "runs" / "_population"

# name: (lo, hi, unit, source). Shares are of lives unless the name says otherwise.
TARGETS = {
    "life_expectancy": (76.0, 80.0, "years", "US period life expectancy about 78 (CDC NCHS 2023)"),
    "good_mood_months": (0.70, 0.78, "share of adult months", "about 74% report mostly positive days (Gallup)"),
    "ever_married": (0.72, 0.88, "share of lives reaching 45", "about 80% have married by 45 (Pew from Census, 2014; "
                     "Census 2025)"),
    "ever_affair": (0.12, 0.22, "share of partnered lives", "20% of married men, 13% of women (GSS)"),
    "separated_from_partner": (0.35, 0.55, "share of partnered lives", "40-45% of first marriages end, cohabiting "
                               "unions more often (CDC NSFG)"),
    "emigrated": (0.02, 0.05, "share of lives", "about 3.6% of people live outside their birth country (UN DESA 2024)"),
    "dyslexia": (0.05, 0.10, "share of lives", "5-10% depending on the cut-off (Snowling 2013)"),
    "short_sighted_by_40": (0.25, 0.45, "share of lives reaching 40", "about 30% worldwide in 2020, rising (Holden 2016)"),
    "frail_65plus": (0.07, 0.15, "share of months aged 65+", "10.7% of community-dwelling over-65s are frail "
                     "(Collard et al. 2012, 21 studies)"),
    "care_home_65plus": (0.02, 0.06, "share of months aged 65+", "about 1.2M in US nursing homes plus about 0.8M in "
                         "assisted living, of 58M over-65s (CDC NSLTCP)"),
    "money_stress_20s": (0.22, 0.42, "share of months aged 20-29 with stress > 0.5", "Fed SHED 2023: 28% of all "
                         "adults not doing at least okay, 33-52% without a degree; the young are among the worst off"),
    "money_stress_60s": (0.08, 0.25, "share of months aged 60-69 with stress > 0.5", "older adults fare better than "
                         "the 28% average (Fed SHED 2023)"),
    "death_cancer": (0.17, 0.24, "share of deaths", "about 21% (CDC 2022)"),
    "death_heart": (0.18, 0.25, "share of deaths", "21-23%, heart attacks included (CDC 2019-2022)"),
    "death_dementia": (0.04, 0.09, "share of deaths", "Alzheimer's plus other dementia about 6% as underlying cause (CDC)"),
    "ace_any": (0.58, 0.70, "share of lives reaching 18", "63.9% of US adults report at least one ACE (BRFSS "
                "2011-2020, Swedo et al. 2023)"),
    "ace_4plus": (0.13, 0.21, "share of lives reaching 18", "17.3% report four or more ACEs (Swedo et al. 2023)"),
    "ace_depression_or": (2.5, 6.5, "odds ratio, ever depressed, 4+ ACEs vs none", "OR about 4.4 for depression "
                          "(Hughes et al. 2017 meta-analysis; Felitti et al. 1998 about 4.6)"),
    "phq9_10plus": (0.05, 0.12, "share of adult years scoring 10+", "8.1% of US adults screen positive on the "
                    "PHQ-9 (NCHS Data Brief 303, NHANES 2013-2016)"),
    "death_stroke": (0.04, 0.08, "share of deaths", "about 5% (CDC 2022)"),
}


def one(seed: int, max_years: int = 105) -> dict:
    F = fx.sample(seed)
    p = Person(F, seed, Circle(F, seed))
    ch = Character(p, F)
    keys = collections.Counter()
    good = adult = 0
    stress = collections.defaultdict(lambda: [0, 0])
    partnered = myopic40 = False
    old = frail = home = 0
    phq = [0, 0]
    while p.alive and p.age < max_years * 12:
        p.step_month(F)
        ch.step(p, F)
        for h in p.happenings:
            keys[h.get("key", "")] += 1
        p.happenings.clear()
        y = p.years
        if y >= 18:
            adult += 1
            good += p.s["mood"] > 0.5
            dec = int(y // 10) * 10
            stress[dec][0] += p.economy.stress > 0.5
            stress[dec][1] += 1
        if y >= 18 and p.age % 12 == 0:
            phq[0] += p.mind.phq9(p) >= 10
            phq[1] += 1
        if y >= 65:
            old += 1
            frail += "frailty" in p.illness.active
            home += getattr(p, "residence", "home") == "care_facility"
        if p.family.partner(p.age) is not None:
            partnered = True
        if y < 40 and ("short-sightedness" in p.illness.active or "short-sightedness" in p.illness.done):
            myopic40 = True
    rels = [x.relation for x in p.family.people]
    return {
        "seed": seed, "years": p.years, "alive": p.alive, "cause": p.cause_of_death, "good": good, "adult": adult,
        "married": any(getattr(x, "married", False) for x in p.family.people),
        "partnered": partnered, "affair": keys["affair"] > 0, "ex": "ex_partner" in rels,
        "emigrated": bool(p.economy.emigrated), "dyslexia": bool(getattr(p.mind, "dyslexia", False)),
        "myopic40": myopic40, "old": old, "frail": frail, "home": home,
        "stress": {k: v for k, v in stress.items()},
        "ace": p.ace.score if p.years >= 18 else None, "depressed": bool(p.mind.had.get("depression")), "phq": phq,
    }


def share(rows, key, where=lambda r: True):
    pool = [r for r in rows if where(r)]
    return sum(bool(r[key]) for r in pool) / max(1, len(pool)), len(pool)


def summarise(rows: list) -> dict:
    dead = [r for r in rows if not r["alive"]]
    causes = collections.Counter(r["cause"] for r in dead)

    def cause(*words):
        return sum(n for c, n in causes.items() if any(w in c.lower() for w in words)) / max(1, len(dead))

    def stress(dec):
        a = sum(r["stress"].get(dec, [0, 0])[0] for r in rows)
        b = sum(r["stress"].get(dec, [0, 0])[1] for r in rows)
        return a / max(1, b)

    got = {
        "life_expectancy": st.mean(r["years"] for r in rows),
        "good_mood_months": sum(r["good"] for r in rows) / max(1, sum(r["adult"] for r in rows)),
        "ever_married": share(rows, "married", lambda r: r["years"] >= 45)[0],
        "ever_affair": share(rows, "affair", lambda r: r["partnered"])[0],
        "separated_from_partner": share(rows, "ex", lambda r: r["partnered"])[0],
        "emigrated": share(rows, "emigrated")[0],
        "dyslexia": share(rows, "dyslexia")[0],
        "short_sighted_by_40": share(rows, "myopic40", lambda r: r["years"] >= 40)[0],
        "frail_65plus": sum(r["frail"] for r in rows) / max(1, sum(r["old"] for r in rows)),
        "care_home_65plus": sum(r["home"] for r in rows) / max(1, sum(r["old"] for r in rows)),
        "money_stress_20s": stress(20),
        "money_stress_60s": stress(60),
        "ace_any": share([r for r in rows if r["ace"] is not None], "ace", lambda r: True)[0],
        "ace_4plus": sum(1 for r in rows if (r["ace"] or 0) >= 4) / max(1, sum(r["ace"] is not None for r in rows)),
        "ace_depression_or": odds_ratio(share(rows, "depressed", lambda r: (r["ace"] or 0) >= 4)[0],
                                        share(rows, "depressed", lambda r: r["ace"] == 0)[0]),
        "phq9_10plus": sum(r["phq"][0] for r in rows) / max(1, sum(r["phq"][1] for r in rows)),
        "death_cancer": cause("cancer", "leukaemia", "lymphoma", "tumour", "melanoma"),
        "death_heart": cause("heart"),
        "death_dementia": cause("dementia", "alzheimer"),
        "death_stroke": cause("stroke"),
    }
    lines = []
    for k, (lo, hi, unit, src) in TARGETS.items():
        v = got[k]
        lines.append({"name": k, "value": round(v, 3), "lo": lo, "hi": hi, "unit": unit, "source": src,
                      "ok": lo <= v <= hi})
    return {"lives": len(rows), "when": time.strftime("%Y-%m-%d %H:%M"), "lines": lines,
            "causes": {c: round(n / max(1, len(dead)), 3) for c, n in causes.most_common(15)},
            "money_stress_by_decade": {d: round(stress(d), 3) for d in range(20, 100, 10)}}


def markdown(rep: dict) -> str:
    ok = sum(x["ok"] for x in rep["lines"])
    out = [f"# Population check: {rep['lives']} lives ({rep['when']})", "",
           f"{ok} of {len(rep['lines'])} rates are inside their target range.", "",
           "| Rate | Simulated | Target | Source |", "|---|---|---|---|"]
    for x in rep["lines"]:
        mark = "" if x["ok"] else " ✗"
        out.append(f"| {x['name'].replace('_', ' ')} | {x['value']}{mark} | {x['lo']}–{x['hi']} {x['unit']} | {x['source']} |")
    out += ["", "Top causes of death: " + ", ".join(f"{c} {v:.0%}" for c, v in rep["causes"].items())]
    return "\n".join(out) + "\n"


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    max_years = 90 if "--quick" in sys.argv else 105
    seeds = range(9000, 9000 + n)
    with mp.Pool(max(1, mp.cpu_count() - 2)) as pool:
        rows = pool.starmap(one, [(s, max_years) for s in seeds])
    rep = summarise(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    (OUT / "report.md").write_text(markdown(rep), encoding="utf-8")
    (OUT / "running").unlink(missing_ok=True)               # the UI's "running" flag (ui/server.py)
    sys.stdout.reconfigure(encoding="utf-8")
    print(markdown(rep))


if __name__ == "__main__":
    main()
