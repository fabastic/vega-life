"""Options are shown in a new order each time, so he learns choices, not letters (vega-7 picked D in 180 of 188
childhood situations while D was the best option in only a few)."""
import random

from vegalife import factors as fx
from vegalife.memory import Memory
from vegalife.people import Circle
from vegalife.scenarios import ALL_SCENARIOS, render_scenario_ex, shuffled_order
from vegalife.world import Person


def test_the_order_changes_and_letters_map_back_to_the_right_choice():
    F = fx.sample(3)
    p = Person(F, 3, Circle(F, 3))
    sc = next(s for s in ALL_SCENARIOS if len(s.choices) >= 3)
    r = random.Random(0)
    orders = set()
    for _ in range(30):
        order = shuffled_order(sc, r)
        orders.add(tuple(order))
        prompt = render_scenario_ex(sc, p, F, r, now="Now (1): here", order=order)[0]
        for i, j in enumerate(order):
            assert f"{'ABCD'[i]}) {sc.choices[j].text}" in prompt
    assert len(orders) > 1
    assert sorted(next(iter(orders))) == list(range(len(sc.choices)))


def test_he_remembers_what_he_did_in_words():
    F = fx.sample(2)
    m = Memory(F, 2)
    ep = m.add(120, "scenario", "bullied", "social", "A boy pushes you.", [], 0.5, 0.9, did_letter="B", did_text="hit back")
    assert "I chose to hit back." in m.render(ep, true=True)
