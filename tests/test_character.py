"""Each human mechanism must push in the direction the research says. These test direction, not size."""
import random
import statistics as st

from vegalife import factors as fx
from vegalife.character import TRAITS, Character, learning_plasticity
from vegalife.memory import Memory
from vegalife.people import Circle
from vegalife.rlvr import outcome, score_scenario
from vegalife.scenarios import ALL_SCENARIOS, LATER
from vegalife.world import Person


def grow(years, seed=1, **over):
    F = fx.sample(seed, over)
    p = Person(F, seed, Circle(F, seed))
    ch = Character(p, F)
    while p.alive and p.age < years * 12:
        p.step_month(F)
        ch.step(p, F)
        for m in p.pending:
            ch.nudge(p, m["key"], m["valence"])
        p.pending.clear()
    return p, F, ch


def sc(key):
    return next(s for s in ALL_SCENARIOS if s.key == key)


def test_later_consequences_are_attached_to_the_choices_they_describe():
    expect = {("party", 0): "whatever they do", ("essay_due", 1): "write it yourself", ("junior_work", 1): "senior",
              ("night_shift", 3): "on top of", ("move_out", 3): "borrow", ("exam_stress", 0): "through the night",
              ("doom_feed", 0): "scrolling", ("getting_to_school", 1): "walk"}
    for (key, i), word in expect.items():
        c = sc(key).choices[i]
        assert word in c.text and c.later and c.delay >= 1
    assert all((s.key, i) in {(s.key, j) for j in range(4)} for (k, i) in LATER for s in ALL_SCENARIOS if s.key == k)


def test_losses_are_felt_more_than_gains():
    p, F, ch = grow(30)
    assert ch.felt(p, -0.01, 0, 0) < -1.4 * ch.felt(p, 0.01, 0, 0)
    calm_p, _, calm = grow(30, trait_neuroticism=0.0)
    anx_p, _, anx = grow(30, trait_neuroticism=1.0)
    assert anx.loss_aversion(anx_p) > calm.loss_aversion(calm_p)
    assert 1.5 <= calm.loss_aversion(calm_p) <= 2.1 and 1.5 <= anx.loss_aversion(anx_p) <= 2.1


def test_a_teenager_discounts_the_future_more_than_an_adult():
    teen, _, ch_t = grow(15)
    adult, _, ch_a = grow(35)
    # a choice that feels fine now but costs later
    assert ch_t.felt(teen, 0.0, -0.01, 3) > ch_a.felt(adult, 0.0, -0.01, 3)
    assert ch_t.present_bias(teen)[0] < ch_a.present_bias(adult)[0]


def test_real_outcome_counts_later_costs_in_full_and_felt_does_not():
    p, F, ch = grow(16)
    party = sc("party")
    r = random.Random(0)
    now, later = outcome(party, p, F, 0, r, draws=20)
    assert later < 0
    real = st.mean(score_scenario(party, p, F, 0, random.Random(i)) for i in range(30))
    felt_later_only = ch.felt(p, 0.0, later, party.choices[0].delay)
    assert abs(felt_later_only) < abs(later * 2.1)                   # discounted, even after loss aversion
    assert -1 <= real <= 1


def test_novelty_only_enters_the_felt_score():
    p, F, ch = grow(14)
    s = sc("tablet_freezes") if p.stage in sc("tablet_freezes").stages else sc("doom_feed")
    a = score_scenario(s, p, F, 1, random.Random(1), character=ch, novelty=lambda c: 0.2)
    b = score_scenario(s, p, F, 1, random.Random(1), character=ch, novelty=lambda c: 0.0)
    real = score_scenario(s, p, F, 1, random.Random(1))
    assert abs((a - b) - 0.2) < 1e-6 or a == 1.0
    assert real == score_scenario(s, p, F, 1, random.Random(1), novelty=lambda c: 0.5)   # ignored without a character


