"""The trainer's decision path end to end, on the CPU: a teenager faces real situations through GRPO.

The world is fast-forwarded to 16 without training (cheap), then he faces situations with delayed consequences
and a problem, so the felt-vs-real split, the lived sample, novelty and scheduling are all exercised for real.
"""
import json
import os

import pytest

from vegalife.scenarios import ALL_SCENARIOS, Problem


@pytest.fixture
def teen(tmp_path, monkeypatch):
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    from vegalife.trainer import Life
    d = tmp_path / "t"
    d.mkdir()
    (d / "config.json").write_text(json.dumps({"seed": 4, "profile": "tiny_lean", "max_age_years": 90,
                                               "sim": {"group_size": 4}}), encoding="utf-8")
    life = Life(d)
    while life.p.age < 16 * 12:
        life.p.step_month(life.F)
        life.character.step(life.p, life.F)
        life.p.pending.clear()
    yield life
    life.stop.set()
    life.events_f.close()


def test_a_teenager_faces_situations_and_lives_with_the_consequences(teen):
    party = next(s for s in ALL_SCENARIOS if s.key == "party")
    essay = next(s for s in ALL_SCENARIOS if s.key == "essay_due")
    for sc in (party, essay, party):
        rec = teen.face(sc)
        assert rec["prompt"].startswith("Now (16y")
        assert len(rec["responses"]) == 4 and isinstance(rec["lived"], str)
        assert -1.0 <= rec["lived_reward"] <= 1.0
        if rec["choice"].startswith("(no valid"):
            assert rec["real_outcome"] is None
        else:
            assert -1.0 <= rec["real_outcome"] <= 1.0
    lived = sum(teen.chosen.values())
    assert lived == sum(1 for r in teen.items if not r["choice"].startswith("(no valid"))
    # any choice with a later consequence was scheduled to arrive later
    later = [r for r in teen.items if r.get("later")]
    assert len(teen.p.due) >= len(later) > 0 or not later


def test_a_problem_uses_the_lived_sample(teen):
    rec = teen.face(Problem("add", "Tom has 2 cups and finds 3 more. How many cups now?", 5, 1))
    assert rec["kind"] == "problem" and rec["lived_reward"] in (-0.3, 0.0, 1.0)
    assert teen.tier_n[1] == 1


def test_live_state_includes_personality_and_now(teen):
    teen.live("running")
    L = json.loads((teen.dir / "live.json").read_text(encoding="utf-8"))
    assert set(L["state"]["personality"]) >= {"openness", "neuroticism", "sleep", "mood"}
    assert L["now"] is None or L["now"]["line"].startswith("Now (")
