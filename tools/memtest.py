"""Peak GPU memory and step time of one network shape under the lean optimiser.

    python tools/memtest.py <width> <layers> [lean|adamw] [batch] [seq]

Run each shape in its own process so the numbers are not polluted by an earlier one.
"""
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vegalife.model import Mind, Shape, lm_loss, param_count   # noqa: E402
from vegalife.optim import Lean, backward_step                  # noqa: E402

d, L = int(sys.argv[1]), int(sys.argv[2])
kind = sys.argv[3] if len(sys.argv) > 3 else "lean"
B = int(sys.argv[4]) if len(sys.argv) > 4 else 16
T = int(sys.argv[5]) if len(sys.argv) > 5 else 256
dev = torch.device("cuda")
torch.manual_seed(0)
m = Mind(Shape(d, L))
if kind == "lean":
    m = m.to(torch.bfloat16)
m = m.to(dev)
m.checkpointing = kind == "lean"
opt = Lean(m, 1e-3) if kind == "lean" else torch.optim.AdamW(m.parameters(), lr=1e-3)
amp = (lambda: torch.autocast("cuda", dtype=torch.bfloat16)) if kind != "lean" else torch.autocast("cpu", enabled=False).__class__
torch.cuda.reset_peak_memory_stats()
base = torch.cuda.memory_allocated() / 1e9
x = torch.randint(0, 256, (B, T), device=dev)
y = torch.randint(0, 256, (B, T), device=dev)
m.train()
t0 = time.time()
for _ in range(3):
    if kind == "lean":
        loss = lm_loss(m, x, y)
    else:
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = lm_loss(m, x, y)
    backward_step(opt, m, loss)
torch.cuda.synchronize()
lm_s = (time.time() - t0) / 3
peak_lm = torch.cuda.max_memory_allocated() / 1e9
# a GRPO step: sample 6 answers of up to 8 bytes after a 120-byte prompt, then a backward on them
m.eval()
ids = torch.randint(0, 256, (6, 120), device=dev)
t0 = time.time()
with torch.no_grad():
    gen, _ = m.generate(ids, 8, 1.0)
m.train()
full = torch.cat([ids, gen], 1)
loss = lm_loss(m, full[:, :-1], full[:, 1:])
backward_step(opt, m, loss)
torch.cuda.synchronize()
rl_s = time.time() - t0
print(f"{d}x{L} {kind}: {param_count(Shape(d, L)) / 1e6:.0f}M params | weights+state {base:.2f} GB | "
      f"peak {torch.cuda.max_memory_allocated() / 1e9:.2f} GB (lm step peak {peak_lm:.2f}) | "
      f"lm step {lm_s:.2f}s, rl step {rl_s:.2f}s")
