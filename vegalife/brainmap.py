"""His brain map: everything in his life as a graph of what led to what. Built here, no outside tools.

Nodes are the things in his life:
  factor, state, trait   what surrounds him and what he is (stress load, health, neuroticism...)
  situation, choice      what he faced and what he chose
  consequence            what a choice cost or gave him later
  event                  what happened to him (bullied, a friend moved away, a gene switched on)
  memory                 what he took from it, and how he recalls it
  person                 his friends
  skill, milestone       skills mastered or lost, the network growing

Edges say what led to what, and how we know:
  basis "exact"      recorded where it happened: a choice changed these states, this memory was recalled in that
                     decision, this event shifted that trait.
  basis "estimated"  a slow influence, measured by counterfactual: the month as he lived it, against the same month
                     with one factor set to its average, with the same randomness. Summed per life stage.
                     Contributions interact, so they do not add up to the total change.

"Led to" means within his simulated world: exact for its mechanics, estimated for slow influences, and silent about
anything the model does not simulate. Every node carries source="simulated", so a person's own entered life can
later sit in the same graph.

Storage is two append-only files in the run folder: brain_nodes.jsonl and brain_edges.jsonl.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import factors as fx

TRAITS = {"openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"}
# The states the slow-influence estimate looks at.
TRACKED = ["anxiety", "allostatic_load", "health", "academic", "community_support", "loneliness", "telomere",
           "insulin_resistance", "wealth", "attachment", "nihilism", "social_isolation", "sleep", "mood",
           "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
# Which factors drive each world event (they are the rates in world.py / people.py).
EVENT_DRIVERS = {"bullied": ["bullying"], "disaster": ["extreme_weather"], "move": ["housing_instability"],
                 "illness": ["early_antibiotics"], "study": ["higher_ed_path"], "home": ["housing_unaffordable"],
                 "work": ["algorithmic_hiring", "workplace_security", "skill_obsolescence"],
                 "gene": ["local_pollution", "extreme_weather", "genetic_risk"], "friend": ["friend_count"]}
STAGE_OF = fx.stage_of


class BrainMap:
    def __init__(self, run_dir: Optional[Path] = None):
        self.nodes: Dict[str, dict] = {}
        self.out: Dict[str, List[dict]] = defaultdict(list)
        self.inn: Dict[str, List[dict]] = defaultdict(list)
        self.dir = run_dir
        self._nf = open(run_dir / "brain_nodes.jsonl", "a", encoding="utf-8") if run_dir else None
        self._ef = open(run_dir / "brain_edges.jsonl", "a", encoding="utf-8") if run_dir else None
        self.counter = defaultdict(int)
        self.pending_estimates: Dict[tuple, float] = defaultdict(float)     # (factor, state, stage) -> sum of pushes
        self.pending_counts: Dict[tuple, int] = defaultdict(int)            # ... -> months checked
        self.pending_scale = 1.0

    # ------------------------------------------------------------------ building
    def node(self, nid: str, kind: str, label: str, age: Optional[int] = None, **props) -> str:
        if nid in self.nodes:
            if props:
                self.nodes[nid]["props"].update(props)
            return nid
        n = {"id": nid, "kind": kind, "label": label, "age": age, "source": "simulated", "props": props}
        self.nodes[nid] = n
        if self._nf:
            self._nf.write(json.dumps(n) + "\n")
        return nid

    def edge(self, src: str, dst: str, relation: str, weight: float = 1.0, age: Optional[int] = None,
             basis: str = "exact", **props) -> None:
        e = {"src": src, "dst": dst, "relation": relation, "weight": round(float(weight), 5), "age": age,
             "basis": basis, "props": props}
        self.out[src].append(e)
        self.inn[dst].append(e)
        if self._ef:
            self._ef.write(json.dumps(e) + "\n")

    def next_id(self, kind: str, age: int) -> str:
        self.counter[(kind, age)] += 1
        return f"{kind}:{age}:{self.counter[(kind, age)]}"

    def flush(self) -> None:
        for f in (self._nf, self._ef):
            if f:
                f.flush()

    def close(self) -> None:
        for f in (self._nf, self._ef):
            if f:
                f.close()

    # ------------------------------------------------------------------ well-known nodes
    def factor(self, key: str) -> str:
        f = fx.ALL[key]
        return self.node(f"factor:{key}", "factor", f.label, None, stage=f.stage, effect=f.effect)

    def state(self, key: str) -> str:
        return self.node(f"state:{key}", "trait" if key in TRAITS else "state", key.replace("_", " "))

    def person(self, name: str) -> str:
        return self.node(f"person:{name}", "person", name)

    def situation(self, key: str, text: str = "") -> str:
        return self.node(f"situation:{key}", "situation", key.replace("_", " "), None, example=text[:160])

    # ------------------------------------------------------------------ loading and querying (for the server)
    @classmethod
    def load(cls, run_dir: Path) -> "BrainMap":
        bm = cls(None)
        bm.dir = run_dir
        bm.extend(run_dir)
        return bm

    def extend(self, run_dir: Path, pos: Optional[dict] = None) -> dict:
        """Reads new lines from the files (from byte positions in `pos`) and returns the new positions."""
        pos = dict(pos or {"n": 0, "e": 0})
        for key, name in (("n", "brain_nodes.jsonl"), ("e", "brain_edges.jsonl")):
            path = run_dir / name
            if not path.exists():
                continue
            with open(path, "rb") as f:
                f.seek(pos[key])
                data = f.read()
            end = data.rfind(b"\n") + 1                      # only whole lines; a partial last line waits
            for line in data[:end].splitlines():
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if key == "n":
                    if obj["id"] in self.nodes:
                        self.nodes[obj["id"]]["props"].update(obj.get("props", {}))
                    else:
                        self.nodes[obj["id"]] = obj
                else:
                    self.out[obj["src"]].append(obj)
                    self.inn[obj["dst"]].append(obj)
            pos[key] += end
        return pos

    def importance(self, nid: str) -> float:
        return sum(abs(e["weight"]) for e in self.out.get(nid, ())) + sum(abs(e["weight"]) for e in self.inn.get(nid, ())) \
            + 0.2 * (len(self.out.get(nid, ())) + len(self.inn.get(nid, ())))

    def in_window(self, n: dict, a: Optional[int], b: Optional[int]) -> bool:
        if n["age"] is None:
            return True
        return (a is None or n["age"] >= a) and (b is None or n["age"] <= b)

    def subgraph(self, ids: Iterable[str], limit_edges: int = 3000) -> dict:
        ids = set(ids)
        edges = [e for i in ids for e in self.out.get(i, ()) if e["dst"] in ids][:limit_edges]
        return {"nodes": [self.nodes[i] for i in ids if i in self.nodes], "edges": edges}

    def top(self, a: Optional[int] = None, b: Optional[int] = None, n: int = 300, kinds: Optional[set] = None,
            q: str = "") -> dict:
        q = q.lower().strip()
        cand = [x for x in self.nodes.values() if self.in_window(x, a, b) and (not kinds or x["kind"] in kinds)
                and (not q or q in x["label"].lower() or q in json.dumps(x.get("props", {})).lower())]
        cand.sort(key=lambda x: -self.importance(x["id"]))
        return self.subgraph(x["id"] for x in cand[:max(1, min(n, 600))])

    def overview(self, a: Optional[int] = None, b: Optional[int] = None) -> dict:
        """The structure of his mind in an age window, with repeats grouped: each situation with what his choices in
        it changed overall, each kind of later consequence once, each kind of event once (with counts). Individual
        choices, memories and moments are left to search and trace."""
        import re
        nodes: Dict[str, dict] = {}
        agg: Dict[tuple, dict] = {}

        def keep(nid):
            if nid in self.nodes and nid not in nodes:
                nodes[nid] = self.nodes[nid]
            return nid

        def group(kind, label, age):
            gid = f"group:{kind}:{label}"
            g = nodes.get(gid)
            if g is None:
                g = nodes[gid] = {"id": gid, "kind": kind, "label": label, "age": age, "source": "simulated",
                                  "props": {"count": 0, "grouped": True, "first_age": age, "last_age": age}}
            g["props"]["count"] += 1
            g["props"]["last_age"] = age
            g["label"] = f"{label} (x{g['props']['count']})" if g["props"]["count"] > 1 else label
            return gid

        def add(src, dst, relation, w, basis="exact"):
            k = (src, dst, relation, basis)
            e = agg.get(k)
            if e is None:
                e = agg[k] = {"src": src, "dst": dst, "relation": relation, "weight": 0.0, "age": None, "basis": basis,
                              "props": {"n": 0}}
            e["weight"] += w
            e["props"]["n"] += 1

        clean = lambda t: re.sub(r"\s+", " ", re.sub(r"\d+", "#", t)).strip()
        stage_of = lambda n: keep(f"stage:{STAGE_OF(n['age'])}") if n.get("age") is not None else None
        for n in self.nodes.values():
            kind, nid = n["kind"], n["id"]
            if kind in ("factor", "state", "trait", "situation", "person"):
                continue                                  # included when something links to them
            if not self.in_window(n, a, b):
                continue
            if kind == "choice":
                sit = next((e["src"] for e in self.inn.get(nid, ()) if e["relation"] == "faced"), None)
                if not sit:
                    continue
                keep(sit)
                st = stage_of(n)
                if st:
                    add(sit, st, "during", 0.05)
                for e in self.out.get(nid, ()):
                    if e["relation"] == "changed":
                        add(sit, keep(e["dst"]), "his choices changed", e["weight"])
                    elif e["relation"] == "led to later":
                        cons = self.nodes.get(e["dst"])
                        if cons:
                            add(sit, group("consequence", clean(cons["label"]), cons["age"]), "led to later", 1.0)
            elif kind == "consequence":
                gid = group("consequence", clean(n["label"]), n["age"])
                nodes[gid]["props"]["count"] -= 1         # counted where its choice is seen, or below if orphaned
                if not any(e["relation"] == "led to later" for e in self.inn.get(nid, ())):
                    nodes[gid]["props"]["count"] += 1
                for e in self.out.get(nid, ()):
                    if e["relation"] == "changed":
                        add(gid, keep(e["dst"]), "changed", e["weight"])
                if stage_of(n):
                    add(gid, stage_of(n), "during", 0.05)
            elif kind == "event":
                gid = group("event", clean(n["label"]), n["age"])
                if stage_of(n):
                    add(gid, stage_of(n), "during", 0.05)
                for e in self.inn.get(nid, ()):
                    if e["src"].startswith(("factor:", "person:")):
                        add(keep(e["src"]), gid, e["relation"], 1.0)
                for e in self.out.get(nid, ()):
                    if e["relation"] in ("shaped", "ended his life"):
                        add(gid, keep(e["dst"]), e["relation"], e["weight"])
                for e in self.inn.get(nid, ()):
                    if e["src"].startswith("state:"):
                        add(keep(e["src"]), gid, e["relation"], e["weight"])
            elif kind in ("skill", "milestone"):
                keep(nid)
                for e in self.inn.get(nid, ()) + self.out.get(nid, ()):
                    keep(e["src"]), keep(e["dst"])
                    add(e["src"], e["dst"], e["relation"], e["weight"], e["basis"])
        for es in self.out.values():                      # factor-level links: drivers and slow influences
            for e in es:
                if not e["src"].startswith("factor:"):
                    continue
                if e["basis"] == "estimated" and e["dst"].startswith("state:"):
                    stage_age = e.get("age")
                    if a is not None and stage_age is not None and stage_age < a:
                        continue
                    add(keep(e["src"]), keep(e["dst"]), "pushes", e["weight"], "estimated")
                elif e["dst"].startswith("situation:") and e["dst"] in nodes:
                    add(keep(e["src"]), e["dst"], e["relation"], e["weight"])
        # the backbone: him, his stages in order, his states feeding his wellbeing, his innate seeds
        for nid in [SELF] + [f"stage:{st}" for st in STAGES]:
            keep(nid)
        for es in list(self.out.values()):
            for e in es:
                if e["relation"] in ("feeds his wellbeing", "then", "a stage of his life", "innate seed"):
                    add(keep(e["src"]), keep(e["dst"]), e["relation"], e["weight"])
        for e in agg.values():                            # repeated pushes: report the average push per stage
            if e["basis"] == "estimated" and e["props"]["n"]:
                e["weight"] /= e["props"]["n"]
            e["weight"] = round(e["weight"], 5)
        return {"nodes": list(nodes.values()), "edges": [e for e in agg.values() if e["src"] in nodes and e["dst"] in nodes]}

    def neighbourhood(self, nid: str) -> dict:
        return {"node": self.nodes.get(nid), "incoming": self.inn.get(nid, [])[:400], "outgoing": self.out.get(nid, [])[:400],
                "names": {e[k]: self.nodes.get(e[k], {}).get("label", e[k]) for e in self.inn.get(nid, [])[:400] + self.out.get(nid, [])[:400] for k in ("src", "dst")}}

    def trace(self, nid: str, direction: str = "up", depth: int = 4, limit: int = 300) -> dict:
        """What led here (up) or what this led to (down), following the strongest links first."""
        seen, frontier, edges = {nid}, [nid], []
        for _ in range(max(1, min(depth, 8))):
            nxt = []
            for cur in frontier:
                links = self.inn.get(cur, ()) if direction == "up" else self.out.get(cur, ())
                for e in sorted(links, key=lambda e: -abs(e["weight"]))[:25]:
                    other = e["src"] if direction == "up" else e["dst"]
                    edges.append(e)
                    if other not in seen and len(seen) < limit:
                        seen.add(other)
                        nxt.append(other)
            frontier = nxt
            if not frontier:
                break
        return {"nodes": [self.nodes[i] for i in seen if i in self.nodes],
                "edges": [e for e in edges if e["src"] in seen and e["dst"] in seen]}

    def stats(self) -> dict:
        kinds = defaultdict(int)
        for n in self.nodes.values():
            kinds[n["kind"]] += 1
        exact = sum(1 for es in self.out.values() for e in es if e["basis"] == "exact")
        total = sum(len(es) for es in self.out.values())
        return {"nodes": len(self.nodes), "edges": total, "exact": exact, "estimated": total - exact, "kinds": dict(kinds)}


# ---------------------------------------------------------------------- the backbone that makes it one brain
STAGES = ["infancy", "childhood", "adolescence", "early_adult", "middle_adult", "late_adult"]
SELF = "self:vega"
# How each state feeds his wellbeing (world.Person.wellbeing, averaged over stages): the links from states to him.
WELLBEING_LINKS = {"health": 0.24, "anxiety": -0.17, "allostatic_load": -0.08, "attachment": 0.05,
                   "community_support": 0.05, "loneliness": -0.05, "social_isolation": -0.05, "problem_solving": 0.03,
                   "resilience": 0.03, "academic": 0.03, "skill_value": 0.03, "motor": 0.03, "wealth": 0.03,
                   "housing": 0.03, "employed": 0.03, "pension": 0.03, "financial_paranoia": -0.03, "autonomy": 0.05,
                   "identity_crisis": -0.05, "goal_horizon": 0.05, "nihilism": -0.05, "household_friction": -0.05}


def stage_node(bm: BrainMap, stage: str) -> str:
    return bm.node(f"stage:{stage}", "stage", fx.STAGE_LABEL[stage])


def backbone(bm: BrainMap) -> None:
    """Him at the centre; his life stages in order; his states feeding his wellbeing; his innate trait seeds."""
    bm.node(SELF, "self", "Vega", None, note="him: every state feeds his wellbeing, every moment sits in a stage")
    prev = None
    for st in STAGES:
        sid = stage_node(bm, st)
        bm.edge(sid, SELF, "a stage of his life", 0.2)
        if prev:
            bm.edge(prev, sid, "then", 0.2)
        prev = sid
    for k, w in WELLBEING_LINKS.items():
        bm.edge(bm.state(k), SELF, "feeds his wellbeing", w)
    for t in sorted(TRAITS):
        bm.edge(bm.factor(f"trait_{t}"), bm.state(t), "innate seed", 0.5)


def during(bm: BrainMap, nid: str, age: int) -> None:
    bm.edge(nid, f"stage:{STAGE_OF(age)}", "during", 0.05, age)


# ---------------------------------------------------------------------- recording helpers (trainer and simulator)
def situation_drivers(bm: BrainMap, sc, p, F, age: int, eps: float = 0.1) -> None:
    """Which factors make this situation more or less likely, computed from its own rate: nudge each factor and see
    how the rate changes. Recorded once per situation per life stage."""
    key = ("drivers", sc.key, STAGE_OF(age))
    if bm.counter[key]:
        return
    bm.counter[key] = 1
    sid = bm.situation(sc.key)
    for k in F.values:
        old = F.values[k]
        lo, hi = max(0.0, old - eps), min(1.0, old + eps)       # two-sided, kept inside 0..1 (works at the ends)
        F.values[k] = hi
        up = sc.rate(p, F)
        F.values[k] = lo
        down = sc.rate(p, F)
        F.values[k] = old
        d = (up - down) / (hi - lo)
        if abs(d) > 0.02:
            bm.edge(bm.factor(k), sid, "makes likelier" if d > 0 else "makes rarer", d, age, "exact", stage=STAGE_OF(age))


def record_choice(bm: BrainMap, age: int, sc, sit: str, choice: int, deltas: dict, felt: float, real, recs, p,
                  answer: str = "") -> str:
    sid = bm.situation(sc.key, sit)
    cid = bm.next_id("choice", age)
    c = sc.choices[choice]
    bm.node(cid, "choice", f"{sc.key.replace('_', ' ')}: {c.text}", age, situation=sit[:200], answer=answer[:20],
            felt=round(felt, 3), real=None if real is None else round(real, 3),
            later={"deltas": c.later, "months": c.delay} if c.later else None)
    bm.edge(sid, cid, "faced", 1.0, age)
    during(bm, cid, age)
    for k, d in deltas.items():
        if abs(d) > 1e-6:
            bm.edge(cid, bm.state(k), "changed", d, age)
    for r in recs or ():
        bm.edge(f"mem:{r.episode_id}", cid, "recalled in", r.detail, age, distorted=r.distorted)
    if p.circle:
        for f in p.circle.friends:
            if f.name in sit:
                bm.edge(bm.person(f.name), cid, "involved in", 1.0, age)
    return cid


def record_memory(bm: BrainMap, src: str, ep, age: int) -> str:
    mid = bm.node(f"mem:{ep.id}", "memory", ep.what[:80], age, episode=ep.id, valence=ep.valence, feeling=ep.feeling,
                  salience=round(ep.salience, 3))
    bm.edge(src, mid, "remembered as", ep.salience, age)
    during(bm, mid, age)
    return mid


def record_event(bm: BrainMap, h: dict, age: int, trait_deltas: Optional[dict] = None) -> str:
    """A world event: what drove it, who was in it, and how it shifted his personality."""
    eid = bm.next_id("event", age)
    bm.node(eid, "event", h["text"][:90], age, valence=h.get("valence"), key=h.get("key"))
    key = h.get("key", "")
    for f in EVENT_DRIVERS.get(key, []):
        bm.edge(bm.factor(f), eid, "drove", 1.0, age)
    for name in h.get("who", []):
        bm.edge(bm.person(name), eid, "involved in", 1.0, age)
    if h.get("cause"):
        bm.edge(h["cause"], eid, "led to later", 1.0, age)
    for t, d in (trait_deltas or {}).items():
        bm.edge(eid, bm.state(t), "shaped", d, age)
    for t, d in (h.get("deltas") or {}).items():          # what a loss changed in his life, and the grief it began
        if abs(d) > 1e-6 and t not in (trait_deltas or {}):
            bm.edge(eid, bm.state(t), "began grief" if t == "grief" else "changed", d, age)
    if key == "dies":
        bm.edge(bm.state("health"), eid, "gave out", 1.0, age)
        bm.edge(eid, SELF, "ended his life", 1.0, age)
    during(bm, eid, age)
    return eid


def record_consequence(bm: BrainMap, item: tuple, age: int) -> str:
    """A delayed consequence arriving: (cause id, deltas, text, valence)."""
    cause, deltas, text, valence = item
    xid = bm.next_id("consequence", age)
    bm.node(xid, "consequence", text[:90], age, valence=valence)
    if cause:
        bm.edge(cause, xid, "led to later", 1.0, age)
    for k, d in deltas.items():
        bm.edge(xid, bm.state(k), "changed", d, age)
    during(bm, xid, age)
    return xid


def attribute_month(bm: BrainMap, p, F, character, age: int, factors: List[str], scale: float = 1.0) -> None:
    """Slow influences this month: for each factor, the month as he lived it against the same month with that factor
    at its average, with the same randomness. Choices are left out (their effects are exact edges). Summed per stage;
    `scale` stands in for the months a factor is not checked (each is checked every `scale` months)."""
    actual = p.clone()
    actual.step_month(F)
    character.step(actual, F)
    stage = STAGE_OF(age)
    for k in factors:
        mean = fx.ALL[k].mean
        if abs(F[k] - mean) < 0.05:
            continue
        cf = p.clone()
        G = F.copy()
        G.values[k] = mean
        cf.step_month(G)
        character.step(cf, G)
        for s in TRACKED:
            d = actual.s[s] - cf.s[s]
            if d:
                bm.pending_estimates[(k, s, stage)] += d
            bm.pending_counts[(k, s, stage)] += 1
    bm.pending_scale = scale


def flush_estimates(bm: BrainMap, age: int, threshold: float = 0.002) -> None:
    """Writes the stage's slow influences that matter as estimated edges, then starts the next stage. The weight is
    the average push per month (how much that month's change differs because of the factor); `total` estimates the
    push summed over the whole stage."""
    for key, total in list(bm.pending_estimates.items()):
        k, s, stage = key
        n = bm.pending_counts.get(key, 0)
        if not n:
            continue
        mean = total / n
        # a level he lives at (sleep, health) matters by its monthly push; a slow accumulator (stress load, telomeres,
        # wealth) by what it adds up to over the stage
        if abs(mean) >= threshold or abs(total * bm.pending_scale) >= 0.03:
            bm.edge(bm.factor(k), bm.state(s), "pushed up" if mean > 0 else "pushed down", mean, age, "estimated",
                    stage=stage, months_checked=n, total=round(total * bm.pending_scale, 4))
    bm.pending_estimates.clear()
    bm.pending_counts.clear()


ROTATION = 4


def rotating_factors(age: int, every: int = ROTATION) -> List[str]:
    """A quarter of the factors each month, so every factor is checked every 4 months and the cost stays small."""
    keys = sorted(fx.ALL)
    return [k for i, k in enumerate(keys) if i % every == age % every]