def test_personality_is_formed_by_life_and_matures():
    rough, _, _ = grow(18, seed=2, bullying=1.0, household_stress=1.0, structural_violence=1.0, caregiver_warmth=0.1)
    kind, _, _ = grow(18, seed=2, bullying=0.0, household_stress=0.0, structural_violence=0.0, caregiver_warmth=0.95)
    assert rough.s["neuroticism"] > kind.s["neuroticism"]
    assert kind.s["agreeableness"] > rough.s["agreeableness"]
    young = [grow(20, seed=s)[0].s["neuroticism"] for s in range(1, 6)]
    old = [grow(60, seed=s)[0].s["neuroticism"] for s in range(1, 6)]
    assert st.mean(old) < st.mean(young)                             # emotional stability rises with age


def test_innate_seed_matters_but_does_not_decide_alone():
    lo, _, _ = grow(30, trait_extraversion=0.0)
    hi, _, _ = grow(30, trait_extraversion=1.0)
    assert hi.s["extraversion"] > lo.s["extraversion"] + 0.2
    assert hi.s["extraversion"] < 0.95 and lo.s["extraversion"] > 0.05


def test_traits_settle_after_25():
    p, F, ch = grow(14)
    before = dict(p.s)
    ch.nudge(p, "bullied", -0.7)
    young_shift = before["neuroticism"] - p.s["neuroticism"]
    q, G, ch2 = grow(40)
    before2 = dict(q.s)
    ch2.nudge(q, "bullied", -0.7)
    assert abs(young_shift) > abs(before2["neuroticism"] - q.s["neuroticism"])


def test_shift_work_and_worry_cost_sleep():
    good = st.mean(grow(40, seed=s, shift_work=0.0)[0].s["sleep"] for s in range(1, 5))
    bad = st.mean(grow(40, seed=s, shift_work=1.0)[0].s["sleep"] for s in range(1, 5))
    assert bad < good


def test_sleep_strengthens_the_last_months_salient_memories_only():
    F = fx.sample(1)
    m = Memory(F, 1)
    old = m.add(100, "event", "a", "social", "x", [], -0.8, 0.9)
    new = m.add(200, "event", "b", "social", "y", [], -0.8, 0.9)
    baby = m.add(12, "event", "c", "social", "z", [], -0.8, 0.9)
    old.strength = new.strength = baby.strength = 0.3
    m.consolidate(200, sleep=1.0)
    assert new.strength > 0.3 and old.strength == 0.3 and baby.strength == 0.3


def test_mood_adapts_partly_to_circumstances():
    p, F, ch = grow(30)
    q = p.clone()
    for _ in range(49):
        ch.step(q, F)                                                # the same life without the windfall
    p.s.update(wealth=1.0, employed=1.0, housing=1.0, community_support=0.9)
    ch.step(p, F)
    jump = p.s["mood"]
    for _ in range(48):
        ch.step(p, F)
    assert p.s["mood"] < jump                                        # gets used to it...
    assert p.s["mood"] > q.s["mood"] + 0.03                          # ...but not completely


def test_stress_narrows_the_lived_choice_and_tiredness_loosens_it():
    p, F, ch = grow(30)
    p.s.update(anxiety=0.0, allostatic_load=0.0, sleep=1.0)
    calm = ch.decision_temperature(p)
    p.s.update(anxiety=0.9)
    stressed = ch.decision_temperature(p)
    p.s.update(anxiety=0.0, sleep=0.2)
    tired = ch.decision_temperature(p)
    assert stressed < calm < tired


def test_language_window_stays_open_to_17_then_narrows():
    assert learning_plasticity(5) == learning_plasticity(16.9) == 1.0
    assert learning_plasticity(25) < 1.0 and learning_plasticity(60) < learning_plasticity(25)


def test_consequences_arrive_later_and_are_remembered():
    p, F, ch = grow(16)
    acad = p.s["academic"]
    p.schedule(3, {"academic": -0.05}, "pays the price: go and do whatever they do", -0.4)
    for _ in range(2):
        p.step_month(F)
    assert not any(m["key"] == "consequence" for m in p.pending)
    p.pending.clear()
    p.step_month(F)
    assert any(m["key"] == "consequence" for m in p.pending)
