"""His network must grow like a brain: built early, then hardening, so adult experience has to work through what
childhood and adolescence laid down instead of flowing into fresh weights."""
import json

import torch

from vegalife import growth
from vegalife.model import Mind, Shape, param_count
from vegalife.optim import Lean


def test_the_schedule_is_front_loaded_and_never_shrinks():
    rows = growth.SCHEDULE
    assert all(b[1] >= a[1] and b[2] >= a[2] for a, b in zip(rows, rows[1:]))
    size = lambda age: param_count(growth.target_shape(age, 0, growth.PROFILES["full"], 512))
    assert 0.35e9 < size(6) < 0.45e9                     # near adult structure by 6
    assert 0.8e9 < size(18) < 0.9e9                      # most of it by 18
    assert 0.95e9 < size(30) < 1.1e9                     # only executive layers after
    assert all(d == 1792 for a, d, _ in rows if a >= 6)  # width is final at 6: later growth is upward only


def test_no_layer_is_born_already_closed():
    for age, _, _ in growth.SCHEDULE[1:]:
        kind = growth.block_kind(age)
        for rel in (0.0, 0.5, 1.0):
            scale, frozen = growth.plasticity(age, kind, age, rel)
            assert scale > 0.95 and not frozen, (age, kind, rel, scale)


def test_critical_periods_close_in_order():
    core_bottom = growth.plasticity(15, "core", 0.0, 0.0)[0]
    assoc_late = growth.plasticity(15, "assoc", 14.0, 1.0)[0]
    assert core_bottom < 0.15 and assoc_late > 0.9
    assert growth.plasticity(24, "core", 0.0, 0.0)[1]                   # frozen in adulthood
    assert not growth.plasticity(17, "core", 0.0, 0.0)[1]               # nothing frozen before 18
    assert growth.plasticity(60, "exec", 21.0, 1.0) == (1.0, False)     # executive layers stay open


def test_layers_added_on_top_leave_what_he_computes_unchanged():
    torch.manual_seed(0)
    m = Mind(Shape(128, 2)).double()
    for p in m.parameters():
        p.data.add_(torch.randn_like(p) * 0.05)
    for mod in m.modules():
        if hasattr(mod, "eps"):
            mod.eps = 1e-14
    x = torch.randint(0, 256, (2, 30))
    before = m(x)
    old = list(m.blocks)
    m.grow(Shape(128, 4), at_top=True, born=19.0, kind="exec")
    assert list(m.blocks)[:2] == old and m.blocks[3].kind == "exec" and m.blocks[3].born == 19.0
    assert torch.allclose(before, m(x), atol=1e-9)


def _adult(lean: bool):
    """A small network at 24: two core layers, two association layers, two executive layers."""
    torch.manual_seed(1)
    m = Mind(Shape(64, 2))
    m.grow(Shape(64, 4), at_top=True, born=9.0, kind="assoc")
    m.grow(Shape(64, 6), at_top=True, born=19.0, kind="exec")
    for p in m.parameters():
        p.data.add_(torch.randn_like(p) * 0.02)
    groups = []
    kinds = {k: [b for b in m.blocks if b.kind == k] for k in ("core", "assoc", "exec")}
    for b in m.blocks:
        rel = kinds[b.kind].index(b) / max(1, len(kinds[b.kind]) - 1)
        scale, frozen = growth.plasticity(24.0, b.kind, b.born, rel)
        groups.append({"params": list(b.parameters()), "lr": 1e-2 * scale})
    groups.append({"params": [m.emb.weight] + list(m.norm.parameters()), "lr": 1e-2})
    if lean:
        m = m.to(torch.bfloat16)
        return m, Lean(groups, 1e-2, weight_decay=0.0)
    return m, torch.optim.AdamW(groups, lr=1e-2, weight_decay=0.0)


