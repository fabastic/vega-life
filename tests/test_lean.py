"""The low-memory optimiser must learn, free gradients as it goes, and survive network growth."""
import importlib.util
from pathlib import Path

import torch

from vegalife.model import Mind, Shape, lm_loss
from vegalife.optim import Lean, backward_step, stochastic_round_bf16


def test_stochastic_rounding_is_unbiased():
    x = torch.full((200_000,), 1.0 + 2 ** -10)          # not representable in bf16 (8 bits of mantissa)
    r = stochastic_round_bf16(x).float()
    assert set(r.unique().tolist()) <= {1.0, 1.0078125}
    assert abs(float(r.mean()) - float(x[0])) < 5e-4    # a plain cast would give exactly 1.0


def test_stochastic_rounding_keeps_negative_numbers_symmetric():
    x = torch.full((100_000,), -(1.0 + 2 ** -10))
    assert abs(float(stochastic_round_bf16(x).float().mean()) - float(x[0])) < 5e-4


def _tiny():
    torch.manual_seed(0)
    m = Mind(Shape(64, 2)).to(torch.bfloat16)
    m.checkpointing = True
    return m


def test_lean_learns_and_frees_gradients():
    m = _tiny()
    opt = Lean(m, 3e-3)
    x = torch.randint(0, 256, (8, 32))
    y = (x + 1) % 256                                    # a learnable fixed mapping
    m.train()
    first = None
    for _ in range(60):
        loss = lm_loss(m, x, y)
        first = first if first is not None else float(loss)
        backward_step(opt, m, loss)
        assert all(p.grad is None for p in m.parameters())      # nothing held after each step
    assert float(loss) < 0.6 * first, (first, float(loss))
    assert all(p.dtype == torch.bfloat16 for p in m.parameters())


def test_lean_survives_growth():
    m = _tiny()
    opt = Lean(m, 3e-3)
    x = torch.randint(0, 256, (4, 16))
    m.train()
    backward_step(opt, m, lm_loss(m, x, x))
    opt.close()
    assert not opt.state and not opt.hooks
    m.grow(Shape(128, 3))
    assert next(m.parameters()).dtype == torch.bfloat16 and m.shape.d == 128 and len(m.blocks) == 3
    opt = Lean(m, 3e-3)
    backward_step(opt, m, lm_loss(m, x, x))
    assert opt.t == 1 and all(p.grad is None for p in m.parameters())


def test_checkpointing_gives_the_same_gradients_as_not():
    torch.manual_seed(0)
    a = Mind(Shape(64, 2))
    b = Mind(Shape(64, 2))
    b.load_state_dict(a.state_dict())
    x = torch.randint(0, 256, (4, 16))
    a.checkpointing, b.checkpointing = False, True
    a.train(), b.train()
    lm_loss(a, x, x).backward()
    lm_loss(b, x, x).backward()
    for pa, pb in zip(a.parameters(), b.parameters()):
        assert torch.allclose(pa.grad, pb.grad, atol=1e-5)


def _server():
    spec = importlib.util.spec_from_file_location("ui_server", Path(__file__).resolve().parent.parent / "ui" / "server.py")
    srv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(srv)
    return srv


def test_trainer_command_lines_map_to_run_names():
    srv = _server()
    rx = srv.TRAINER_CMD
    assert rx.search(r'"C:\Python312\python.exe" -m vegalife.trainer "C:\Users\V\Projects\Vega\vega-life\runs\vega-1"').group(1) == "vega-1"
    assert rx.search(r"python.exe -m vegalife.trainer runs\life_2").group(1) == "life_2"
    assert rx.search("python.exe other.py") is None
