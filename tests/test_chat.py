"""Talking to him: he answers in his own words, from his life, and talking does not change that life."""
import json
import time

import torch

from vegalife import chat
from vegalife.memory import Memory
from vegalife import factors as fx
from vegalife.trainer import Life

FAST = {"max_items_per_month": 2, "max_lm_steps_per_month": 2, "group_size": 3, "speech_bytes_per_month": 6000,
        "eval_every_months": 3, "checkpoint_months": 3}


def _config(d, years=0.5):
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps({"seed": 5, "profile": "tiny", "max_age_years": years, "sim": FAST}),
                                   encoding="utf-8")


def _ask(d, text, rid="q1"):
    with open(d / "chat_in.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": rid, "t": time.time(), "message": text, "history": []}) + "\n")


def _replies(d):
    return [json.loads(l) for l in (d / "chat_out.jsonl").read_text(encoding="utf-8").splitlines()]


def test_the_conversation_brings_back_a_matching_memory_and_fits_his_context():
    F = fx.sample(2)
    m = Memory(F, 2)
    m.add(100, "scenario", "bullied", "social", "Some older kids push you at school.", [], -0.6, 0.9, did_text="tell a teacher")
    m.add(110, "scenario", "party", "social", "A friend invites you to a party.", [], 0.5, 0.4, did_text="go")
    assert "push" in chat.pick_memory(m, "Were you ever pushed around at school?").what
    assert chat.pick_memory(m, "hmm") is None
    long = [{"who": "you", "text": "x" * 250}, {"who": "him", "text": "y" * 250}] * 4
    p = chat.build_prompt("Now (8y0m): at home.", "Vega", long, "and then?", "When I was 8, ...")
    assert len(p.encode()) + 1 <= 512 - chat.MAX_NEW and p.endswith("You: and then?\nVega:")


def test_a_living_life_answers_and_talking_does_not_change_it(tmp_path, monkeypatch):
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    quiet, talked = tmp_path / "quiet", tmp_path / "talked"
    _config(quiet)
    _config(talked)
    a = Life(quiet)
    a.run()
    _ask(talked, "Do you like your friends?")
    b = Life(talked)
    b.run()
    r = _replies(talked)
    assert len(r) == 1 and r[0]["id"] == "q1" and r[0]["source"] == "live" and isinstance(r[0]["reply"], str)
    assert a.p.s == b.p.s                                        # same life, word for word
    for (k, x), (_, y) in zip(a.model.state_dict().items(), b.model.state_dict().items()):
        assert torch.equal(x, y), k


def test_a_life_at_rest_is_woken_from_its_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    d = tmp_path / "rest"
    _config(d)
    Life(d).run()
    model, name, mem, now, age, source = chat._load(d, torch.device("cpu"))
    assert age == 6 and "checkpoint" in source and now().startswith("Now (0y6m)")
    _ask(d, "What do you remember?", "q2")
    t = chat.Talker(model, torch.device("cpu"), __import__("contextlib").nullcontext, name, mem, now, age)
    assert chat.Inbox(d).serve(lambda: t, source) == 1
    assert _replies(d)[-1]["id"] == "q2"
    assert chat.Inbox(d).serve(lambda: t, source) == 0           # answered once, never twice
