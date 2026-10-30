"""The present moment must follow his state, agree with the situation he is in, and always fit in a prompt."""
import random

from vegalife import factors as fx
from vegalife.memory import Memory
from vegalife.people import Circle
from vegalife.present import NOW_BYTES, Moment, Present, problem_scene
from vegalife.scenarios import ALL_SCENARIOS, problem, render_problem, render_scenario_ex
from vegalife.speech import Speech
from vegalife.world import Person

CTX, MAX_NEW = 512, 8


def life(seed=1, years=10, **over):
    F = fx.sample(seed, over)
    c = Circle(F, seed)
    p = Person(F, seed, c)
    while p.alive and p.age < years * 12:
        p.step_month(F)
    return p, F, c


def test_now_line_has_the_moment_and_fits():
    p, F, _ = life(years=9)
    pr = Present(F, 1)
    for _ in range(200):
        m = pr.moment(p, F)
        line = m.line()
        assert line.startswith("Now (9y0m): ") and len(line.encode()) <= NOW_BYTES
        assert m.place in line and "I feel" in line


def test_the_situation_sets_the_scene():
    p, F, _ = life(years=40, shift_work=0.9)
    m = Present(F, 1).moment(p, F, scene="night_shift")
    assert m.place == "at work"
    p, F, _ = life(years=15, bullying=0.9)
    assert Present(F, 1).moment(p, F, scene="bullied").place == "at school"


def test_feelings_follow_his_state():
    p, F, _ = life(years=20)
    pr = Present(F, 1)
    p.s.update(anxiety=0.95, allostatic_load=0.2, felt_loneliness=0.1)
    assert any("scared" in f for f in pr.moment(p, F).feelings)
    p.s.update(anxiety=0.0, allostatic_load=0.0, attachment=0.9, community_support=0.9)
    assert any(w in " ".join(pr.moment(p, F).feelings) for w in ("calm", "loved", "happy"))


def test_what_happened_lately_is_on_his_mind_then_fades():
    p, F, _ = life(years=12)
    pr = Present(F, 1)
    pr.happened(p.age, "Maya moves away", -0.6)
    assert "Maya moving away" in pr.moment(p, F).mind
    p.age += 8                                            # eight months later it is no longer the present
    assert "Maya" not in pr.moment(p, F).mind


def test_friends_are_with_him_at_school():
    friends = [{"name": "Maya", "joined_years": 4, "closeness": 1.0}]
    F = fx.sample(1)
    c = Circle(F, 1, friends)
    p = Person(F, 1, c)
    while p.age < 10 * 12:
        p.step_month(F)
    pr = Present(F, 1)
    withs = [pr.moment(p, F, scene="bullied").with_ for _ in range(50)]
    assert sum("Maya" in w for w in withs) > 25


def test_moment_never_contradicts_itself_for_a_baby():
    p, F, _ = life(years=1)
    for _ in range(100):
        m = Present(F, 1).moment(p, F)
        assert "work" not in m.place and "school" not in m.place


def test_a_prompt_with_now_and_memory_always_fits():
    worst = 0
    for seed in range(1, 5):
        F = fx.sample(seed, {"memory_strength": 1.0, "rumination": 1.0})
        c = Circle(F, seed)
        p = Person(F, seed, c)
        mem, pr, r = Memory(F, seed), Present(F, seed), random.Random(seed)
        while p.alive and p.age < 95 * 12:
            p.step_month(F)
            pr.happened(p.age, "the family is forced to move; friends are left behind", -0.6)
            if p.age % 6:
                continue
            for sc in ALL_SCENARIOS:
                if p.stage in sc.stages:
                    ep = mem.add(p.age, "scenario", sc.key, sc.domain, sc.situation(p, F, r), [], -0.5, 0.8, did_letter="A")
                    ep.detail = ep.strength = 1.0
                    prompt = render_scenario_ex(sc, p, F, r, mem, rehearse=False, now=pr.moment(p, F, r, sc.key).line())[0]
                    worst = max(worst, len(prompt.encode()))
                    assert len(prompt.encode()) + MAX_NEW <= CTX, (sc.key, len(prompt.encode()), prompt)
            q = problem(p, r)
            if q:
                assert len(render_problem(q, p, pr.moment(p, F, r, problem_scene(p)).line()).encode()) + MAX_NEW <= CTX
    assert worst > 300


def test_lessons_and_speech_carry_the_present_in_the_same_format():
    p, F, c = life(years=9)
    sp = Speech(F, 1)
    sp.present = Present(F, 1, sp.kin)
    lessons, life_lines = sp.month_parts(p, F, [], 40000)
    assert sum(x.startswith("Now (9y0m): ") for x in life_lines) >= 3
    assert any(x.startswith("I am ") for x in life_lines)
    assert lessons and all(x.startswith("Now (9y0m): ") for x in lessons)
    assert sp.present.last is not None                   # the month's own moment is the one shown as right now


def test_line_drops_parts_rather_than_overflowing():
    m = Moment(100, "a stormy Wednesday afternoon in September", "at the community centre", "playing cards with everyone",
               ["his partner", "his kids"], "worn out", ["very hopeless", "a bit suspicious"],
               "The family is forced to move and everything is changing at once")
    assert len(m.line().encode()) <= NOW_BYTES and m.line().startswith("Now (8y4m): ")
