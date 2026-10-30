"""Grow a bf16 network through every milestone to ~1B on the GPU with the lean optimiser, as the trainer does.

Checks that growth never needs more memory than training does, and that a step works after each growth.
"""
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vegalife.growth import SCHEDULE                          # noqa: E402
from vegalife.model import Mind, Shape, lm_loss               # noqa: E402
from vegalife.optim import Lean, backward_step                # noqa: E402

dev = torch.device("cuda")
torch.manual_seed(0)
m = Mind(Shape(SCHEDULE[0][1], SCHEDULE[0][2])).to(torch.bfloat16).to(dev)
m.checkpointing = True
opt = Lean(m, 3e-4)
x = torch.randint(0, 256, (16, 256), device=dev)
y = torch.randint(0, 256, (16, 256), device=dev)
for age, d, L in SCHEDULE:
    if d > m.shape.d or L > m.shape.layers:
        opt.close()
        torch.cuda.reset_peak_memory_stats()
        m.grow(Shape(d, L))
        opt = Lean(m, 3e-4)
        torch.cuda.empty_cache()
        grow_peak = torch.cuda.max_memory_allocated() / 1e9
    else:
        grow_peak = 0.0
    m.train()
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    loss = lm_loss(m, x, y)
    backward_step(opt, m, loss)
    torch.cuda.synchronize()
    print(f"age {age:>4}: {m.n_params() / 1e6:6.0f}M  growth peak {grow_peak:.2f} GB  train-step peak "
          f"{torch.cuda.max_memory_allocated() / 1e9:.2f} GB  {time.time() - t0:.1f}s  loss {float(loss):.2f}", flush=True)
