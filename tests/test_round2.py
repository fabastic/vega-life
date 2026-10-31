"""Round 2: events change state (affairs, separations, households, care homes, dyslexia, being there for people),
named deaths, recovery and lasting personality change, the money loop, surroundings as doses, and the model-side
pieces (scoring by meaning, fading templates, the network map, the probe, the fork lab)."""
import json
import math
import random

import pytest
import torch

from vegalife import factors as fx
from vegalife.character import Character, plasticity
from vegalife.family import Relative
from vegalife.people import Circle
from vegalife.world import Person


def _person(seed=5, years=0, **over):
    F = fx.sample(seed, over or None)
    p = Person(F, seed, Circle(F, seed))
    ch = Character(p, F)
    while p.alive and p.age < years * 12:
        p.step_month(F)
        ch.step(p, F)
        p.happenings.clear()
    return p, F, ch


def _partnered(seed=5, married=False):
    p, F, ch = _person(seed, 30)
    pt = Relative("Sam", "partner", p.age - 360, 0.8, joined=p.age - 60)
    pt.cohabiting, pt.married = True, married
    p.family.people = [x for x in p.family.people if x.relation != "partner"] + [pt]
    return p, F, ch, pt


def test_an_affair_weighs_on_him_and_discovery_can_end_the_marriage():
    p, F, ch, pt = _partnered(married=True)
    p.bonds.step(p, F)
    b = p.bonds.bonds["Sam"]
    p.bonds.affair = {"partner": "Sam", "since": p.age}
    before = p.conscious.guilt
    b.trust = 0.0                                          # a partner who already distrusts him finds out fast
    out = []
    for _ in range(40):
        out += p.bonds._affair(p, F)
        if p.bonds.affair is None:
            break
    assert any("finds out" in h["text"] for h in out) or p.conscious.guilt > before
    if any("finds out" in h["text"] for h in out):
        assert b.crisis_until > p.age and b.pattern == "contempt"


def test_separating_splits_the_household_and_leaves_an_ex():
    p, F, ch, pt = _partnered(married=True)
    p.s["wealth"] = 0.6
    kid = Relative("Ivy", "child", p.age - 24, 0.9, joined=p.age - 24)
    p.family.people.append(kid)
    h = p.family.separate(p, pt)
    assert "divorce" in h["text"] and pt.relation == "ex_partner" and not pt.gone       # they share a child
    assert p.s["wealth"] < 0.6 and not p.family.pooled(p.age)


def test_living_together_pools_money():
    p, F, ch, pt = _partnered()
    q = p.clone()
    q.family.partner(q.age).cohabiting = False
    for _ in range(12):
        p.step_month(F)
        q.step_month(F)
    assert p.family.pooled(p.age) and not q.family.pooled(q.age)


def test_a_care_home_changes_where_and_how_he_lives():
    p, F, ch = _person(7, 0)
    p.age = 85 * 12
    p.residence = "care_facility"
    p.s["autonomy"], p.s["employed"] = 0.9, 1.0
    p.seasons._care_home(p, F)
    assert p.s["autonomy"] <= 0.35 and p.s["employed"] == 0.0 and p.work.retired


def test_dyslexia_slows_reading_unless_supported():
    p, F, ch = _person(8, 9)
    q = p.clone()
    p.mind.dyslexia, q.mind.dyslexia = True, False
    p.mind.diagnosed["dyslexia"] = q.mind.diagnosed["dyslexia"] = None
    p.school.tutored = q.school.tutored = False
    for _ in range(24):
        p.school.tutored = q.school.tutored = False
        p.school.step(p, F)
        q.school.step(q, F)
    assert p.school.grades["literature"] < q.school.grades["literature"]


def test_showing_up_deepens_a_bond_and_staying_away_cools_it():
    p, F, ch = _person(9, 30)
    f = next(iter(p.circle.present(p.age)), None)
    if f is None:
        pytest.skip("no friend in this life")
    p.bonds.step(p, F)
    b = p.bonds.bonds[f.name]
    t0 = b.trust
    p.s["agreeableness"], p.work.hours = 1.0, 30
    f.closeness = 1.0
    shown = p.bonds.their_event(p, F, f, "illness")
    assert (shown[0]["key"] == "there_for" and b.trust > t0) or (shown[0]["key"] == "absent" and b.trust < t0)


def test_teen_pregnancy_goes_through_the_whole_pregnancy():
    p, F, ch = _person(10, 16, sex=0.0)
    h = p.family.conceive(p, "finds out she is pregnant at 16", teen=True)
    assert p.family.expecting == p.age + 9 and h["key"] == "child"


def test_every_death_has_a_named_cause():
    for seed in range(40, 52):
        p, F, ch = _person(seed, 110)
        assert p.cause_of_death and p.cause_of_death not in ("natural causes", "his body gave out")


def test_lasting_events_shape_personality_more_in_youth():
    young, F, ch_y = _person(11, 10)
    old, G, ch_o = _person(11, 40)
    ch_y.nudge(young, "bullied", -0.8, 0.8)
    ch_o.nudge(old, "bullied", -0.8, 0.8)
    assert ch_y.formed["neuroticism"] > ch_o.formed["neuroticism"] > 0
    assert plasticity(10) == 1.0 and plasticity(30) < 0.2