def _relative_change(lean: bool) -> dict:
    m, opt = _adult(lean)
    before = [[p.detach().float().clone() for p in b.parameters()] for b in m.blocks]
    x = torch.randint(0, 256, (4, 32))
    for _ in range(3):                                   # an upsetting event: the same lesson, hard, a few times
        opt.zero_grad()
        loss = m(x).float().logsumexp(-1).mean()
        loss.backward()
        opt.step()
    out = {}
    for b, old in zip(m.blocks, before):
        num = sum((p.detach().float() - o).norm() ** 2 for p, o in zip(b.parameters(), old)) ** 0.5
        den = sum(o.norm() ** 2 for o in old) ** 0.5
        out.setdefault(b.kind, []).append(float(num / den))
    return {k: sum(v) / len(v) for k, v in out.items()}


def test_an_adult_changes_mostly_in_new_layers_not_in_childhood_ones():
    for lean in (False, True):
        ch = _relative_change(lean)
        assert ch["core"] * 5 < ch["exec"], (lean, ch)
        assert ch["assoc"] < ch["exec"], (lean, ch)


def test_a_frozen_layer_gets_no_gradient_and_keeps_no_state():
    torch.manual_seed(2)
    m = Mind(Shape(64, 3)).to(torch.bfloat16)
    opt = Lean([{"params": list(b.parameters())} for b in m.blocks] + [{"params": [m.emb.weight] + list(m.norm.parameters())}], 1e-3)
    x = torch.randint(0, 256, (2, 16))
    opt.zero_grad(); m(x).float().mean().backward()
    b0 = m.blocks[0]
    assert all(p in opt.state for p in b0.parameters())
    b0.frozen = True
    params = list(b0.parameters())
    m.prune(b0, 0.05)
    for p in params:
        p.requires_grad_(False)
    opt.forget(params)
    before = [p.clone() for p in params]
    opt.zero_grad(); m(x).float().mean().backward()
    assert all(p.grad is None and p not in opt.state for p in params)
    assert all(torch.equal(a, b) for a, b in zip(before, params))
    assert (b0.fc.weight == 0).float().mean() >= 0.04                # pruned


def test_a_freeze_in_a_growth_month_is_still_recorded(tmp_path, monkeypatch):
    """An association layer formed at 9 freezes at 21, the same month the first executive layer grows."""
    from vegalife import trainer
    (tmp_path / "config.json").write_text(json.dumps({"seed": 4, "profile": "tiny", "max_age_years": 90}), encoding="utf-8")
    monkeypatch.setenv("VEGA_DEVICE", "cpu")
    L = trainer.Life(tmp_path)
    try:
        d, n = L.model.shape.d, L.model.shape.layers
        L.model.grow(Shape(d, n + 1), at_top=True, born=9.0, kind="assoc")
        L._optimizer()
        L.p.age = 21 * 12
        L.p.s["allostatic_load"] = 0.0
        monkeypatch.setattr(trainer.growth, "target_shape", lambda *a: Shape(d, n + 2, 512))
        L.grow_if_due()                                          # rebuilds the optimiser: must not freeze silently
        assert L.model.blocks[n].kind == "assoc" and not L.model.blocks[n].frozen
        assert L.model.blocks[n + 1].kind == "exec"
        L.consolidate()
        assert L.model.blocks[n].frozen
        assert any(nd["id"].startswith(f"milestone:freeze:{n}:") for nd in L.brain.nodes.values())
    finally:
        L.stop.set()
        L.events_f.close()
        L.brain.close()


def test_a_capped_life_still_learns_after_its_core_freezes(tmp_path):
    from vegalife.trainer import Life
    (tmp_path / "config.json").write_text(json.dumps({"seed": 3, "profile": "tiny", "max_age_years": 90}), encoding="utf-8")
    import os
    os.environ["VEGA_DEVICE"] = "cpu"
    L = Life(tmp_path)
    try:
        L.p.age = 30 * 12
        L.consolidate()                                       # the core closes, and the map records it
        assert L.model.blocks[0].frozen
        assert any(n["kind"] == "milestone" and n["id"].startswith("milestone:freeze") for n in L.brain.nodes.values())
        L.grow_if_due()
        L.consolidate()
        blocks = list(L.model.blocks)
        assert blocks[0].frozen and not blocks[-1].frozen
        loss = L.learn_language(["Teacher: two and two make four."] * 200, ["Mum: time for bed."] * 200)
        assert loss == loss
    finally:
        L.stop.set()
        L.events_f.close()
        if L.brain is not None:
            L.brain.close()
