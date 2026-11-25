"""Round 3, C3: the world's dated timeline."""
from vegalife import factors as fx
from vegalife.people import Circle
from vegalife.timeline import SCAR, Timeline, birth_year, recession
from vegalife.world import Person


def test_recession_years_follow_the_nber_dates():
    assert recession(2009) == 1.0 and recession(2015) == 0.0 and recession(1981) > 0.5


def test_birth_year_maps_onto_1950_to_2010():
    assert birth_year(fx.sample(1, {"birth_year": 0.0})) == 1950
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
    F = fx.sample(4, {"birth_year": (1990 - 1950) / 60})
    p = Person(F, 4, Circle(F, 4))
    seen = []
    while p.alive and p.age < 25 * 12:
        p.step_month(F)
        seen += [h["text"] for h in p.happenings if h["key"] == "world"]
        p.happenings.clear()
    assert any("internet" in t for t in seen) and any("smartphones" in t for t in seen)
