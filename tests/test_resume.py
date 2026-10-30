"""A life that is checkpointed, cut off and resumed must carry on exactly as if it had never stopped: same world,
same memories, same network, same log and brain map."""
import json
import shutil

import pytest
import torch

from vegalife.trainer import Life

FAST = {"max_items_per_month": 2, "max_lm_steps_per_month": 2, "group_size": 3, "speech_bytes_per_month": 6000,
        "eval_every_months": 3, "checkpoint_months": 3}


def _config(d, profile, years):
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps({"seed": 11, "profile": profile, "max_age_years": years, "sim": FAST}),
                                   encoding="utf-8")


def _live(d, resume=False):
    L = Life(d, resume=resume)
    L.run()
    return L


def _lines(d, name):
    return (d / name).read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("profile", ["tiny", "tiny_lean"])
def test_a_resumed_life_is_the_same_life(tmp_path, monkeypatch, profile):
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    straight, cut = tmp_path / "straight", tmp_path / "cut"
    _config(straight, profile, 0.75)
    _config(cut, profile, 0.5)
    a = _live(straight)
    _live(cut)                                         # ends at 6 months with a checkpoint
    assert (cut / "resume.pt").exists()
    # A crash after the checkpoint: some lines were written that the resume must cut away.
    with open(cut / "events.jsonl", "a", encoding="utf-8") as f:
        f.write('{"age": 99, "event": "written after the checkpoint, then the power went"}\n')
    _config(cut, profile, 0.75)
    b = _live(cut, resume=True)
    assert b.p.age == a.p.age == 9
    assert b.p.s == a.p.s
    assert [e.what for e in b.mem.episodes] == [e.what for e in a.mem.episodes]
    for (k, x), (_, y) in zip(a.model.state_dict().items(), b.model.state_dict().items()):
        assert torch.equal(x, y), k
    strip = lambda ls: [l for l in ls if '"resumed from' not in l and "written after" not in l]
    assert strip(_lines(cut, "events.jsonl")) == strip(_lines(straight, "events.jsonl"))
    assert _lines(cut, "brain_nodes.jsonl") == _lines(straight, "brain_nodes.jsonl")
    assert _lines(cut, "brain_edges.jsonl") == _lines(straight, "brain_edges.jsonl")


def test_resume_without_a_checkpoint_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    _config(tmp_path, "tiny", 1)
    with pytest.raises(FileNotFoundError):
        Life(tmp_path, resume=True)
