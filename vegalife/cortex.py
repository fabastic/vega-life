"""His network as a brain: regions you can watch, and a probe of what it knows about him.

Cortex
  The network is grouped into macro-regions: the input layer (byte embedding), then for every block its attention
  ("which earlier bytes matter now") and its feed-forward part ("what that means"), then the output. That is at
  most 2 * layers + 2 nodes (under 130 at the full 1B shape), whatever the parameter count, so the map stays light
  as he grows from a few million to a billion parameters. For each region it records, with light hooks:
    activity   variance of the region's output on real input (how strongly it is responding)
    learning   size of the gradient flowing back through it during his monthly learning (how much it is changing)
  plus its size, when it formed, what kind of layer it is, and whether its critical period has closed (frozen).
  trainer.py writes cortex.json every few months; ui/cortex.html draws it.

Probe
  A linear probe (Alain & Bengio 2016) asks: does his network carry his current state when nothing in the prompt
  tells it? It reads his final hidden state after a bare question ("How are you, really?") and fits a ridge
  regression to his true mood, worry, grief, loneliness and joy over the months, scored on the most recent
  months it was not fitted on (R², time-ordered holdout). Near 0: his weights hold no trace of how he is; higher:
  they do. Caveat: states drift slowly over a life, so part of any fit can be time itself; the holdout is the
  latest months for that reason.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import torch


class Cortex:
    def __init__(self):
        self.stats: Dict[str, Dict[str, float]] = {}
        self.handles: list = []
        self.attached: tuple = ()
        self.recording = False

    def __getstate__(self):                  # hooks cannot be saved; stats are cheap to rebuild
        return {"stats": self.stats}

    def __setstate__(self, st):
        self.__init__()
        self.stats = st.get("stats", {})

    def attach(self, model) -> None:
        key = tuple(id(b) for b in model.blocks)
        if key == self.attached:
            return
        for h in self.handles:
            h.remove()
        self.handles = []
        for i, b in enumerate(model.blocks):
            for part, mod in (("attn", b.proj), ("mlp", b.out)):
                self.handles.append(mod.register_forward_hook(self._hook(f"{i}.{part}")))
        self.handles.append(model.emb.register_forward_hook(self._hook("input")))
        self.attached = key

    def _ema(self, name: str, field: str, v: float) -> None:
        st = self.stats.setdefault(name, {"act": 0.0, "grad": 0.0})
        st[field] = v if st[field] == 0.0 else 0.8 * st[field] + 0.2 * v

    def _hook(self, name: str):
        def f(mod, inp, out):
            if not self.recording or not torch.is_tensor(out):
                return
            self._ema(name, "act", float(out.detach().float().var()))
            if out.requires_grad:
                out.register_hook(lambda g: self._ema(name, "grad", float(g.detach().float().norm())) or None)
        return f

    def snapshot(self, model, age: float) -> dict:
        nodes, edges = [], []
        get = lambda n: self.stats.get(n, {"act": 0.0, "grad": 0.0})
        nodes.append({"id": "input", "label": "input (bytes)", "kind": "input", "layer": -1,
                      "params": int(model.emb.weight.numel()), **get("input")})
        prev = "input"
        for i, b in enumerate(model.blocks):
            for part, mods in (("attn", (b.qkv, b.proj)), ("mlp", (b.fc, b.out))):
                nid = f"{i}.{part}"
                nodes.append({"id": nid, "label": f"layer {i + 1} {'attention' if part == 'attn' else 'feed-forward'}",
                              "kind": b.kind, "part": part, "layer": i, "born": round(b.born, 2), "frozen": b.frozen,
                              "params": int(sum(m.weight.numel() for m in mods)), **get(nid)})
                edges.append({"src": prev, "dst": nid, "flow": get(nid)["grad"]})
                prev = nid
            if i > 0:                                 # the residual stream: each layer also sees the last one directly
                edges.append({"src": f"{i - 1}.attn", "dst": f"{i}.attn", "flow": 0.5 * get(f"{i}.attn")["grad"],
                              "skip": True})
        nodes.append({"id": "output", "label": "output (next byte)", "kind": "output", "layer": len(model.blocks),
                      "params": int(sum(p.numel() for p in model.norm.parameters())), "act": 0.0, "grad": 0.0})
        edges.append({"src": prev, "dst": "output", "flow": 0.0})
        return {"age": round(age, 2), "params": model.n_params(), "layers": len(model.blocks), "d": model.shape.d,
                "nodes": nodes, "edges": edges}


class Probe:
    TARGETS = ("mood", "anxiety", "grief", "felt_loneliness", "joy")

    def __init__(self, keep: int = 240):
        self.keep = keep
        self.x: List[torch.Tensor] = []
        self.y: List[List[float]] = []
        self.last: Optional[float] = None

    def add(self, h: torch.Tensor, targets: List[float]) -> Optional[float]:
        h = h.detach().float().cpu()
        if self.x and self.x[0].numel() != h.numel():  # his width grew: a new space, start again
            self.x, self.y = [], []
        self.x.append(h)
        self.y.append([float(t) for t in targets])
        self.x, self.y = self.x[-self.keep:], self.y[-self.keep:]
        n = len(self.x)
        if n < 30:
            return None
        X = torch.stack(self.x)
        Y = torch.tensor(self.y)
        cut = int(n * 0.8)
        mu, sd = X[:cut].mean(0), X[:cut].std(0) + 1e-6
        Xs = (X - mu) / sd
        A = Xs[:cut]
        lam = 10.0 * A.shape[1] / max(1, cut)          # ridge: far more dimensions than months, so shrink hard
        W = torch.linalg.solve(A.T @ A + lam * torch.eye(A.shape[1]), A.T @ (Y[:cut] - Y[:cut].mean(0)))
        pred = Xs[cut:] @ W + Y[:cut].mean(0)
        ss_res = ((Y[cut:] - pred) ** 2).sum(0)
        ss_tot = ((Y[cut:] - Y[cut:].mean(0)) ** 2).sum(0) + 1e-9
        self.last = round(float((1 - ss_res / ss_tot).clamp(min=-1.0).mean()), 4)
        return self.last
