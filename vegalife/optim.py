"""A low-memory optimiser so a bigger network fits on an 8 GB GPU.

AdamW in fp32 needs about 16 bytes per parameter (weight, gradient, two moments). This one needs about 4:

  * weights stay in bf16 (2 bytes); updates are applied with stochastic rounding, so a step smaller than bf16's
    resolution is not lost, only randomly rounded, and averages out correctly
  * each weight is updated the moment its gradient is ready, inside backward, and the gradient is freed at once, so
    gradients never exist for the whole network together
  * the second moment is factored into a row and a column vector (Adafactor), a few KB per matrix
  * the first moment is optional and kept in bf16 (2 bytes)
  * each update is clipped by its own RMS (Adafactor's update clipping) in place of global gradient clipping,
    which needs every gradient at once

Parameters can be split into groups, each with its own `lr` (a layer's critical period sets it), and a frozen
parameter can be dropped with `forget`, which frees its state.

Use through `backward_step`, which does the right thing for either optimiser.
"""
from __future__ import annotations

import torch


def stochastic_round_bf16(x: torch.Tensor) -> torch.Tensor:
    """fp32 -> bf16, rounding up or down at random in proportion to the distance to each neighbour."""
    bits = x.view(torch.int32)
    noise = torch.randint(0, 1 << 16, x.shape, dtype=torch.int32, device=x.device)
    return ((bits + noise) & -65536).view(torch.float32).to(torch.bfloat16)


class Lean:
    fused = True

    def __init__(self, model, lr: float, beta1: float = 0.9, beta2: float = 0.95,
                 weight_decay: float = 0.05, clip_rms: float = 1.0, momentum: bool = True):
        """`model` is a module (one group) or a list of groups: dicts with "params" and any other keys."""
        if isinstance(model, torch.nn.Module):
            model = [{"params": list(model.parameters())}]
        self.param_groups = []
        self.group_of: dict = {}
        self.params = []
        for g in model:
            g = dict(g, lr=g.get("lr", lr), params=[p for p in g["params"] if p.requires_grad])
            self.param_groups.append(g)
            for p in g["params"]:
                self.group_of[p] = g
                self.params.append(p)
        self.beta1, self.beta2, self.wd, self.clip_rms, self.momentum = beta1, beta2, weight_decay, clip_rms, momentum
        self.t = 0
        self.state: dict = {}
        self.hooks = {p: p.register_post_accumulate_grad_hook(self._hook) for p in self.params}

    def close(self) -> None:
        """Release hooks and state; needed before the network grows and its parameters are replaced."""
        for h in self.hooks.values():
            h.remove()
        self.hooks, self.state, self.params, self.group_of = {}, {}, [], {}

    def forget(self, params) -> None:
        """Stop updating these parameters (they have been frozen) and free their state."""
        for p in params:
            h = self.hooks.pop(p, None)
            if h is not None:
                h.remove()
            self.state.pop(p, None)
            g = self.group_of.pop(p, None)
            if g is not None:
                g["params"] = [q for q in g["params"] if q is not p]
        gone = set(map(id, params))
        self.params = [p for p in self.params if id(p) not in gone]

    def zero_grad(self, set_to_none: bool = True) -> None:
        self.t += 1
        for p in self.params:
            p.grad = None

    def step(self) -> None:          # the work is done in the hooks, as each gradient arrives
        pass

    @torch.no_grad()
    def _hook(self, p: torch.Tensor) -> None:
        g = p.grad.float()
        p.grad = None
        st = self.state.get(p)
        if st is None:
            st = {}
            if p.dim() >= 2:
                st["vr"] = torch.zeros(p.shape[:-1], device=p.device)
                st["vc"] = torch.zeros(p.shape[:-2] + p.shape[-1:], device=p.device)
            else:
                st["v"] = torch.zeros_like(g)
            if self.momentum:
                st["m"] = torch.zeros_like(p)
            self.state[p] = st
        b2 = min(self.beta2, 1.0 - float(self.t) ** -0.8)
        sq = g * g + 1e-30
        if "vr" in st:
            st["vr"].mul_(b2).add_(sq.mean(-1), alpha=1 - b2)
            st["vc"].mul_(b2).add_(sq.mean(-2), alpha=1 - b2)
            v = st["vr"].unsqueeze(-1) * st["vc"].unsqueeze(-2) / st["vr"].mean(-1, keepdim=True).unsqueeze(-1)
        else:
            st["v"].mul_(b2).add_(sq, alpha=1 - b2)
            v = st["v"]
        u = g * torch.rsqrt(v + 1e-30)
        u = u / torch.clamp(u.pow(2).mean().sqrt() / self.clip_rms, min=1.0)      # stays on the GPU: no sync
        if self.momentum:
            m = st["m"].float().mul_(self.beta1).add_(u, alpha=1 - self.beta1)
            st["m"].copy_(m)
            u = m
        lr = self.group_of[p]["lr"]
        w = p.float()
        w.mul_(1 - lr * self.wd).add_(u, alpha=-lr)
        p.copy_(stochastic_round_bf16(w))


def backward_step(opt, model: torch.nn.Module, loss: torch.Tensor, clip: float = 1.0) -> None:
    """zero_grad, backward, and (for the usual optimiser) clip and step. The lean one steps during backward."""
    opt.zero_grad(set_to_none=True)
    loss.backward()
    if not getattr(opt, "fused", False):
        torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
        opt.step()
