"""When his network grows, and when each part of it stops changing.

The brain's structure is built early: by 6 it is near its adult size, 7-18 adds association layers on top while the
early ones harden, and 18-30 adds only a few executive layers while everything older is consolidated (myelination,
pruning). So the schedule is front-loaded, like a brain, not back-loaded:

  0-6    width grows to its final size and the core layers form       ~0.4M -> ~386M
  7-18   one association layer a year, added on top                   ~386M -> ~848M
  18-30  four executive layers, added on top                           ~848M -> ~1.0B

Width stops growing at 6 because widening writes fresh units into every layer, including ones that have already
hardened (they would be dead weight forever). After 6 the network only grows upward.

Each layer has a critical period: fully plastic when it forms, then its learning rate falls to a floor (10%) and,
in adulthood, it is frozen and lightly pruned. Core layers close at 7-12, association layers about 7 years after
they form (the last at ~25, like the prefrontal cortex), executive layers stay plastic. So an adult's new
experiences have to work through a hardened childhood and adolescence instead of flowing into fresh weights.

Milestones are by age; adversity in early life delays them. A profile caps the size to what the GPU can train: the
shape stays on the full schedule's path and simply stops growing at the cap.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .model import Shape, param_count

# (age in years, width, layers)
SCHEDULE: List[Tuple[float, int, int]] = [
    (0.0, 128, 2),
    (0.5, 256, 3),
    (1.0, 384, 4),
    (2.0, 768, 6),
    (3.0, 1024, 8),
    (4.0, 1280, 8),
    (5.0, 1536, 9),
    (6.0, 1792, 10),       # width is final: from here on he grows only upward
    (7.0, 1792, 11), (8.0, 1792, 12), (9.0, 1792, 13), (10.0, 1792, 14), (11.0, 1792, 15), (12.0, 1792, 16),
    (13.0, 1792, 17), (14.0, 1792, 18), (15.0, 1792, 19), (16.0, 1792, 20), (17.0, 1792, 21), (18.0, 1792, 22),
    (21.0, 1792, 23), (24.0, 1792, 24), (27.0, 1792, 25), (30.0, 1792, 26),
]

CORE_UNTIL = 6.5          # layers formed before this are core (sensory, attachment, threat)
ASSOC_UNTIL = 18.5        # ...before this, association layers; after it, executive layers
FLOOR = 0.1               # a closed layer still learns, at a tenth of the rate
FREEZE_FROM = 18.0        # nothing is frozen before adulthood
EMB_CLOSE = 10.0          # the byte embedding (also his output head) consolidates, but is never frozen

PROFILES = {
    # 8 GB laptop GPU: AdamW in fp32 needs ~16 bytes per parameter, plus activations.
    "laptop": 220_000_000,
    # ~1B: needs a 24-48 GB GPU (or 8-bit optimiser states).
    "full": 1_100_000_000,
    # for quick tests
    "tiny": 3_000_000,
    # the whole 1B path on an 8 GB GPU: bf16 weights, lean optimiser, checkpointed blocks (peak 5.2 GB at 1.0B)
    "laptop_xl": 1_100_000_000,
    "tiny_lean": 3_000_000,
}

LEAN = {"laptop_xl", "tiny_lean"}       # profiles that train with optim.Lean in bf16 instead of AdamW in fp32

NOTES = {
    "tiny": "a few million parameters, for quick tests",
    "laptop": "stops at ~158M (the 4-year milestone): fp32 AdamW, the most an 8 GB GPU can train that way",
    "laptop_xl": "the whole path to ~1.0B by age 30 on an 8 GB GPU: bf16 weights, lean optimiser, checkpointed blocks (peak ~5.2 GB at 1.0B); slow",
    "full": "the whole path to ~1.0B with fp32 AdamW; needs a 24-48 GB GPU",
    "tiny_lean": "a few million parameters with the lean optimiser, for testing it",
}


def target_shape(age_years: float, delay_years: float, cap: int, ctx: int) -> Shape:
    best = Shape(SCHEDULE[0][1], SCHEDULE[0][2], ctx)
    for age, d, L in SCHEDULE:
        if age_years + 1e-9 >= age + (delay_years if age > 0 else 0.0):
            s = Shape(d, L, ctx)
            if param_count(s) <= cap:
                best = s
    return best


def delay(allostatic_load: float, attachment: float) -> float:
    """Up to ~1.5 years of delay for chronic stress with little care."""
    return 1.5 * allostatic_load * (1 - 0.5 * attachment)


def describe(cap: int, ctx: int = 512) -> List[dict]:
    rows = []
    for age, d, L in SCHEDULE:
        s = Shape(d, L, ctx)
        rows.append({"age": age, "width": d, "layers": L, "params": param_count(s), "within_cap": param_count(s) <= cap})
    return rows


def block_kind(born_years: float) -> str:
    return "core" if born_years < CORE_UNTIL else "assoc" if born_years < ASSOC_UNTIL else "exec"


def grows_on_top(age_years: float) -> bool:
    """After early childhood new layers go on top of the stack (association, then executive), instead of between
    the existing ones."""
    return age_years >= CORE_UNTIL


def close_age(kind: str, born_years: float, rel_depth: float) -> Optional[float]:
    """When a layer's critical period closes: core layers bottom-up from 7 to 12, association layers ~7 years after
    they form (never later than 25), executive layers never."""
    if kind == "core":                            # at least four open years, even for a layer formed at 5
        return max(7.0 + 5.0 * rel_depth, born_years + 4.0)
    if kind == "assoc":
        return min(25.0, born_years + 7.0)
    return None


def plasticity(age_years: float, kind: str, born_years: float, rel_depth: float) -> Tuple[float, bool]:
    """(learning-rate scale, frozen) for one layer. Every layer gets a fully plastic window after it forms."""
    close = close_age(kind, born_years, rel_depth)
    if close is None:
        return 1.0, False
    scale = FLOOR + (1 - FLOOR) / (1 + math.exp((age_years - close) / 1.0))
    return scale, age_years >= max(FREEZE_FROM, close + 5.0)


def embedding_plasticity(age_years: float) -> float:
    return FLOOR + (1 - FLOOR) / (1 + math.exp((age_years - EMB_CLOSE) / 1.5))


def compute(cap: int, until_years: float = 30.0, ctx: int = 512) -> float:
    """Parameter-years up to an age: a rough measure of how much training the schedule costs."""
    total, step = 0.0, 1 / 12
    a = 0.0
    while a < until_years:
        total += param_count(target_shape(a, 0.0, cap, ctx)) * step
        a += step
    return total
