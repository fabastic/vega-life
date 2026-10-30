"""His brain map must record real chains of cause and effect, and the estimates must point the right way."""
import json

import pytest

from vegalife import factors as fx
from vegalife.brainmap import BrainMap
from vegalife.lifesim import SimLife
from vegalife.people import Circle
from vegalife.world import Person


def sim(tmp_path, name, years, **over):
    d = tmp_path / name
    d.mkdir()
    life = SimLife(d, {"seed": 4, "factors": over})
    life.run(years)
    return BrainMap.load(d), life


def edges(bm, relation=None, basis=None):
    return [e for es in bm.out.values() for e in es if (relation is None or e["relation"] == relation)
            and (basis is None or e["basis"] == basis)]


@pytest.fixture(scope="module")
def life25(tmp_path_factory):
    return sim(tmp_path_factory.mktemp("b"), "life", 25, household_stress=0.95, bullying=1.0)


def test_a_choice_leads_to_a_consequence_a_memory_and_a_later_decision(life25):
    bm, _ = life25
    later = edges(bm, "led to later")
    assert later and all(bm.nodes[e["src"]]["kind"] == "choice" and bm.nodes[e["dst"]]["kind"] == "consequence" for e in later)
    remembered = edges(bm, "remembered as")
    assert any(bm.nodes[e["src"]]["kind"] == "choice" for e in remembered)
    recalled = edges(bm, "recalled in")
    assert recalled and all(e["src"].startswith("mem:") and bm.nodes[e["dst"]]["kind"] == "choice" for e in recalled)
    assert all(e["src"] in bm.nodes for e in recalled)                     # a recall points at a real memory


def test_choices_record_what_they_changed(life25):
    bm, _ = life25
    ch = next(n for n in bm.nodes.values() if n["kind"] == "choice")
    assert any(e["relation"] == "changed" and e["dst"].startswith("state:") for e in bm.out[ch["id"]])
    assert any(e["relation"] == "faced" for e in bm.inn[ch["id"]])


def test_bullying_drives_the_situation_and_being_bullied_shapes_him(life25):
    bm, _ = life25
    assert any(e["src"] == "factor:bullying" and e["dst"] == "situation:bullied" and e["weight"] > 0
               for e in edges(bm, "makes likelier"))
    bullied = [n for n in bm.nodes.values() if n["kind"] == "event" and "bullied" in n["label"]]
    assert bullied
    assert any(e["dst"] == "state:neuroticism" and e["weight"] > 0 for n in bullied for e in bm.out[n["id"]])
    assert any(e["src"] == "factor:bullying" for n in bullied for e in bm.inn[n["id"]])


def test_slow_influences_point_the_right_way(life25):
    bm, _ = life25
    est = [e for e in edges(bm, basis="estimated") if e["src"] == "factor:household_stress" and e["dst"] == "state:allostatic_load"]
    assert est and all(e["weight"] > 0 for e in est)                       # chronic stress raises stress load
    assert all("stage" in e["props"] for e in edges(bm, basis="estimated"))


def test_trace_follows_the_chain_upstream(life25):
    bm, _ = life25
    cons = next(n for n in bm.nodes.values() if n["kind"] == "consequence" and bm.inn[n["id"]])
    t = bm.trace(cons["id"], "up", 3)
    kinds = {n["kind"] for n in t["nodes"]}
    assert {"consequence", "choice", "situation"} <= kinds
    down = bm.trace("factor:bullying", "down", 2)
    assert any(n["id"] == "situation:bullied" for n in down["nodes"])


def test_queries_are_capped_and_well_formed(life25):
    bm, _ = life25
    top = bm.top(n=5000)
    assert len(top["nodes"]) <= 600
    ids = {n["id"] for n in top["nodes"]}
    assert all(e["src"] in ids and e["dst"] in ids for e in top["edges"])
    win = bm.top(10 * 12, 15 * 12, n=100, kinds={"choice"})
    assert all(n["kind"] == "choice" and 120 <= n["age"] <= 180 for n in win["nodes"])
    hits = bm.top(q="bullied", n=50)
    assert hits["nodes"]


def test_the_server_reads_new_lines_as_they_are_written(tmp_path):
    bm = BrainMap(tmp_path)
    bm.node("a", "event", "first", 1)
    bm.flush()
    reader = BrainMap(None)
    pos = reader.extend(tmp_path)
    assert "a" in reader.nodes
    bm.node("b", "event", "second", 2)
    bm.edge("a", "b", "led to later")
    bm.flush()
    reader.extend(tmp_path, pos)
    assert "b" in reader.nodes and reader.out["a"][0]["dst"] == "b"


def test_a_clone_lives_a_month_without_touching_him():
    F = fx.sample(1)
    p = Person(F, 1, Circle(F, 1))
    for _ in range(100):
        p.step_month(F)
    before = (dict(p.s), p.age, p.rng.getstate())
    c = p.clone()
    c.step_month(F)
    assert (dict(p.s), p.age, p.rng.getstate()) == before
    d = p.clone()
    d.step_month(F)
    assert d.s == c.s                                                     # same randomness, same month


def test_overview_groups_repeats_into_a_readable_map(life25):
    bm, _ = life25
    o = bm.overview()
    ids = {n["id"] for n in o["nodes"]}
    assert len(o["nodes"]) < len(bm.nodes) / 5                            # far smaller than every moment
    assert all(e["src"] in ids and e["dst"] in ids for e in o["edges"])
    groups = [n for n in o["nodes"] if n["props"].get("grouped")]
    assert groups and any(n["props"]["count"] > 1 for n in groups)
    assert any(e["relation"] == "his choices changed" and e["src"].startswith("situation:") for e in o["edges"])
    teen = bm.overview(13 * 12, 17 * 12 + 11)
    assert all(n["props"]["first_age"] >= 13 * 12 for n in teen["nodes"] if n["props"].get("grouped"))


def _pieces(ids, pairs):
    adj = {i: set() for i in ids}
    for a, b in pairs:
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    seen, count = set(), 0
    for i in ids:
        if i in seen:
            continue
        count += 1
        stack = [i]
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x)
                stack.extend(adj[x] - seen)
    return count


def test_everything_is_one_connected_brain(life25):
    bm, _ = life25
    assert _pieces(list(bm.nodes), [(e["src"], e["dst"]) for es in bm.out.values() for e in es]) == 1
    o = bm.overview()
    assert _pieces([n["id"] for n in o["nodes"]], [(e["src"], e["dst"]) for e in o["edges"]]) == 1
    assert "self:vega" in bm.nodes and all(f"stage:{s}" in bm.nodes for s in
                                           ("infancy", "childhood", "adolescence", "early_adult"))


def test_every_node_is_marked_simulated(life25):
    bm, _ = life25
    assert all(n.get("source") == "simulated" for n in bm.nodes.values())
