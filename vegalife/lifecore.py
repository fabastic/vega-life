"""The parts of a month that do not involve the network, shared by the trainer and the no-network simulator, so both
live and record a month the same way.

  world_month   the world acts, his character forms, what happened goes into his memory, his present and his
                brain map (with the slow influences of the factors estimated by counterfactual)
  live_choice   after he has chosen (by network or at random): apply the choice, schedule what it leads to later,
                remember it, and record it in the brain map
"""
from __future__ import annotations

from typing import List, Optional

from . import brainmap as bmod
from .factors import stage_of

EVENT_DOMAIN = {"friend": "social", "bullied": "social", "home": "social", "work": "socioeconomic",
                "move": "socioeconomic", "study": "socioeconomic", "disaster": "socioeconomic", "illness": "biological",
                "consequence": "social", "death": "social", "divorce": "social", "breakup": "social",
                "dementia": "social", "partner": "social", "child": "social", "joy": "social", "retire": "socioeconomic",
                "burnout": "socioeconomic", "school": "socioeconomic", "exam": "socioeconomic", "fight": "social",
                "bond": "social", "repair": "social", "estranged": "social", "mental": "mental", "diagnosis": "mental",
                "recover": "mental", "help": "mental", "their_health": "social", "phone": "technological",
                "cyberbullied": "technological", "prejudice": "social", "bias": "social", "stood_up": "social", "out": "social",
                "sorrow": "mental", "infertility": "biological", "miscarriage": "social", "stillbirth": "social",
                "scam": "socioeconomic", "body": "biological",
                "hardship": "social", "good": "social"}
FEELING = (("anxiety", 0.015, "scared"), ("health", -0.02, "hurt"), ("peer_isolation", 0.015, "left out"),
           ("allostatic_load", 0.02, "worn out"), ("community_support", 0.015, "close to people"),
           ("attachment", 0.015, "safe"), ("resilience", 0.01, "capable"), ("academic", 0.015, "proud"))


def world_month(L, attribute: bool = True) -> List[str]:
    """L has: p, F, character, present, mem, brain (or None), say(text). Returns the month's event texts."""
    p, F = L.p, L.F
    age = p.age
    if L.brain is not None and attribute and p.alive:
        bmod.attribute_month(L.brain, p, F, L.character, age, bmod.rotating_factors(age), scale=bmod.ROTATION)
    events = p.step_month(F)
    for e in events:
        L.say(e)
    L.character.step(p, F)                                        # sleep, mood, and personality forming
    for h in p.happenings:
        shifts = {}
        if h["memorable"]:
            L.present.happened(age, h["text"], h["valence"])     # on his mind now...
            shifts = L.character.nudge(p, h["key"], h["valence"])  # ...shaping him a little...
        nid = None
        if L.brain is not None:
            if h["key"] == "consequence":
                nid = bmod.record_consequence(L.brain, (h["cause"], h["deltas"], h["text"], h["valence"]), age)
            else:
                nid = bmod.record_event(L.brain, h, age, shifts)
        if h["memorable"]:                                        # ...and becoming a memory that starts to fade
            ep = L.mem.add(age, "event", h["key"], EVENT_DOMAIN.get(h["key"], "social"), h["text"][:100], h["who"],
                           h["valence"], h["arousal"])
            if nid:
                bmod.record_memory(L.brain, nid, ep, age)
    p.happenings.clear()
    p.pending.clear()
    L.mem.consolidate(age, p.s["sleep"])                          # a night's sleep strengthens what was salient
    L.mem.step(age, p.s)
    if p.alive:                                                   # what wins his attention this month: his thoughts
        cs = p.conscious
        cs.step(p, F, L.present.moment(p, F, cs.rng, keep=False), L.mem)
    if L.brain is not None and (not p.alive or stage_of(p.age) != stage_of(age)):
        bmod.flush_estimates(L.brain, age)                        # a life stage ended: write its slow influences
    return events


def live_choice(L, sc, sit: str, choice: int, felt: float, real: Optional[float], recs, answer: str = "") -> dict:
    """He has chosen. Apply it, schedule its later consequence, remember it, record it. Returns the deltas."""
    p, F = L.p, L.F
    age = p.age
    c = sc.choices[choice]
    before = p.wellbeing()
    deltas = c.effect(p, F, L.r)
    p.apply(deltas, fades=True)
    p.conscious.after(p, F, c.text)                               # guilt or quiet pride, by his conscience
    cid = None
    if L.brain is not None:
        bmod.situation_drivers(L.brain, sc, p, F, age)
        cid = bmod.record_choice(L.brain, age, sc, sit, choice, deltas, felt, real, recs, p, answer)
    if deltas.get("children", 0) > 0:
        L.character.nudge(p, "children+", 1.0)
    if c.later:
        s = dict(p.s)
        for k, d in c.later.items():
            s[k] = min(1.0, max(0.0, s[k] + d))
        dv = p.wellbeing(s) - p.wellbeing()
        p.schedule(c.delay, c.later, f"{'it pays off' if dv >= 0 else 'pays the price'}: {c.text}",
                   max(-1.0, min(1.0, 25 * dv)), cause=cid)
    change = p.wellbeing() - before
    valence = max(-1.0, min(1.0, 25.0 * change))
    feeling = next((w for k, th, w in FEELING if (deltas.get(k, 0) < th if th < 0 else deltas.get(k, 0) > th)), "")
    names = [f.name for f in p.circle.friends if f.name in sit] if p.circle else []
    ep = L.mem.add(age, "scenario", sc.key, sc.domain, sit, names, valence, 0.25 + 0.75 * abs(valence), feeling,
                   "ABCD"[choice], c.text)
    if cid:
        bmod.record_memory(L.brain, cid, ep, age)
    return {"deltas": deltas, "wellbeing_change": change, "choice_id": cid}
