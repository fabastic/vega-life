"""Round 3, C4 and C5: parenting styles and adverse childhood experiences."""
from vegalife import factors as fx
from vegalife.ace import Ace, odds_ratio
from vegalife.people import Circle
from vegalife.world import Person


def grow(seed, overrides=None, years=18):
    F = fx.sample(seed, overrides)
    p = Person(F, seed, Circle(F, seed))
    while p.alive and p.age < years * 12:
        p.step_month(F)
        p.happenings.clear()
    return p, F


def test_parenting_style_follows_warmth_and_strictness():
    style = lambda w, s: Person(fx.sample(1, {"caregiver_warmth": w, "parent_strictness": s}), 1, None) \
        .parenting_style(fx.sample(1, {"caregiver_warmth": w, "parent_strictness": s}))
    assert style(0.9, 0.9) == "authoritative"
    assert style(0.1, 0.9) == "authoritarian"
    assert style(0.9, 0.1) == "permissive"
    assert style(0.1, 0.1) == "neglectful"


def test_harsher_homes_carry_more_aces():
    hard = sum(Ace(fx.sample(s, {"ses": 0.05, "caregiver_warmth": 0.1}), s).adversity for s in range(50))
    soft = sum(Ace(fx.sample(s, {"ses": 0.95, "caregiver_warmth": 0.95}), s).adversity for s in range(50))
    assert hard > 2 * soft


def test_aces_land_before_18_and_stop():
    p, _ = grow(3, {"ses": 0.05, "caregiver_warmth": 0.1}, years=25)
    assert p.ace.score >= 1
    assert not p.ace.plan
    assert all(k for k in p.ace.had)


def test_aces_raise_adult_depression_hazard_only():
    a = Ace(fx.sample(1), 1)
    a.had = ["emotional_abuse"] * 4
    assert a.hazard("depression") > 0.5 and a.hazard("alcohol use") > 0.5
    assert a.hazard("psychosis") == 0.0
    a.off = True
    assert a.hazard("depression") == 0.0


def test_odds_ratio():
    assert abs(odds_ratio(0.5, 0.2) - 4.0) < 1e-9


def test_every_ace_delta_is_a_real_state():
    from vegalife.ace import CATS
    p = Person(fx.sample(1), 1, None)
    for _, _, d in CATS.values():
        assert set(d) <= set(p.s), set(d) - set(p.s)


def test_a_resumed_life_does_not_replay_its_childhood():
    a = Ace(fx.sample(3, {"ses": 0.05, "caregiver_warmth": 0.1}), 3, start_month=20 * 12)
    assert a.partial and not a.plan


def test_depression_screen_is_in_range_and_rises_when_depressed():
    p, _ = grow(1, years=30)
    base = p.mind.phq9(p)
    assert 0 <= base <= 27
    p.mind.active["depression"] = p.age
    p.s["mood"] = 0.1
    assert p.mind.phq9(p) >= 10 > base or p.mind.phq9(p) > base


def test_abuse_at_home_teaches_people_are_not_safe():
    p = Person(fx.sample(3), 3, Circle(fx.sample(3), 3))
    moved = p.beliefs.evidence(p, "ace", -0.8, 0.85, "is hit at home")
    assert moved["people_trustworthy"] < 0 and moved["self_worth"] < 0
