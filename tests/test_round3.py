"""Round 3: her own voice in a woman's life, and the overnight check."""
import re

from vegalife import factors as fx
from vegalife.character import Character
from vegalife.people import Circle
from vegalife.voice import in_voice
from vegalife.world import Person


def test_pronouns_follow_whose_life_it_is():
    assert in_voice("loses his job", True) == "loses her job"
    assert in_voice("loses his job", False) == "loses his job"
    assert in_voice("He tells himself it is fine", True) == "She tells herself it is fine"
    assert in_voice("Dad loses his job", True) == "Dad loses his job"                 # that "his" is Dad's
    assert in_voice("his father dies and he cries", True) == "her father dies and she cries"
    assert in_voice("has a row with his father Dad about his grades", True) == \
        "has a row with her father Dad about her grades"
    assert in_voice("his brother calls him", True) == "her brother calls her"


def test_a_womans_life_is_told_as_hers():
    F = fx.sample(5, {"sex": 0.0})
    p = Person(F, 5, Circle(F, 5))
    ch = Character(p, F)
    lines, stray = 0, []
    while p.alive and p.age < 40 * 12:
        p.step_month(F)
        ch.step(p, F)
        for h in p.happenings:
            lines += 1
            if re.search(r"\b(he|his|him|himself)\b", h["text"], re.I) and not re.search(
                    r"\b(dad|father|brother|son|grandad|grandpa|uncle|husband|boyfriend|mr)\b", h["text"], re.I):
                stray.append(h["text"])
        p.happenings.clear()
    assert lines > 100 and not stray, stray[:5]
