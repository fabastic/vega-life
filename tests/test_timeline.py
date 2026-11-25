"""Round 3, C3: the world's dated timeline."""
from vegalife import factors as fx
from vegalife.people import Circle
from vegalife.timeline import SCAR, Timeline, birth_year, recession
from vegalife.world import Person


def test_recession_years_follow_the_nber_dates():
    assert recession(2009) == 1.0 and recession(2015) == 0.0 and recession(1981) > 0.5


def test_birth_year_maps_onto_1940_to_2010():
    assert birth_year(fx.sample(1, {"birth_year": 0.0})) == 1940
    assert birth_year(fx.sample(1, {"birth_year": 1.0})) == 2010


def test_starting_work_in_a_recession_scars_pay_then_fades():
    t = Timeline(fx.sample(1, {"birth_year": 0.6, "ses": 0.5}))
    t.entered, t.entry_depth = 2008, 1.0
    assert abs(t.scar(2008) - SCAR) < 1e-9
    assert 0 < t.scar(2012) < SCAR
    assert t.scar(2020) == 0.0
    poor = Timeline(fx.sample(1, {"ses": 0.0}))
    poor.entered, poor.entry_depth = 2008, 1.0
    assert poor.scar(2012) > t.scar(2012)          # longer and deeper for the less advantaged


def test_he_lives_through_dated_world_events():
    F = fx.sample(4, {"birth_year": (1990 - 1940) / 70})
    p = Person(F, 4, Circle(F, 4))
    seen = []
    while p.alive and p.age < 25 * 12:
        p.step_month(F)
        seen += [h["text"] for h in p.happenings if h["key"] == "world"]
        p.happenings.clear()
    assert any("internet" in t for t in seen) and any("smartphones" in t for t in seen)


def test_a_long_held_job_lost_costs_years_of_pay():
    t = Timeline(fx.sample(1))
    t.job_since = 0
    t.lost_job(10 * 12)
    assert abs(t.job_scar(10 * 12) - 0.25) < 1e-9
    assert 0.12 < t.job_scar(16 * 12) < 0.2          # about 15% six years on (Jacobson et al. 1993)
    assert t.job_scar(30 * 12) == 0.0
    short = Timeline(fx.sample(1))
    short.job_since = 0
    short.lost_job(12)
    assert short.job_scar(12) < 0.06


def test_hiring_bias_slows_finding_work():
    def months_out(minority):
        total = 0
        for seed in range(30):
            F = fx.sample(seed, {"minority_status": minority, "migrant_background": 0.0, "birth_year": 0.6})
            p = Person(F, seed, Circle(F, seed))
            while p.alive and p.age < 30 * 12:
                p.step_month(F)
                p.happenings.clear()
                total += 22 <= p.years and p.s["employed"] < 0.5 and p.s["schooling"] < 0.5
        return total
    assert months_out(1.0) > months_out(0.0)


def test_a_child_in_the_pandemic_loses_some_learning():
    def academic_at_13(seed, by):
        F = fx.sample(seed, {"birth_year": (by - 1940) / 70})      # birth year draws apart: same life otherwise
        p = Person(F, seed, Circle(F, seed))
        while p.alive and p.age < 13 * 12:
            p.step_month(F)
            p.happenings.clear()
        return p.s["academic"]
    hit = sum(academic_at_13(s, 2008) for s in range(12))
    spared = sum(academic_at_13(s, 1990) for s in range(12))
    assert hit < spared


def test_about_a_quarter_of_men_born_1944_to_1952_are_drafted():
    men = [Timeline(fx.sample(s, {"sex": 1.0, "birth_year": (1948 - 1940) / 70})) for s in range(400)]
    share = sum(t.drafted for t in men) / len(men)
    assert 0.15 < share < 0.35, share
    assert not any(Timeline(fx.sample(s, {"sex": 0.0, "birth_year": (1948 - 1940) / 70})).drafted for s in range(50))
    assert not any(Timeline(fx.sample(s, {"sex": 1.0, "birth_year": 0.5})).drafted for s in range(50))


def test_any_way_of_losing_work_records_the_scar_and_rehire_resets_tenure():
    F = fx.sample(1)
    p = Person(F, 1, Circle(F, 1))
    t = p.timeline
    p.age = 30 * 12
    p.s["employed"] = 1.0
    t.step(p, F)
    assert t.job_since == 30 * 12
    p.age += 8 * 12
    p.s["employed"] = 0.0                      # e.g. prison or illness, not the layoff line
    t.step(p, F)
    assert t.losses and abs(t.losses[-1][1] - 0.25) < 1e-9
    p.age += 12
    p.s["employed"] = 1.0
    t.step(p, F)
    assert t.job_since == 39 * 12


def test_an_older_saved_timeline_resumes():
    import pickle
    t = Timeline(fx.sample(1))
    state = dict(t.__dict__)
    for k in ("job_since", "losses", "drafted", "served_at", "was_employed"):
        state.pop(k)
    old = Timeline.__new__(Timeline)
    old.__setstate__(state)
    assert old.job_scar(100) == 0.0 and old.drafted is False
    assert pickle.loads(pickle.dumps(old)).losses == []


def test_babies_still_get_world_events_without_an_age():
    F = fx.sample(4, {"birth_year": (2006 - 1940) / 70})
    p = Person(F, 4, Circle(F, 4))
    seen = []
    while p.age < 5 * 12:
        p.step_month(F)
        seen += [h["text"] for h in p.happenings if h["key"] == "world"]
        p.happenings.clear()
    assert any("smartphones" in s and "too early" in s for s in seen)