def test_small_setbacks_are_adapted_to_within_months():
    p, F, ch = _person(12, 30)
    base = p.s["mood_baseline"]
    p.s["mood_baseline"] = base + 0.2                      # life just got worse than what he is used to
    ch.step(p, F)
    assert p.s["mood_baseline"] < base + 0.2 - 0.2 / 9


def test_occupation_record_and_care_by_money():
    p, F, ch = _person(13, 25, region=0.0)                  # North America: care costs money
    p.economy.stress = 0.0
    calm = p.care(F)
    p.economy.stress = 1.0
    assert p.care(F) < calm
    q, G, _ = _person(13, 25, region=0.3)                   # Nordic countries: care is universal
    q.economy.stress = 1.0
    assert abs(q.care(G) - G["healthcare_access"]) < 1e-9
    p.economy.tier = None
    p.hardships.record = True
    out = []
    p.economy._place(p, F, out)
    assert p.economy.tier is not None and "starts work as" in out[0]["text"]


def test_emigrating_changes_country_and_background():
    p, F, ch = _person(14, 30, region=0.6)                  # Sub-Saharan Africa
    out = []
    p.economy._emigrate(p, F, "Sub-Saharan Africa", out)
    assert F["migrant_background"] == 1.0 and p.economy.emigrated["to"] in ("Western Europe", "North America",
                                                                             "Middle East and North Africa")


def test_surroundings_lead_and_city_childhood():
    clean, F, _ = _person(15, 7, lead_exposure=0.0)
    leaded, G, _ = _person(15, 7, lead_exposure=1.0)
    assert leaded.school.iq < clean.school.iq - 5             # ~7 points at 30 ug/dL (Lanphear 2005)
    city, H, _ = _person(16, 18, urbanicity=1.0)
    rural, K, _ = _person(16, 18, urbanicity=0.0)
    assert city.surroundings.mental_risk()["psychosis"] > rural.surroundings.mental_risk()["psychosis"]


def test_self_answers_are_scored_by_meaning():
    from vegalife.selftalk import SelfQuestion, candidates, numbers_in, score_self
    q = SelfQuestion("self_age", "", 21)
    assert numbers_in("I am twenty-one") == [21] and score_self(q, "Twenty one!") == 1.0
    assert score_self(q, "I am 20, no 21") == 0.4 and score_self(q, "hmm") == -0.3
    assert score_self(q, "I am 21.", closest=0.0) == pytest.approx(0.6)
    assert candidates(q)[q.answer - max(0, q.answer - 2)] == "I am 21."


def test_template_thoughts_fade_into_his_own_state():
    from vegalife.conscious import feel_vector, template_share
    p, F, ch = _person(17, 30)
    assert template_share(2) == 1.0 and template_share(7) == 0.0
    assert feel_vector(p).startswith("mood ") and "guilt" in feel_vector(p)


def test_network_map_and_probe():
    from vegalife.cortex import Cortex, Probe
    from vegalife.model import Mind, Shape
    m = Mind(Shape(64, 3, 64))
    cx = Cortex()
    cx.attach(m)
    cx.recording = True
    x = torch.randint(0, 255, (2, 32))
    loss = m(x).float().mean()
    loss.backward()
    snap = cx.snapshot(m, 1.0)
    assert len(snap["nodes"]) == 2 * 3 + 2 and any(n["act"] > 0 for n in snap["nodes"])
    pr, g = Probe(), torch.Generator().manual_seed(0)
    w = torch.randn(16, generator=g)
    r2 = None
    for _ in range(60):
        h = torch.randn(16, generator=g)
        r2 = pr.add(h, [float(torch.sigmoid(h @ w))] * 5)
    assert r2 is not None and r2 > 0.5


def test_fork_lab_parses_arms():
    from vegalife.experiment import parse_arm
    a = parse_arm("poor:state.wealth=0.02,ses=0.1,ablate=conscience,remove=mother")
    assert a["state"] == {"wealth": 0.02} and a["factors"] == {"ses": 0.1}
    assert a["ablate"] == ["conscience"] and a["remove"] == ["mother"]
    with pytest.raises(SystemExit):
        parse_arm("bad:nonsense=1")


def test_fork_lab_runs_two_arms(tmp_path, monkeypatch):
    from vegalife.experiment import compare, fork, measure, parse_arm, run_arm
    from vegalife.trainer import Life
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    src = tmp_path / "base"
    src.mkdir()
    fast = {"max_items_per_month": 1, "max_lm_steps_per_month": 1, "group_size": 2, "speech_bytes_per_month": 3000,
            "eval_every_months": 3, "checkpoint_months": 3, "replay_steps": 1}
    (src / "config.json").write_text(json.dumps({"seed": 3, "profile": "tiny", "max_age_years": 0.5, "sim": fast}))
    Life(src).run()
    results = {}
    for spec in ("control", "noconscience:ablate=conscience,state.wealth=0.0"):
        arm = parse_arm(spec)
        dst = fork(src, arm, "ex", 3)
        assert run_arm(dst, "cpu") == 0
        results[arm["name"]] = measure(dst)
    d = compare(results)
    assert results["noconscience"]["ablate"] == ["conscience"] and results["noconscience"]["wealth"] <= 0.05
    assert d["control"]["self_model_overlap"] == 1.0
