"""The life-story tools (timeline lanes, places, the written story, the weekday record) and the population check."""
import json

from vegalife import factors as fx
from vegalife.character import Character
from vegalife.people import Circle
from vegalife.story import CITIES, lane_of, places, story_markdown, timeline
from vegalife.world import Person


def test_lanes_come_from_keys_then_words():
    assert lane_of("wedding") == "love" and lane_of("work") == "work"
    assert lane_of("", "is diagnosed with asthma") == "body" and lane_of("", "meets Yuki, a new friend") == "friends"
    assert lane_of("", "something unclassifiable") == "world" and lane_of("joy", "finishes what he set out to do") == "mind"


def test_places_follow_region_and_emigration():
    L = {"factors": {"region": {"value": 0.6}}, "family": {"people": [{"name": "Mum", "relation": "mother"}]}}
    pl = places(L, 3)
    assert pl["born"]["region"] == "Sub-Saharan Africa" and pl["now"] == pl["born"] and not pl["moves"]
    L["economy"] = {"emigrated": {"from": "Sub-Saharan Africa", "to": "Western Europe", "at": 27.5}}
    pl = places(L, 3)
    assert pl["now"]["region"] == "Western Europe" and pl["moves"]
    assert pl["people"][0]["city"] == pl["born"]["city"]                 # his mother stayed behind
    assert all(-90 <= c[1] <= 90 and -180 <= c[2] <= 180 for cs in CITIES.values() for c in cs)


def test_story_reads_a_timeline(tmp_path):
    rows = [{"age": 4.2, "text": "meets Yuki", "key": "friend", "lane": "friends", "v": 0.6, "a": 0.5},
            {"age": 27.0, "text": "marries Sam, surrounded by everyone they love", "key": "wedding", "lane": "love",
             "v": 1.0, "a": 0.9},
            {"age": 27.5, "text": "the flat floods", "key": "disaster", "lane": "world", "v": -0.5, "a": 0.6}]
    (tmp_path / "timeline.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (tmp_path / "config.json").write_text(json.dumps({"seed": 4}), encoding="utf-8")
    (tmp_path / "live.json").write_text(json.dumps({"age_years": 30.0, "factors": {"region": {"value": 0.2}},
                                                    "mind": {"inner": "Tay in maths."}}), encoding="utf-8")
    assert [r["lane"] for r in timeline(tmp_path)] == ["friends", "love", "world"]
    md = story_markdown(tmp_path)
    assert "## Childhood" in md and "At 4 he meets Yuki." in md and "At 27: The flat floods." in md
    assert "Born in" in md and "Tay in maths." in md
    live = json.loads((tmp_path / "live.json").read_text(encoding="utf-8"))
    live["factors"]["sex"] = {"value": 0.0}
    (tmp_path / "live.json").write_text(json.dumps(live), encoding="utf-8")
    assert "At 4 she meets Yuki." in story_markdown(tmp_path)


def test_weekday_is_recorded_each_birthday():
    F = fx.sample(21)
    p = Person(F, 21, Circle(F, 21))
    ch = Character(p, F)
    while p.age < 8 * 12:
        p.step_month(F)
        ch.step(p, F)
        p.happenings.clear()
    days = p.surroundings.days
    assert set(days) >= {3, 5, 7} and days[7]["school"] > 0 and days[7]["sleep"] > 6


def test_population_summary_scores_against_targets():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import population
    rows = [population.one(s, 40) for s in (9000, 9001, 9002)]
    rep = population.summarise(rows)
    names = {x["name"] for x in rep["lines"]}
    assert names == set(population.TARGETS) and all(isinstance(x["ok"], bool) for x in rep["lines"])
    assert "| Rate |" in population.markdown(rep)
