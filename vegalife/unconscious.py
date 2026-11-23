"""What shapes him without his knowing (expansion plan 1.3).

His explicit memories (memory.py) can be recalled and told; they fade and get rewritten. This is the other kind:
traces he cannot retrieve or put into words, which still bias what he does.

  implicit tags      every cue he meets (a kind of situation, a domain, a person's name) carries an affective tag:
                     a running average of how things went when it was there. It fades far more slowly than an
                     episode does, so a cue can keep its pull after the memory behind it is gone (implicit memory
                     outlasting explicit memory: Tulving; Squire 1992).
  mere exposure      cues he meets often become a little more comfortable for that alone (Zajonc 1968).
  unresolved         a strongly felt bad event that nothing has resolved (no repair, no recovery, no help) stays open.
                     While open, it adds a little tension to choices touching the same cue, and it can surface
                     unbidden into his thoughts. It closes when a good event with the same cue arrives, or slowly
                     with time.

How it acts: an approach/avoid bias on how a choice feels (bias). It never changes his state directly.
Ablation: "implicit" in the config's ablate list switches it off (no tags formed, no bias), so it can be compared
against "memory" (explicit memories hidden from his decisions).
Its own random generator: it never shifts his world.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

RESOLVES = {"repair", "recover", "help", "there_for", "justice", "good", "joy", "bond"}


class Unconscious:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 3571 + 11)
        self.off = False
        self.tag: Dict[str, float] = {}        # cue -> affect, -1..1
        self.seen: Dict[str, int] = {}         # cue -> times met
        self.open: List[dict] = []             # unresolved: {"cue", "who", "text", "since", "weight"}
        self.surfaced = ""

    def cues(self, key: str, domain: str, who) -> List[str]:
        return [c for c in [key, domain, *list(who or [])] if c]

    def take(self, age: int, key: str, domain: str, who, valence: float, arousal: float, text: str) -> None:
        if self.off:
            return
        cs = self.cues(key, domain, who)
        rate = 0.15 * (0.5 + arousal)
        for c in cs:
            self.tag[c] = self.tag.get(c, 0.0) + rate * (valence - self.tag.get(c, 0.0))
            self.seen[c] = self.seen.get(c, 0) + 1
        if key in RESOLVES or valence > 0.3:
            for o in self.open:
                if o["cue"] in cs or (o["who"] and set(o["who"]) & set(cs)):
                    o["weight"] *= 0.3
        if valence < -0.5 and arousal > 0.5 and key not in RESOLVES:
            self.open.append({"cue": key, "who": list(who or []), "text": text[:80], "since": age,
                              "weight": -valence * arousal})
        self.open = [o for o in self.open if o["weight"] > 0.05][-12:]

    def step(self, age: int) -> None:
        """Monthly: tags decay very slowly; open conflicts ease a little; one may surface into his thoughts."""
        if self.off:
            return
        for c in list(self.tag):
            self.tag[c] *= 0.998
            if abs(self.tag[c]) < 1e-3:
                del self.tag[c]
        for o in self.open:
            o["weight"] *= 0.985
        self.surfaced = ""
        if self.open and self.rng.random() < 0.15:
            o = max(self.open, key=lambda o: o["weight"] * self.rng.random())
            self.surfaced = o["text"]

    def bias(self, key: str, domain: str, situation: str, choice_text: str) -> float:
        """Approach or avoid, felt before he chooses, from cues he cannot name. Small: about -0.1..+0.1."""
        if self.off:
            return 0.0
        cs = [key, domain] + [c for c in self.tag if c[:1].isupper() and c in situation]
        affect = sum(self.tag.get(c, 0.0) for c in cs) / max(1, len(cs))
        familiar = sum(min(1.0, self.seen.get(c, 0) / 40) for c in cs) / max(1, len(cs))
        tension = sum(o["weight"] for o in self.open if o["cue"] in cs or set(o["who"]) & set(cs))
        # avoiding the cue (doing nothing, leaving) feels safer when tension is high
        avoid = any(w in choice_text.lower() for w in ("leave", "ignore", "stay home", "walk away", "say no", "skip"))
        out = 0.08 * affect + 0.02 * familiar + (0.05 if avoid else -0.03) * min(1.0, tension)
        return max(-0.1, min(0.1, out))

    def to_json(self) -> dict:
        top = sorted(self.tag.items(), key=lambda x: -abs(x[1]))[:10]
        return {"off": self.off, "tags": {k: round(v, 3) for k, v in top},
                "unresolved": [{"text": o["text"], "since_years": round(o["since"] / 12, 1),
                                "weight": round(o["weight"], 2)} for o in self.open[-6:]],
                "surfaced": self.surfaced}
