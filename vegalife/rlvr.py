"""Reinforcement learning from verifiable rewards, one situation at a time.

For each scenario or problem life throws at him, the model samples a group of K answers. Each answer is scored
by the simulator, not a judge: a problem's answer is right or wrong, and a scenario's choice is scored by how
much it changes his wellbeing when its effect is applied to a copy of his state. Advantages are rewards minus
the group mean, divided by the group std (GRPO without a KL term).

Two scores are kept apart:
  the real outcome   the wellbeing change, including consequences that arrive later, undiscounted. Used to judge
                     what was good (caregivers' advice, memories, the UI).
  the felt outcome   the same change as a human feels it at the moment of choosing (character.Character.felt):
                     losses weigh more, later consequences are discounted, and untried choices are a little more
                     attractive. Used only as his learning signal.

The answer he lives is sampled separately from the learning group, at a temperature set by his state (stress
narrows it, lack of sleep loosens it), so the learning group always keeps the same spread.
"""
from __future__ import annotations

import random
import re
from typing import Callable, List, Optional, Tuple

import torch

from .factors import FactorSet
from .model import BOS, Mind, decode, encode
from .optim import backward_step
from .scenarios import Problem, Scenario
from .world import Person

FORMAT_PENALTY = -0.3
SCALE = 25.0          # wellbeing changes are small; this puts a typical choice in [-1, 1]


def parse_choice(text: str) -> int:
    t = text.strip()
    return "ABCD".index(t[0]) if t and t[0] in "ABCD" else -1


def parse_int(text: str):
    m = re.match(r"\s*(-?\d+)", text)
    return int(m.group(1)) if m else None


def outcome(sc: Scenario, p: Person, F: FactorSet, choice: int, r: random.Random, draws: int = 4) -> Tuple[float, float]:
    """(now, later): the expected wellbeing change now, and the further change when the later consequence arrives,
    averaged over a few draws of the choice's random outcome."""
    c = sc.choices[choice]
    before = p.wellbeing()
    now = later = 0.0
    for _ in range(draws):
        s = dict(p.s)
        for k, d in c.effect(p, F, r).items():
            s[k] = min(1.0, max(0.0, s[k] + d))
        w1 = p.wellbeing(s)
        now += w1 - before
        if c.later:
            for k, d in c.later.items():
                s[k] = min(1.0, max(0.0, s[k] + d))
            later += p.wellbeing(s) - w1
    return now / draws, later / draws


def score_scenario(sc: Scenario, p: Person, F: FactorSet, choice: int, r: random.Random, draws: int = 4,
                   character=None, novelty: Optional[Callable[[int], float]] = None) -> float:
    """The real outcome of a choice (character=None), or the outcome as he feels it (with his character, plus a
    novelty pull toward choices he has rarely made)."""
    if choice < 0:
        return FORMAT_PENALTY
    now, later = outcome(sc, p, F, choice, r, draws)
    if character is None:
        return max(-1.0, min(1.0, SCALE * (now + later)))
    felt = SCALE * character.felt(p, now, later, sc.choices[choice].delay)
    return max(-1.0, min(1.0, felt + (novelty(choice) if novelty else 0.0)))


def score_problem(pr: Problem, text: str) -> float:
    v = parse_int(text)
    if v is None:
        return FORMAT_PENALTY
    return 1.0 if v == pr.answer else 0.0


def grpo(model: Mind, opt, prompt: str, scorer: Callable[[str], float], k: int, max_new: int,
         temperature: float, device, scaler_ctx, lived_temperature: Optional[float] = None
         ) -> Tuple[List[str], List[float], float, str, float]:
    """One GRPO update on one prompt. Returns (responses, rewards, loss, lived answer, its reward).

    The lived answer is drawn before the update, from the same policy, at `lived_temperature` (or is the first
    group sample if none is given)."""
    ctx = model.shape.ctx
    toks = ([BOS] + encode(prompt))[-(ctx - max_new):]
    idx = torch.tensor([toks] * k, device=device)
    model.eval()
    with scaler_ctx():
        gen, lengths = model.generate(idx, max_new, temperature)
        if lived_temperature is not None:
            lg, ll = model.generate(idx[:1], max_new, max(0.05, lived_temperature))
    texts = [decode(gen[i, : int(lengths[i])].tolist()) for i in range(k)]
    rewards = [scorer(t) for t in texts]
    if lived_temperature is not None:
        lived = decode(lg[0, : int(ll[0])].tolist())
        lived_reward = scorer(lived)
    else:
        lived, lived_reward = texts[0], rewards[0]
    rt = torch.tensor(rewards, device=device)
    std = rt.std()
    if k < 2 or float(std) < 1e-6:
        return texts, rewards, 0.0, lived, lived_reward       # the whole group scored the same: nothing to learn
    adv = (rt - rt.mean()) / (std + 1e-4)
    model.train()
    full = torch.cat([idx, gen], 1)
    n_prompt = idx.shape[1]
    with scaler_ctx():
        logits = model(full[:, :-1])[:, n_prompt - 1:].float()
    logp = torch.log_softmax(logits, -1).gather(-1, gen[..., None]).squeeze(-1)
    steps = torch.arange(gen.shape[1], device=device)[None, :]
    mask = (steps < lengths[:, None]).float()
    loss = -(adv[:, None] * logp * mask).sum() / mask.sum().clamp(min=1)
    backward_step(opt, model, loss)
    return texts, rewards, float(loss), lived, lived_reward
