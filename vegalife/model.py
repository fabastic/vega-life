"""Vega's language model, written and trained from scratch. It is born tiny and grows with him.

A byte-level decoder-only transformer: RMSNorm, rotary positions, tied input/output embedding, head size fixed
at 64. Growth is function-preserving, so the model knows exactly what it knew a moment before it grew:

  grow_width   adds heads, residual dimensions and MLP units. New residual dimensions start at zero, nothing
               writes into them yet, and the RMSNorm gains are rescaled by sqrt(d_old / d_new) so every
               normalised activation is unchanged.
  grow_depth   inserts blocks whose output projections are zero, so each new block starts as the identity.

Both keep the output identical (up to RMSNorm eps); test_growth.py checks this.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.checkpoint

HEAD = 64
VOCAB = 259          # 256 bytes + PAD, BOS, EOS
PAD, BOS, EOS = 256, 257, 258
INIT_STD = 0.02


@dataclass
class Shape:
    d: int
    layers: int
    ctx: int = 512

    @property
    def heads(self) -> int:
        return self.d // HEAD

    @property
    def hidden(self) -> int:
        return 4 * self.d


def param_count(shape: Shape) -> int:
    d, L = shape.d, shape.layers
    return VOCAB * d + L * (4 * d * d + 2 * d * 4 * d + 2 * d) + d


class RMSNorm(nn.Module):
    def __init__(self, d: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        x32 = x.float() if x.dtype in (torch.float16, torch.bfloat16) else x
        return (x32 * torch.rsqrt(x32.pow(2).mean(-1, keepdim=True) + self.eps)).type_as(x) * self.weight


def rotary(ctx: int, device) -> tuple:
    inv = 1.0 / (10000 ** (torch.arange(0, HEAD, 2, device=device).float() / HEAD))
    t = torch.arange(ctx, device=device).float()
    f = torch.outer(t, inv)
    return f.cos(), f.sin()


def rope(x, cos, sin):
    x1, x2 = x[..., ::2], x[..., 1::2]
    return torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), -1).flatten(-2)


class Block(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.n1 = RMSNorm(d)
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.proj = nn.Linear(d, d, bias=False)
        self.n2 = RMSNorm(d)
        self.fc = nn.Linear(d, 4 * d, bias=False)
        self.out = nn.Linear(4 * d, d, bias=False)
        self.born = 0.0              # age (years) the layer formed, and what kind it is (growth.block_kind)
        self.kind = "core"
        self.frozen = False

    def forward(self, x, cos, sin):
        B, T, C = x.shape
        h = C // HEAD
        q, k, v = self.qkv(self.n1(x)).split(C, dim=2)
        q, k, v = (t.view(B, T, h, HEAD).transpose(1, 2) for t in (q, k, v))
        c, s_ = cos[:T].to(q.dtype), sin[:T].to(q.dtype)
        q, k = rope(q, c, s_), rope(k, c, s_)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(y.transpose(1, 2).reshape(B, T, C))
        return x + self.out(F.gelu(self.fc(self.n2(x))))


class Mind(nn.Module):
    def __init__(self, shape: Shape):
        super().__init__()
        self.shape = shape
        self.emb = nn.Embedding(VOCAB, shape.d)
        self.blocks = nn.ModuleList(Block(shape.d) for _ in range(shape.layers))
        self.norm = RMSNorm(shape.d)
        for p in self.parameters():
            if p.dim() == 2:
                nn.init.normal_(p, std=INIT_STD)
        for b in self.blocks:   # GPT-2 style scaled residual init
            nn.init.normal_(b.proj.weight, std=INIT_STD / math.sqrt(2 * shape.layers))
            nn.init.normal_(b.out.weight, std=INIT_STD / math.sqrt(2 * shape.layers))
        self._rot = None

    def n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def _rotary(self, device):
        if self._rot is None or self._rot[0].device != device:
            self._rot = rotary(self.shape.ctx, device)
        return self._rot

    checkpointing = False           # recompute each block in backward instead of storing its activations

    def forward(self, idx):
        cos, sin = self._rotary(idx.device)
        x = self.emb(idx)
        if len(self.blocks) and self.blocks[0].frozen:
            x = x.detach()        # hardened input layers: no gradient flows down through them (the head still learns)
        for b in self.blocks:
            if self.checkpointing and self.training and torch.is_grad_enabled():
                x = torch.utils.checkpoint.checkpoint(b, x, cos, sin, use_reentrant=False)
            else:
                x = b(x, cos, sin)
        return self.norm(x) @ self.emb.weight.t()

    # ------------------------------------------------------------------ generation
    @torch.no_grad()
    def generate(self, idx, max_new: int, temperature: float = 1.0, stop: tuple = (10, EOS), generator=None):
        """Samples continuations for a batch. Returns (new_tokens [B, n], lengths [B]) where length counts up to
        and including the first stop token."""
        B = idx.shape[0]
        out = []
        done = torch.zeros(B, dtype=torch.bool, device=idx.device)
        lengths = torch.full((B,), max_new, device=idx.device)
        for step in range(max_new):
            logits = self(idx[:, -self.shape.ctx:])[:, -1, :VOCAB].float()
            logits[:, PAD] = -1e9
            logits[:, BOS] = -1e9
            if temperature <= 0:
                nxt = logits.argmax(-1)
            else:
                nxt = torch.multinomial(F.softmax(logits / temperature, -1), 1, generator=generator).squeeze(1)
            out.append(nxt)
            idx = torch.cat([idx, nxt[:, None]], 1)
            hit = torch.zeros_like(done)
            for s in stop:
                hit |= nxt == s
            newly = hit & ~done
            lengths[newly] = step + 1
            done |= hit
            if bool(done.all()):
                break
        return torch.stack(out, 1), lengths

    # ------------------------------------------------------------------ growth
    @torch.no_grad()
    def grow(self, target: Shape, at_top: bool = False, born: float = 0.0, kind: str = "core") -> list:
        """Grows in place to the target shape. New layers go between the old ones, or on top (at_top), and are
        stamped with the age they formed and their kind. Returns what was done."""
        done = []
        if target.d > self.shape.d:
            done.append(f"width {self.shape.d} -> {target.d}")
            self._grow_width(target.d)
        if target.layers > self.shape.layers:
            done.append(f"depth {self.shape.layers} -> {target.layers}{' (on top)' if at_top else ''}")
            self._grow_depth(target.layers, at_top, born, kind)
        return done

    def _grow_width(self, d2: int) -> None:
        d = self.shape.d
        h2 = 4 * d2
        dev, dt = self.emb.weight.device, self.emb.weight.dtype
        scale = math.sqrt(d / d2)

        def norm(old: RMSNorm) -> RMSNorm:
            n = RMSNorm(d2, old.eps).to(dev, dt)
            n.weight.data.fill_(scale)
            n.weight.data[:d] = old.weight.data * scale
            return n

        E = torch.zeros(VOCAB, d2, device=dev, dtype=dt)
        E[:, :d] = self.emb.weight.data
        self.emb = nn.Embedding(VOCAB, d2).to(dev, dt)
        self.emb.weight.data.copy_(E)
        for b in self.blocks:
            # qkv rows: [q | k | v], each d2 long; old heads keep their slots at the start of each section.
            Wq = torch.empty(3 * d2, d2, device=dev, dtype=dt).normal_(std=INIT_STD)
            for sec in range(3):
                Wq[sec * d2: sec * d2 + d, :d] = b.qkv.weight.data[sec * d: (sec + 1) * d]
            b.qkv = nn.Linear(d2, 3 * d2, bias=False, device=dev, dtype=dt)
            b.qkv.weight.data.copy_(Wq)
            # proj: old block copied; new heads' outputs and writes into new residual dims start at zero.
            Wp = torch.zeros(d2, d2, device=dev, dtype=dt)
            Wp[:d, :d] = b.proj.weight.data
            b.proj = nn.Linear(d2, d2, bias=False, device=dev, dtype=dt)
            b.proj.weight.data.copy_(Wp)
            # fc: new hidden units and new input columns random (inputs on new dims are zero for now).
            Wf = torch.empty(h2, d2, device=dev, dtype=dt).normal_(std=INIT_STD)
            Wf[:4 * d, :d] = b.fc.weight.data
            b.fc = nn.Linear(d2, h2, bias=False, device=dev, dtype=dt)
            b.fc.weight.data.copy_(Wf)
            # out: new hidden units' outputs and writes into new residual dims start at zero.
            Wo = torch.zeros(d2, h2, device=dev, dtype=dt)
            Wo[:d, :4 * d] = b.out.weight.data
            b.out = nn.Linear(h2, d2, bias=False, device=dev, dtype=dt)
            b.out.weight.data.copy_(Wo)
            b.n1, b.n2 = norm(b.n1), norm(b.n2)
            for p in b.parameters():                   # a widened layer that was frozen stays frozen
                p.requires_grad_(not b.frozen)
        self.norm = norm(self.norm)
        self.shape = Shape(d2, self.shape.layers, self.shape.ctx)

    def _grow_depth(self, L2: int, at_top: bool = False, born: float = 0.0, kind: str = "core") -> None:
        L = self.shape.layers
        dev, dt = self.emb.weight.device, self.emb.weight.dtype
        blocks = list(self.blocks)
        n_new = L2 - L
        if at_top:                    # on top of everything (later layers: association, then executive)
            positions = [len(blocks)] * n_new
        else:                         # spread evenly through the stack (early childhood)
            positions = sorted({round((i + 1) * len(blocks) / (n_new + 1)) for i in range(n_new)})
            while len(positions) < n_new:
                positions.append(len(blocks))
        for k, pos in enumerate(sorted(positions, reverse=True)):
            nb = Block(self.shape.d).to(dev, dt)
            for p in nb.parameters():
                if p.dim() == 2:
                    nn.init.normal_(p, std=INIT_STD)
            nb.proj.weight.data.zero_()
            nb.out.weight.data.zero_()
            nb.born, nb.kind = born, kind
            blocks.insert(pos, nb)
        self.blocks = nn.ModuleList(blocks)
        self.shape = Shape(self.shape.d, L2, self.shape.ctx)

    # ------------------------------------------------------------------ ageing
    @torch.no_grad()
    def degrade(self, amount: float, gen: torch.Generator) -> None:
        """Neurodegeneration: multiplicative noise and silencing of a few MLP units, scaled by amount (0-1)."""
        if amount <= 0:
            return
        for b in self.blocks:
            w = b.out.weight
            noise = torch.randn(w.shape, generator=gen, device="cpu").to(w.device, w.dtype)
            w.mul_(1 + 0.02 * amount * noise)
            kill = torch.rand(w.shape[1], generator=gen) < 0.002 * amount
            w[:, kill.to(w.device)] = 0

    @torch.no_grad()
    def prune(self, block: "Block", fraction: float) -> int:
        """Synaptic pruning: silence the weakest MLP connections of a layer as it is frozen. Returns how many."""
        n = 0
        for w in (block.fc.weight, block.out.weight):
            k = int(w.numel() * fraction)
            if k:
                cut = w.abs().flatten().float().kthvalue(k).values
                mask = w.abs() <= cut.to(w.dtype)
                n += int(mask.sum())
                w[mask] = 0
        return n

    def config(self) -> dict:
        return asdict(self.shape) | {"heads": self.shape.heads, "params": self.n_params()}


def lm_loss(model: Mind, x, y, w=None):
    """Next-byte loss. `w` (same shape as y) weights each target; used to make him attend to answers in a lesson."""
    logits = model(x)
    ce = F.cross_entropy(logits.float().reshape(-1, VOCAB), y.reshape(-1), ignore_index=PAD, reduction="none")
    if w is None:
        return ce[y.reshape(-1) != PAD].mean()
    w = w.reshape(-1).float() * (y.reshape(-1) != PAD)
    return (ce * w).sum() / w.sum().clamp(min=1.0)


ANSWER = b"Answer:"


def answer_weights(data: list, weight: float, markers=(b"Answer:", b"\nVega:")) -> list:
    """Per-byte weights: `weight` on the bytes after each marker up to the end of the line, 1 elsewhere. The
    markers are the answers he gives: to problems and situations ('Answer:'), and his own lines when someone talks
    to him ('Vega:'), so learning concentrates on what he says, not only on what he hears."""
    b = bytes(t for t in data if t < 256) if all(t < 256 for t in data) else bytes(t if t < 256 else 0 for t in data)
    w = [1.0] * len(b)
    for mark in markers:
        i = b.find(mark)
        while i >= 0:
            j = i + len(mark)
            k = b.find(b"\n", j)
            k = len(b) if k < 0 else k + 1
            for q in range(j, k):
                w[q] = weight
            i = b.find(mark, k)
    return w


def encode(text: str) -> list:
    return list(text.encode("utf-8", errors="replace"))


def decode(tokens) -> str:
    return bytes(t for t in tokens if t < 256).decode("utf-8", errors="replace")
