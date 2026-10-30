"""The simulated world must stay roughly in line with the published numbers in CALIBRATION.md.

A cheap version of tools/calibrate.py (fewer lives, wider bounds) so a change that breaks realism fails the suite.
"""
import importlib.util
import statistics as st
from pathlib import Path

spec = importlib.util.spec_from_file_location("calibrate", Path(__file__).resolve().parent.parent / "tools" / "calibrate.py")
cal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)
SEEDS = range(1, 71)


def test_life_expectancy_is_near_the_us_figure():
    ages = [a for a, _ in cal.lifespans(seeds=SEEDS)]
    assert 73 <= st.mean(ages) <= 84, st.mean(ages)


def test_richer_families_live_longer_by_years_not_decades():
    gap = cal.mean_age(cal.lifespans({"ses": 0.95}, SEEDS)) - cal.mean_age(cal.lifespans({"ses": 0.05}, SEEDS))
    assert 3 <= gap <= 18, gap


def test_pollution_costs_a_few_years():
    # measured from hazards: comparing ages at death would need thousands of lives to see a 3-year effect
    loss = cal.years_from_hazard(cal.lifespans({"local_pollution": 0.0}, SEEDS), cal.lifespans({"local_pollution": 1.0}, SEEDS))
    assert 1.0 <= loss <= 5.0, loss
