"""Death and grief, body chemistry, children and work: each must stay near what the research says, across lives."""
import collections
import random

from vegalife import factors as fx
from vegalife.character import Character
from vegalife.family import Family, monthly_death_risk
from vegalife.memory import Memory
from vegalife.people import Circle
from vegalife.present import Present
from vegalife.selftalk import facts, self_question
from vegalife.speech import Speech
from vegalife.world import Person


def _lives(n, years=85):
    out = []
    for seed in range(n):
        F = fx.sample(seed)
        p = Person(F, seed, Circle(F, seed))
        ch = Character(p, F)
        moods = []
        while p.alive and p.age < years * 12:
            p.step_month(F)
            ch.step(p, F)
            p.happenings.clear()
            p.pending.clear()
            if p.age % 6 == 0:
                moods.append(p.s["mood"])
        out.append((p, moods))
    return out


LIVES = None


def lives():
    global LIVES
    if LIVES is None:
        LIVES = _lives(120)
    return LIVES


def test_death_rates_follow_life_tables():
    assert 0.002 < monthly_death_risk(50) * 12 < 0.006
    assert 0.03 < monthly_death_risk(80) * 12 < 0.08


def test_grief_paths_match_bereavement_research():
    paths = collections.Counter(l.path for p, _ in lives() for l in p.family.losses
                                if l.kind == "death" and l.weight >= 0.7)
    n = sum(paths.values())
    assert n > 100
    assert 0.38 < paths["resilient"] / n < 0.65          # Bonanno: about half resilient
    assert 0.06 < paths["prolonged"] / n < 0.25          # Bonanno 15.6% chronic; Lundorff PGD ~10%


def test_he_is_mostly_okay_most_of_the_time():
    moods = [m for _, ms in lives() for m in ms]
    good = sum(m > 0.5 for m in moods) / len(moods)
    assert 0.6 < good < 0.88                             # Gallup: 74% have more positive than negative days


def test_children_and_partners_are_common_but_not_universal():
    kids = [sum(1 for x in p.family.people if x.relation == "child") for p, _ in lives() if p.years > 50]
    none = kids.count(0) / len(kids)
    assert 0.12 < none < 0.45 and 1.0 < sum(kids) / len(kids) < 2.5


def test_work_has_searches_promotions_and_mostly_normal_hours():
    ps = [p for p, _ in lives() if p.years > 66]
    assert sum(p.work.level for p in ps) / len(ps) > 1.0
    assert sum(p.work.retired for p in ps) / len(ps) > 0.5


def test_a_scheduled_death_happens_when_you_say_and_starts_grief():
    F = fx.sample(3)
    fam = [{"relation": "mother", "name": "Mum", "age_at_his_birth": 30, "closeness": 0.95, "dies_at_years": 10}]
    p = Person(F, 3, Circle(F, 3), fam)
    while p.age < 10 * 12 + 2:
        p.step_month(F)
        p.happenings.clear()
        p.pending.clear()
    mum = p.family.people[0]
    assert not mum.alive and mum.died == 120 and p.s["grief"] > 0.1
    assert p.family.losses[0].who == "Mum" and p.s["caregiver_attention"] < 0.9


def test_good_moments_release_chemistry_and_become_memories():
    F = fx.sample(5)
    p = Person(F, 5, Circle(F, 5))
    joys = 0
    for _ in range(60):
        p.step_month(F)
        joys += sum(1 for h in p.happenings if h["key"] == "joy")
        p.happenings.clear()
        p.pending.clear()
    assert joys > 10
    assert all(0 <= p.s[k] <= 1 for k in ("dopamine", "oxytocin", "serotonin", "endorphins", "cortisol", "joy"))


def test_self_knowledge_answers_are_true():
    F = fx.sample(9)
    p = Person(F, 9, Circle(F, 9))
    ch = Character(p, F)
    for _ in range(30 * 12):
        p.step_month(F)
        ch.step(p, F)
        p.happenings.clear()
        p.pending.clear()
    r = random.Random(1)
    pr = Present(F, 9, Speech(F, 9).kin)
    qa = dict(facts(p, pr.moment(p, F, r, keep=False), Memory(F, 9), r))
    assert qa["How old are you?"] == "I am 30."
    kids = [x for x in p.family.people if x.relation == "child" and x.alive]
    assert ("Yes" in qa["Do you have children?"]) == bool(kids)
    sq = self_question(p, F, pr, "Vega", r)
    assert sq.prompt.endswith("Vega:") and isinstance(sq.answer, int)


def test_a_self_answer_counts_when_its_number_is_true():
    from vegalife.selftalk import SelfQuestion, score_self
    q = SelfQuestion("self_age", "p", 16)
    assert score_self(q, " I am 16.") == 1.0 and score_self(q, " 16") == 1.0
    assert score_self(q, " I am 15.") == 0.0 and score_self(q, " hello") < 0
