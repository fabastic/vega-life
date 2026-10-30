"""Growth must not change what the model computes; the world and the reward plumbing must hold together."""
import random

import torch

from vegalife import factors as fx
from vegalife.growth import PROFILES, SCHEDULE, target_shape
from vegalife.model import Mind, Shape, param_count
from vegalife.rlvr import parse_choice, parse_int, score_problem, score_scenario
from vegalife.scenarios import ALL_SCENARIOS, Problem, draw, render_scenario
from vegalife.world import Person


def _logits_after(grow_to):
    torch.manual_seed(0)
    m = Mind(Shape(128, 2)).double()
    for p in m.parameters():                 # train-like weights, not the init
        p.data.add_(torch.randn_like(p) * 0.05)
    for mod in m.modules():                  # eps is the only thing growth cannot preserve exactly
        if hasattr(mod, "eps"):
            mod.eps = 1e-14
    x = torch.randint(0, 256, (2, 40))
    before = m(x)
    m.grow(grow_to)
    after = m(x)
    return before, after, m


def test_width_growth_preserves_function():
    before, after, m = _logits_after(Shape(256, 2))
    assert m.shape.d == 256 and m.shape.heads == 4
    assert torch.allclose(before, after, atol=1e-8), (before - after).abs().max()


def test_depth_growth_preserves_function():
    before, after, m = _logits_after(Shape(128, 5))
    assert len(m.blocks) == 5
    assert torch.allclose(before, after, atol=1e-9)


def test_width_and_depth_growth_preserves_function():
    before, after, _ = _logits_after(Shape(384, 6))
    assert torch.allclose(before, after, atol=1e-8)


def test_grown_model_still_learns_on_new_units():
    _, _, m = _logits_after(Shape(256, 3))
    x = torch.randint(0, 256, (2, 20))
    m(x).sum().backward()
    assert m.blocks[0].proj.weight.grad[128:].abs().sum() > 0      # writes into new residual dims get gradient


def test_schedule_reaches_about_a_billion():
    last = Shape(SCHEDULE[-1][1], SCHEDULE[-1][2])
    assert 0.95e9 < param_count(last) < 1.1e9
    assert param_count(target_shape(40, 0, PROFILES["laptop"], 512)) <= PROFILES["laptop"]
    assert target_shape(0, 0, PROFILES["full"], 512).d == 128


def test_factors_seed_and_override():
    a, b = fx.sample(3), fx.sample(3)
    assert a.values == b.values
    c = fx.sample(3, {"caregiver_phubbing": 0.9})
    assert c["caregiver_phubbing"] == 0.9 and c.source["caregiver_phubbing"] == "user"
    t = fx.sample(3, timeline=[{"age_years": 1, "key": "ai_scams", "value": 1.0}])
    assert t.apply_timeline(12) and t["ai_scams"] == 1.0


def test_a_whole_life_runs_without_the_model():
    F = fx.sample(5)
    p = Person(F, 5)
    r = random.Random(0)
    seen = set()
    while p.alive and p.age < 95 * 12:
        p.step_month(F)
        for item in draw(p, F, r, 6):
            if isinstance(item, Problem):
                assert score_problem(item, str(item.answer)) == 1.0
            else:
                seen.add(item.key)
                render_scenario(item, p, F, r)
                score_scenario(item, p, F, r.randrange(4), r)
        for v in p.s.values():
            assert 0.0 <= v <= 1.0
    assert len(seen) > len(ALL_SCENARIOS) // 2


def test_parsers():
    assert parse_choice(" B because") == 1 and parse_choice("x") == -1
    assert parse_int(" 42\n") == 42 and parse_int("no") is None
