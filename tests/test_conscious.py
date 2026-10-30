"""His awareness and his conscience: thoughts he can report, a self-model that is true, a moral sense that grows,
and learning that concentrates on what he says."""
import random

from vegalife import factors as fx
from vegalife.character import Character
from vegalife.lifecore import world_month
from vegalife.memory import Memory
from vegalife.model import answer_weights, encode
from vegalife.people import Circle
from vegalife.present import Present, as_his_own
from vegalife.speech import Speech
from vegalife.world import Person


class _L:
    pass


def _life(seed=9, years=30):
    F = fx.sample(seed)
    L = _L()
    L.p, L.F = Person(F, seed, Circle(F, seed)), F
    L.character, L.present, L.mem, L.brain = Character(L.p, F), Present(F, seed, Speech(F, seed).kin), Memory(F, seed), None
    L.say = lambda t: None
    for _ in range(years * 12):
        world_month(L)
        L.character.step(L.p, F)
    return L


def test_he_has_thoughts_and_a_true_self_model():
    L = _life()
    cs = L.p.conscious
    assert 1 <= len(cs.thoughts) <= 3 and all(t.endswith((".", "!")) or "..." in t for t in cs.thoughts)
    kids = any(x.relation == "child" for x in L.p.family.people)
    assert ("I am a father." in cs.self_model) == kids
    assert cs.line().startswith("Thought: ")


def test_conscience_grows_with_age_and_weighs_harm_more_than_help():
    F = fx.sample(1)
    p = Person(F, 1, Circle(F, 1))
    cs = p.conscious
    young = cs.moral_sense(p, F)
    p.age = 20 * 12
    p.s["pfc_maturity"] = 0.9
    old = cs.moral_sense(p, F)
    assert young < 0.05 < old
    assert cs.weigh(p, F, "hit back") < 0 < cs.weigh(p, F, "comfort your little brother")
    assert cs.weigh(p, F, "take the bus") == 0
    cs.after(p, F, "hit back")
    assert cs.guilt > 0 and cs.last_deed[1] < 0


def test_learning_weights_his_own_replies():
    data = encode("Now (30y0m): at home.\nYou: How old are you?\nVega: I am 30.\nMum: Dinner!")
    w = answer_weights(data, 8.0)
    text = bytes(data).decode()
    i = text.index("I am 30.")
    assert w[i] == 8.0 and w[text.index("Dinner")] == 1.0 and w[text.index("How old")] == 1.0


def test_event_notes_become_his_own_words():
    assert as_his_own("goes for a long run", "gerund") == "going for a long run"
    assert as_his_own("watches {child} learn something new") == "watch my child learn something new"
    assert as_his_own("tries something he has never done") == "try something I have never done"
