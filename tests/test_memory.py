"""Memory must fade the way the docstring in memory.py says, keep the truth intact, and fit in a prompt."""
import random
import statistics as st

from vegalife import factors as fx
from vegalife.memory import Memory, fade_lines, retention
from vegalife.people import Circle
from vegalife.scenarios import ALL_SCENARIOS, MEMORY_BYTES, render_scenario_ex
from vegalife.speech import Speech
from vegalife.world import Person

CTX, MAX_NEW = 512, 4
CALM = {"allostatic_load": 0.0, "neurodegeneration": 0.0, "anxiety": 0.0, "community_support": 0.5}


def mem(seed=1, **over):
    return Memory(fx.sample(seed, over), seed)


def add(m, age, key="bullied", valence=-0.7, arousal=0.7, who=("Maya",), **kw):
    return m.add(age, kw.pop("kind", "event"), key, "social", "A group of older kids keep pushing you around at school.",
                 list(who), valence, arousal, did_letter=kw.pop("did_letter", "B"), did_text="tell a teacher", **kw)


def fade(m, months, state=CALM):
    for t in range(months):
        m.step(1000 + t, state)


def test_memories_fade_and_the_true_record_does_not_change():
    m = mem()
    ep = add(m, 120)
    true_before = m.render(ep, true=True)
    s0, d0 = ep.strength, ep.detail
    fade(m, 60)
    assert ep.strength < s0 and ep.detail < d0 and ep.detail < ep.strength     # detail goes before the gist
    assert m.render(ep, true=True) == true_before
    assert ep.who == ["Maya"] and (ep.valence, ep.did_letter, ep.age) == (-0.7, "B", 120)


def test_emotional_events_outlast_dull_ones():
    m = mem()
    big = add(m, 120, key="a", valence=-0.9, arousal=0.9)
    dull = add(m, 120, key="b", valence=0.0, arousal=0.1, who=())
    fade(m, 90)
    assert big.strength > dull.strength and big.detail > dull.detail


def test_rehearsal_slows_forgetting_and_stress_speeds_it():
    m = mem()
    a, b = add(m, 120, key="a"), add(m, 120, key="b")
    b.rehearsals = 5
    fade(m, 60)
    assert b.strength > a.strength
    calm, tense = mem(), mem()
    x, y = add(calm, 120), add(tense, 120)
    fade(calm, 60)
    fade(tense, 60, dict(CALM, allostatic_load=0.9, neurodegeneration=0.5))
    assert y.strength < x.strength


def test_old_enough_and_it_is_gone():
    m = mem()
    add(m, 120, valence=0.0, arousal=0.1, who=())
    fade(m, 400)
    assert m.forgotten >= 1 and not m.episodes


def test_infantile_amnesia():
    m = mem()
    baby, child = add(m, 12, key="a"), add(m, 120, key="b")
    assert baby.strength < 0.2 * child.strength and baby.detail < 0.5


def test_recalled_text_loses_names_and_specifics_as_detail_falls():
    m = mem()
    ep = add(m, 108)
    ep.detail = 1.0
    t1 = m.render(ep)
    assert "Maya" not in t1 and "I chose to tell a teacher" in t1 and "When I was 9" in t1
    ep.detail = 0.6
    t2 = m.render(ep)
    assert "I chose" not in t2 and "about" in t2
    ep.detail = 0.3
    t3 = m.render(ep)
    assert "9" not in t3 and "older kids" not in t3 and "badly" in t3
    ep.detail = 0.1
    assert len(m.render(ep)) < len(t1) and "felt" in m.render(ep)


def test_names_in_the_situation_are_blurred_when_detail_is_low():
    m = Memory(fx.sample(1), 1)
    ep = m.add(100, "scenario", "friend_dare", "social", "Maya dares you to climb the wall.", ["Maya"], -0.5, 0.6,
               did_letter="A", did_text="do it")
    ep.detail = 0.6
    assert "Maya" not in m.render(ep) and "a friend" in m.render(ep)
    assert "Maya" in m.render(ep, true=True)


def test_recalling_strengthens_and_distortion_is_stored_beside_the_truth():
    m = mem(memory_strength=0.9)
    ep = add(m, 120)
    ep.detail = 0.05
    ep.strength = 0.5
    state = dict(CALM, anxiety=1.0, neurodegeneration=0.6)
    s0 = ep.strength
    for _ in range(80):
        m._reconsolidate(ep, state)
        ep.detail = 0.05                              # keep it vague so distortion is likely
    assert ep.strength > s0 and ep.rehearsals == 80
    assert ep.distortion, "a vague memory recalled many times under stress should have been rewritten"
    assert (ep.valence, ep.did_letter) == (-0.7, "B")                 # the truth is untouched
    assert m.render(ep, true=True) != m.render(ep) or ep.distortion


