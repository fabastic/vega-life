"""His autobiographical memory: what he lived through, and what he can still recall of it.

Two kinds of memory are kept apart on purpose.
  * Skills and facts (counting, sums, how a sentence goes) live in the network's weights and fade only through disuse.
  * Episodes (this happened, I chose that, it went badly, Maya was there) live here. They fade.

Each episode is stored as fields, never as text, and the true record is never edited. What fades is how well he can
read it back:

  strength   whether he can find it at all. Falls with time; falls more slowly for emotional events and for ones he
             keeps going back to; faster under chronic stress, broken sleep and neurodegeneration. Below 4% it is gone.
  detail     how much of it is left. Falls faster than strength, so old memories survive as a gist.

Recalling is reconstructing: it strengthens the memory, and it can distort it. A distortion is stored beside the
true record (episode.distortion), so you can always see what happened and what he now remembers. Events before the
age of three are barely kept (infantile amnesia).
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

INFANTILE_AMNESIA_MONTHS = 36
GONE = 0.04
CAPACITY = 6000
STAGE_WORD = [(36, "a baby"), (144, "little"), (228, "a teenager"), (432, "young"), (672, "grown"), (10 ** 9, "older")]
TOPIC = {"social": "with people", "mental": "in my head", "biological": "with my body",
         "socioeconomic": "about money or school", "technological": "with technology", "education": "at school"}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class Episode:
    id: int
    age: int                      # month it happened
    kind: str                     # "scenario" | "event"
    key: str                      # scenario key or event type
    domain: str
    what: str                     # the situation, or the event, in one sentence
    who: List[str]
    did_letter: str               # what he chose (scenarios), else ""
    did_text: str
    valence: float                # how it turned out, -1 bad .. 1 good
    arousal: float                # how intense it was, 0 .. 1
    feeling: str
    salience: float
    strength: float
    detail: float = 1.0
    rehearsals: int = 0
    distortion: Optional[dict] = None       # {"valence":.., "did_letter":.., "who":[..]} what he now wrongly remembers
    recalled: int = 0


@dataclass
class Recollection:
    text: str
    episode_id: int
    detail: float
    distorted: bool = False


class Memory:
    def __init__(self, F, seed: int):
        self.rng = random.Random(seed * 40503 + 11)
        self.F = F
        self.episodes: List[Episode] = []
        self.next_id = 1
        self.forgotten = 0
        self.formed = 0
        self.names: Set[str] = set()
        self.last_seen: Dict[str, int] = {}           # key -> month last lived, for novelty
        self.state: Optional[Dict[str, float]] = None  # his live state (set by the trainer), for neuroticism

    # ------------------------------------------------------------------ forming memories
    def add(self, age: int, kind: str, key: str, domain: str, what: str, who: List[str], valence: float,
            arousal: float, feeling: str = "", did_letter: str = "", did_text: str = "") -> Episode:
        F = self.F
        novel = 1.0 if age - self.last_seen.get(key, -10 ** 6) > 24 else 0.0
        self.last_seen[key] = age
        emo = 0.6 + 0.8 * self._temper("emotional_intensity")
        salience = clip(0.45 * abs(valence) + 0.35 * clip(arousal * emo) + 0.2 * novel)
        strength = 0.6 + 0.4 * salience
        detail = 1.0
        if age < INFANTILE_AMNESIA_MONTHS:              # almost nothing from the first three years survives
            strength *= 0.15
            detail *= 0.4
        ep = Episode(self.next_id, age, kind, key, domain, what, list(who), did_letter, did_text, clip(valence, -1, 1),
                     clip(arousal), feeling or self._feeling(valence), salience, strength, detail)
        self.next_id += 1
        self.formed += 1
        self.names.update(who)
        self.episodes.append(ep)
        if len(self.episodes) > CAPACITY:
            self.episodes.sort(key=lambda e: e.strength)
            self.forgotten += len(self.episodes) - CAPACITY
            self.episodes = self.episodes[len(self.episodes) - CAPACITY:]
        return ep

    @staticmethod
    def _feeling(valence: float) -> str:
        return "glad" if valence > 0.25 else "bad" if valence < -0.25 else "flat"

    # ------------------------------------------------------------------ fading
    def tau(self, ep: Episode, state: Dict[str, float], age: int) -> float:
        """Months over which this memory's strength falls by a factor of e."""
        F = self.F
        t = 18.0 * (1 + 6 * ep.salience) * (1 + 0.6 * ep.rehearsals) * (0.5 + F["memory_strength"])
        t *= (1 - 0.4 * state.get("allostatic_load", 0.0)) * (1 - 0.7 * state.get("neurodegeneration", 0.0))
        t *= 0.7 + 0.3 * state.get("sleep", 1.0)       # poor sleep weakens consolidation
        return max(2.0, t)

    def consolidate(self, age: int, sleep: float) -> None:
        """Sleep replays the last month's salient episodes and strengthens them, more with better sleep. Replay
        favours salient experience (mostly rodent evidence). Nothing from before age three is consolidated."""
        for ep in self.episodes:
            if age - ep.age <= 1 and ep.age >= INFANTILE_AMNESIA_MONTHS:
                ep.strength = min(1.0, ep.strength + 0.15 * sleep * ep.salience)

    def _temper(self, factor: str) -> float:
        """A memory temperament factor, half set by the user and half by his current neuroticism (if known)."""
        n = self.state.get("neuroticism") if self.state is not None else None
        return self.F[factor] if n is None else 0.5 * self.F[factor] + 0.5 * n

    def step(self, age: int, state: Dict[str, float]) -> None:
        keep = []
        for ep in self.episodes:
            t = self.tau(ep, state, age)
            ep.strength *= math.exp(-1.0 / t)
            ep.detail = max(0.05, ep.detail * math.exp(-1.0 / (0.5 * t)))
            if ep.strength < GONE:
                self.forgotten += 1
            else:
                keep.append(ep)
        self.episodes = keep

    # ------------------------------------------------------------------ remembering
    def _view(self, ep: Episode) -> dict:
        d = ep.distortion or {}
        return {"valence": d.get("valence", ep.valence), "did_letter": d.get("did_letter", ep.did_letter),
                "did_text": d.get("did_text", ep.did_text), "who": d.get("who", ep.who)}

    def render(self, ep: Episode, true: bool = False, detail: Optional[float] = None) -> str:
        """The memory as he would tell it now (or as it truly was, with true=True)."""
        d = 1.0 if true else (ep.detail if detail is None else detail)
        v = {"valence": ep.valence, "did_letter": ep.did_letter, "did_text": ep.did_text, "who": ep.who} if true \
            else self._view(ep)
        yrs = ep.age // 12
        if d >= 0.75:
            when = f"When I was {yrs}"
        elif d >= 0.5:
            when = f"When I was about {max(1, round(yrs / 2) * 2)}"
        elif d >= 0.25:
            when = "When I was " + next(w for lim, w in STAGE_WORD if ep.age < lim)
        else:
            when = ""
        what = ep.what if d >= 0.5 else (f"something {TOPIC.get(ep.domain, 'happened')}" if d >= 0.25 else "")
        if d < 0.75:                                    # names go first
            for n in sorted(self.names, key=len, reverse=True):
                what = re.sub(rf"\b{re.escape(n)}\b", "a friend", what)
        # What he did, in words: the options are shown in a new order each time, so a letter would mean nothing.
        did = (f" I chose to {v['did_text']}." if v["did_text"] else f" I chose {v['did_letter']}.") \
            if d >= 0.75 and (v["did_text"] or v["did_letter"]) else ""
        word = "well" if v["valence"] > 0.15 else "badly" if v["valence"] < -0.15 else "okay"
        outcome = f" It went {word}." if d >= 0.25 else ""
        feel = f" I felt {ep.feeling}." if d < 0.25 or d >= 0.75 else ""
        parts = [p for p in (when, what) if p]
        text = ", ".join(parts)
        text = (text + "." if text and not text.endswith(".") else text) + did + outcome + feel
        return text.strip() or f"I felt {ep.feeling}, but I do not know why."

    def recall(self, cues: Set[str], age: int, state: Dict[str, float], k: int = 1, max_bytes: int = 120,
               rehearse: bool = True) -> List[Recollection]:
        """What comes to mind for these cues. Remembering strengthens a memory and may distort it, unless
        rehearse=False (used when building lessons, so that lessons do not alter his memory)."""
        r, F = self.rng, self.F
        scored = []
        for ep in self.episodes:
            overlap = 1.0 if ep.key in cues else 0.7 if any(w in cues for w in ep.who) else 0.5 if ep.domain in cues else 0.0
            if overlap == 0.0:
                continue
            p = clip(ep.strength * overlap * 1.4 * (0.5 + 0.5 * F["memory_strength"] + 0.2))
            if r.random() < p:
                scored.append((ep.strength * overlap + 0.05 * r.random(), ep))
        scored.sort(key=lambda t: -t[0])
        out = []
        for _, ep in scored[:k]:
            text = self.render(ep)
            if len(text) + len("Memory: ") > max_bytes:
                text = text[: max_bytes - len("Memory: ") - 3].rstrip() + "..."
            out.append(Recollection(text, ep.id, ep.detail, ep.distortion is not None))
            if rehearse:
                self._reconsolidate(ep, state)
        return out

    def _reconsolidate(self, ep: Episode, state: Dict[str, float]) -> None:
        """Remembering rewrites a memory a little: it is strengthened, and the gaps may be filled in wrongly."""
        r, F = self.rng, self.F
        ep.recalled += 1
        ep.rehearsals += 1
        ep.strength = min(1.0, ep.strength + 0.12)
        p = clip(0.03 + 0.1 * state.get("anxiety", 0.0) + 0.25 * state.get("neurodegeneration", 0.0)
                 + 0.05 * self._temper("rumination")) * (1 - ep.detail)
        if r.random() < p:
            d = dict(ep.distortion or {})
            roll = r.random()
            if roll < 0.5:                              # colours the memory with today's mood
                base = d.get("valence", ep.valence)
                d["valence"] = clip(base - 0.4 * state.get("anxiety", 0.0) + 0.2 * state.get("community_support", 0.0), -1, 1)
            elif roll < 0.8 and ep.did_letter:          # misremembers what he chose
                d["did_letter"] = r.choice([c for c in "ABCD" if c != ep.did_letter])
                others = [t for t in _options(ep.key) if t != ep.did_text]
                if ep.did_text and others:
                    d["did_text"] = r.choice(others)
            elif ep.who and len(self.names) > 1:        # puts the wrong person there
                d["who"] = [r.choice(sorted(self.names - set(ep.who)) or ep.who)]
            ep.distortion = d or None

    def reminisce(self, state: Dict[str, float], max_bytes: int = 120) -> List[Recollection]:
        """Memories that surface on their own: vivid and unpleasant ones when he is anxious or ruminating, otherwise
        whatever is strongest. These are the 'Memory:' lines in what he hears himself think."""
        r, F = self.rng, self.F
        anxiety = state.get("anxiety", 0.0)
        pool = [e for e in self.episodes if e.strength > 0.1]
        if not pool:
            return []
        rum = self._temper("rumination")
        if r.random() < 0.5 * anxiety * (0.3 + rum):                        # an intrusion
            bad = [e for e in pool if e.valence < -0.3 and e.arousal > 0.5]
            if bad:
                ep = max(bad, key=lambda e: e.strength * e.arousal + r.random() * 0.1)
                return self._one(ep, state, max_bytes)
        weights = [e.strength * (1 + (1 - e.valence) * rum) for e in pool]
        ep = r.choices(pool, weights)[0]
        return self._one(ep, state, max_bytes)

    def _one(self, ep: Episode, state, max_bytes: int) -> List[Recollection]:
        text = self.render(ep)
        if len(text) + 8 > max_bytes:
            text = text[: max_bytes - 11].rstrip() + "..."
        out = [Recollection(text, ep.id, ep.detail, ep.distortion is not None)]
        self._reconsolidate(ep, state)
        return out

    # ------------------------------------------------------------------ for the UI and saving
    def summary(self, now: int, samples: int = 8) -> dict:
        eps = self.episodes
        show = random.Random(now)                 # for display only: must not move his memory's own randomness
        pick = sorted(eps, key=lambda e: -e.salience)[: samples // 2] + show.sample(eps, min(samples // 2, len(eps)))
        seen, rows = set(), []
        for e in pick:
            if e.id in seen:
                continue
            seen.add(e.id)
            rows.append({"id": f"mem:{e.id}", "age_years": round(e.age / 12, 1), "key": e.key, "true": self.render(e, true=True),
                         "recalled": self.render(e), "strength": round(e.strength, 2), "detail": round(e.detail, 2),
                         "distorted": e.distortion is not None, "recalled_times": e.recalled})
        return {"kept": len(eps), "forgotten": self.forgotten, "formed": self.formed,
                "mean_detail": round(sum(e.detail for e in eps) / len(eps), 3) if eps else 0.0,
                "mean_strength": round(sum(e.strength for e in eps) / len(eps), 3) if eps else 0.0,
                "distorted": sum(1 for e in eps if e.distortion), "samples": rows}

    def dump(self, limit: int = 400) -> List[dict]:
        top = sorted(self.episodes, key=lambda e: -e.strength)[:limit]
        return [{**e.__dict__} for e in top]


def _options(key: str) -> List[str]:
    """The other things he could have done in that kind of situation (what a misremembered choice turns into)."""
    from .scenarios import ALL_SCENARIOS                # late import: scenarios is built on top of the world
    return next(([c.text for c in sc.choices] for sc in ALL_SCENARIOS if sc.key == key), [])


def retention(delta_months: float, state: Dict[str, float], F) -> float:
    """Share of an old month of ordinary life that is still replayed to the network (not lessons)."""
    tau = 72.0 * (0.5 + F["memory_strength"]) * (1 - 0.4 * state.get("allostatic_load", 0.0)) \
        * (1 - 0.7 * state.get("neurodegeneration", 0.0)) * (0.7 + 0.3 * state.get("sleep", 1.0))
    return 0.1 + 0.9 * math.exp(-max(0.0, delta_months) / max(6.0, tau))


def fade_lines(lines: List[str], keep: float, rng: random.Random) -> List[str]:
    """An old month as he can still replay it: some lines gone, the rest cut short when the memory is weak."""
    out = []
    for ln in lines:
        if rng.random() > keep:
            continue
        if keep < 0.5 and len(ln) > 40 and rng.random() < 0.5:
            ln = ln[: int(len(ln) * (0.4 + keep))]
        out.append(ln)
    return out
