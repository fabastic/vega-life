"""School, friends and surroundings must change what happens to him, in the direction their descriptions say."""
import random
import statistics as st

from vegalife import factors as fx
from vegalife.people import Circle
from vegalife.scenarios import ALL_SCENARIOS, draw, render_scenario
from vegalife.speech import Speech
from vegalife.world import Person


def live_to(age_years, seed, overrides=None, friends=None, seed_friends=True):
    F = fx.sample(seed, overrides)
    c = Circle(F, seed, friends, seed_friends)
    p = Person(F, seed, c)
    while p.alive and p.age < age_years * 12:
        p.step_month(F)
    return p, F, c


def mean_at(age, key, overrides, seeds=range(1, 9), **kw):
    return st.mean(live_to(age, s, overrides, **kw)[0].s[key] for s in seeds)


def test_catalogue_has_school_friends_and_surroundings():
    stages = {f["stage"] for f in fx.catalogue()}
    assert {"school", "friends", "surroundings"} <= stages
    assert len(fx.ALL) >= 60


def test_better_school_means_better_results():
    good = mean_at(17.9, "academic", {"school_quality": 0.95, "teacher_warmth": 0.9, "class_crowding": 0.05})
    poor = mean_at(17.9, "academic", {"school_quality": 0.05, "teacher_warmth": 0.1, "class_crowding": 0.95})
    assert good > poor + 0.05, (good, poor)


def test_bullying_raises_stress_and_isolation():
    high = live_to(15, 1, {"bullying": 1.0}), live_to(15, 2, {"bullying": 1.0})
    low = live_to(15, 1, {"bullying": 0.0}), live_to(15, 2, {"bullying": 0.0})
    pick = lambda xs, k: st.mean(x[0].s[k] for x in xs)
    assert pick(high, "allostatic_load") > pick(low, "allostatic_load")
    assert pick(high, "school_belonging") < pick(low, "school_belonging")


def test_degree_costs_money_and_helps_work():
    uni, _, _ = live_to(30, 3, {"higher_ed_path": 1.0})
    none, _, _ = live_to(30, 3, {"higher_ed_path": 0.0})
    assert uni.s["credential"] == 1.0 and none.s["credential"] == 0.0
    assert uni.s["schooling"] == 0.0


def test_listed_friends_are_used_and_close_friends_help():
    friends = [{"name": "Maya", "joined_years": 4, "closeness": 0.9, "kindness": 0.9, "risk": 0.1, "studiousness": 0.8},
               {"name": "Jonas", "joined_years": 5, "closeness": 0.8, "kindness": 0.8, "risk": 0.9, "studiousness": 0.2}]
    with_f = mean_at(14, "community_support", {}, friends=friends)
    without = mean_at(14, "community_support", {}, friends=[], seed_friends=False)
    assert with_f > without + 0.1, (with_f, without)
    p, F, c = live_to(10, 1, friends=friends)
    assert {f.name for f in c.present(p.age)} == {"Maya", "Jonas"}
    assert c.risk(p.age) > 0.3 and c.study(p.age) > 0.3


def test_friends_leave_only_when_you_say_so():
    friends = [{"name": "Maya", "joined_years": 4, "left_years": 9, "closeness": 0.9}]
    p, F, c = live_to(8, 1, friends=friends)
    assert c.present(p.age)
    p, F, c = live_to(10, 1, friends=friends)
    assert not c.present(p.age)


def test_friends_appear_in_his_language_and_situations():
    friends = [{"name": "Maya", "joined_years": 3, "closeness": 0.9, "kindness": 0.9, "risk": 0.9, "studiousness": 0.9}]
    p, F, c = live_to(12, 1, {"peer_risk_culture": 0.9}, friends=friends)
    sp = Speech(F, 1)
    text = "\n".join(sp.month(p, F, [], 20000) for _ in range(3))
    assert "Maya" in text
    seen = set()
    r = random.Random(0)
    for _ in range(400):
        seen |= {x.key for x in draw(p, F, r, 8) if hasattr(x, "choices")}
    assert {"friend_dare", "friend_low"} <= seen
    sc = next(s for s in ALL_SCENARIOS if s.key == "friend_dare")
    assert "Maya" in render_scenario(sc, p, F, r)


def test_curriculum_changes_the_lessons():
    F_math = fx.sample(1, {"curr_math": 1.0, "curr_arts_play": 0.0, "curr_language": 0.0, "curr_social_emotional": 0.0})
    F_arts = fx.sample(1, {"curr_math": 0.0, "curr_arts_play": 1.0, "curr_language": 0.0, "curr_social_emotional": 0.0})
    p, _, _ = live_to(8, 1)
    def count(F, word):
        sp = Speech(F, 1)
        return sum(sp._school(p, F).count(word) for _ in range(300))
    assert count(F_math, "plus") + count(F_math, "times") > count(F_arts, "plus") + count(F_arts, "times")
    assert count(F_arts, "draw") + count(F_arts, "sing") > count(F_math, "draw") + count(F_math, "sing")