def test_recall_without_rehearse_changes_nothing():
    m = mem()
    ep = add(m, 120)
    ep.strength = 1.0
    before = (ep.strength, ep.rehearsals, ep.distortion)
    for _ in range(50):
        m.recall({"bullied"}, 130, CALM, rehearse=False)
    assert (ep.strength, ep.rehearsals, ep.distortion) == before


def test_recall_follows_cues_and_strength():
    m = mem()
    strong = add(m, 100, key="bullied")
    strong.strength = 1.0
    weak = add(m, 100, key="exam_stress")
    weak.strength = 0.06
    hits = [r.episode_id for _ in range(200) for r in m.recall({"bullied", "exam_stress"}, 120, CALM, rehearse=False)]
    assert hits.count(strong.id) > 3 * max(1, hits.count(weak.id))
    assert not any(m.recall({"nothing_like_this"}, 120, CALM) for _ in range(50))


def test_intrusions_are_vivid_unpleasant_memories():
    m = mem(rumination=1.0)
    bad = add(m, 100, key="bullied", valence=-0.9, arousal=0.95)
    bad.strength = 1.0
    good = add(m, 100, key="finds", valence=0.8, arousal=0.4)
    good.strength = 0.3
    texts = [r.episode_id for _ in range(100) for r in m.reminisce(dict(CALM, anxiety=1.0))]
    assert texts.count(bad.id) > texts.count(good.id)


def test_a_prompt_with_a_memory_always_fits_in_the_context():
    F = fx.sample(2, {"memory_strength": 1.0})
    worst = 0
    for seed in range(1, 6):
        c = Circle(F, seed)
        p = Person(F, seed, c)
        m = Memory(F, seed)
        r = random.Random(seed)
        while p.alive and p.age < 95 * 12:
            p.step_month(F)
            if p.age % 6:
                continue
            for sc in ALL_SCENARIOS:
                if p.stage in sc.stages:
                    ep = m.add(p.age, "scenario", sc.key, sc.domain, sc.situation(p, F, r), [], -0.5, 0.8, did_letter="A")
                    ep.detail = 1.0
                    ep.strength = 1.0
            sc = r.choice([s for s in ALL_SCENARIOS if p.stage in s.stages] or ALL_SCENARIOS)
            prompt, _, recs = render_scenario_ex(sc, p, F, r, m, rehearse=False)
            worst = max(worst, len(prompt.encode()))
            assert all(len(x.text) + 8 <= MEMORY_BYTES for x in recs)
            assert len(prompt.encode()) + MAX_NEW <= CTX, (sc.key, len(prompt.encode()))
    assert worst > 0


def test_memory_lines_have_the_same_format_in_lessons_and_in_questions():
    F = fx.sample(1)
    c = Circle(F, 1)
    p = Person(F, 1, c)
    for _ in range(12 * 9):
        p.step_month(F)
    m = Memory(F, 1)
    for k in ("bullied", "friend_dare", "exam_stress"):
        ep = add(m, 80, key=k)
        ep.strength = 1.0
    sp = Speech(F, 1)
    sp.mem = m
    lessons, life = sp.month_parts(p, F, [], 40000)
    lines = [x for x in lessons + life if "Memory:" in x]
    assert lines and all(x.startswith("Memory: ") or x.split("\n")[1].startswith("Memory: ") for x in lines)


def test_retention_falls_with_age_stress_and_decline():
    F = fx.sample(1)
    r = lambda d, s=CALM: retention(d, s, F)
    assert r(0) > r(24) > r(120) >= 0.1
    assert r(60, dict(CALM, allostatic_load=0.9, neurodegeneration=0.5)) < r(60)


def test_faded_replay_drops_and_shortens_lines():
    rng = random.Random(0)
    lines = [f"line number {i}: " + "x" * 80 for i in range(200)]
    strong = fade_lines(lines, 0.95, rng)
    weak = fade_lines(lines, 0.2, rng)
    assert len(strong) > 150 and len(weak) < 70
    assert st.mean(len(x) for x in weak) < st.mean(len(x) for x in strong)


def test_people_events_become_memories_with_feeling():
    F = fx.sample(1, {"bullying": 1.0})
    p = Person(F, 1, Circle(F, 1))
    pending = []
    while p.age < 15 * 12:
        p.step_month(F)
        pending += p.pending
        p.pending.clear()
    assert pending and all(-1 <= e["valence"] <= 1 and 0 <= e["arousal"] <= 1 for e in pending)
    assert any(e["key"] == "bullied" and e["valence"] < -0.5 for e in pending)
    assert not any("methylation" in e["text"] for e in pending)          # silent biology is not remembered
