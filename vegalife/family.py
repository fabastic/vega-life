"""The people he is born among, and losing them.

His family are people with their own ages: a mother and father, grandparents, brothers and sisters, often a pet, and
later perhaps a partner. They age and die at life-table rates (or when you schedule it), his friends can die too, and
some losses are not deaths: his parents' divorce, a break-up, a grandparent's dementia (still alive, no longer there).

Each loss starts its own grief, shaped by how close they were and who he is:

  path        share (close loss)   course                                   calibrated against
  resilient   ~45-50%              a sharp, short dip, gone in months       Bonanno et al. 2002 (widowhood, n=205)
  recovering  ~35-40%              heavy, then easing over a year or two    Bonanno 2002 "common grief/recovery"
  prolonged   ~10-15%              still heavy years later                  Lundorff 2017: PGD in 9.8% of bereaved;
                                                                            ~49% after violent or sudden death (2020)
  Risk of the prolonged path rises with closeness and dependency, a sudden death, neuroticism, insecure attachment,
  and falls with community support (Bonanno 2002: chronic grief tracks pre-loss dependency).

Grief is not a smooth line. Month to month it swings between facing the loss and getting on with life (Stroebe &
Schut's dual process), and it comes back on anniversaries. While it lasts it raises anxiety, stress load and
loneliness, lowers mood and sleep, and puts the person on his mind. Some losses also change his life:
  * a parent dying while he is a child: less care, a harder home, and a lasting tilt toward low mood
    (adult depression risk ~1.2x after a natural death, ~3x after a violent one; Simbi 2020, Danish registers)
  * losing a partner: his own risk of dying x1.41 for six months, x1.14 after that (Moon et al. 2011 meta-analysis)
  * any very close death, later in life: heart-attack risk ~21x on the first day, falling over the month
    (Mostofsky et al. 2012), averaged here into the month of the loss
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .factors import FactorSet

GOMPERTZ_A, GOMPERTZ_B = 3.5e-5, 0.09          # yearly death risk ~0.3% at 50, ~5% at 80, as in US life tables
LOSS_WEIGHT = {"mother": 1.0, "father": 0.95, "partner": 1.0, "child": 1.15, "sibling": 0.8, "grandparent": 0.6,
               "friend": 0.7, "pet": 0.35, "pregnancy": 0.55}
# Pregnancy: ~10-20% of known pregnancies end in miscarriage, mostly before 12 weeks (ACOG; Tommy's); stillbirth
# ~1 in 175 US births (CDC), 1 in 147 in a 2025 JAMA study; maternal death ~19 per 100,000 US births. About 1 in 6
# adults face infertility (WHO 2023): a year or more of trying without a pregnancy. Fathers grieve a lost pregnancy
# too, often unacknowledged ("stay strong for her"): their grief gets less support.
MISCARRIAGE, STILLBIRTH, MATERNAL_DEATH = 0.15, 0.006, 0.0002
# Among sudden deaths of people aged 15-64, the share that are suicides (suicide is a leading cause of death under 45).
SUICIDE_SHARE = 0.3
OTHER_LOSS = {"divorce": 0.45, "breakup": 0.6, "dementia": 0.4}
NAMES = ["Rose", "Arthur", "Mira", "Tomas", "Leela", "Omar", "Ines", "Kai", "Noor", "Felix", "Hana", "Jonah", "Asha",
         "Lev", "Maya", "Ravi", "Zoe", "Elio", "Sana", "Theo"]
PETS = ["Biscuit", "Pepper", "Mango", "Shadow", "Luna", "Toffee"]
TITLE = {"pregnancy": "their baby", "mother": "his mother", "father": "his father", "grandparent": "his grandparent", "sibling": "his sibling",
         "partner": "his partner", "pet": "the family pet", "friend": "his friend", "child": "his child"}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def monthly_death_risk(age_years: float) -> float:
    return 1 - math.exp(-GOMPERTZ_A * math.exp(GOMPERTZ_B * age_years) / 12)


@dataclass
class Relative:
    name: str
    relation: str                   # mother, father, grandparent, sibling, partner, pet
    born: int                       # his age in months when they were born (negative: before him)
    closeness: float
    joined: int = 0                 # month they come into his life (a partner, a pet)
    alive: bool = True
    died: Optional[int] = None
    cause: str = ""
    dies_at: Optional[int] = None   # set by you: the month (his age) they die
    lifespan: Optional[int] = None  # a pet's natural span, in months
    dementia: bool = False
    gone: bool = False              # left his life without dying (a divorce, a break-up)
    seeded: bool = True

    def age(self, month: int) -> float:
        return (month - self.born) / 12

    def present(self, month: int) -> bool:
        return self.alive and not self.gone and month >= self.joined

    def to_json(self, month: int) -> dict:
        return {"name": self.name, "relation": self.relation, "closeness": round(self.closeness, 2),
                "age": round(self.age(month if self.alive else self.died), 1), "alive": self.alive,
                "died_at_his_age": None if self.died is None else round(self.died / 12, 1), "cause": self.cause,
                "present": self.present(month), "dementia": self.dementia, "gone": self.gone,
                "joined_at_his_age": round(self.joined / 12, 1), "listed_by_user": not self.seeded}


@dataclass
class Loss:
    who: str
    relation: str
    kind: str                       # death, divorce, breakup, dementia
    month: int
    weight: float
    path: str                       # resilient, recovering, prolonged
    sudden: bool = False
    over: bool = False

    def intensity(self, now: int, facing: bool) -> float:
        t = now - self.month
        base = {"resilient": 0.45 * math.exp(-t / 2), "recovering": 0.85 * math.exp(-t / 9),
                "prolonged": 0.8 * math.exp(-t / 60)}[self.path]
        if self.kind == "dementia" and not self.over:
            base = max(base, 0.3)                 # ambiguous loss: no ending to grieve toward while they live
        if t > 0 and t % 12 == 0:
            base += 0.3 * math.exp(-t / 120)      # anniversaries bring it back, for years
        base *= 1.25 if facing else 0.75          # dual process: some months he faces it, some he gets on with life
        return clip(self.weight * base)


class Family:
    def __init__(self, F: FactorSet, seed: int, listed: Optional[List[dict]] = None, n_siblings: int = 0):
        self.rng = random.Random(seed * 7349 + 61)
        self.people: List[Relative] = []
        self.losses: List[Loss] = []
        self.grief = 0.0
        self.extra_hazard = 1.0
        self.expecting: Optional[int] = None      # the month a baby is due
        self.grandchildren = 0
        self.lose_at: Optional[int] = None         # a pregnancy that will not end in a birth
        self.lose_kind = ""
        self.trying = 0                            # months trying for a baby without a pregnancy
        self.ivf = False
        self.pregnancy_losses = 0
        if listed:
            for d in listed:
                self.add(d, seeded=False)
        else:
            self._seed(F, n_siblings)

    # ------------------------------------------------------------------ who he is born among
    def add(self, d: dict, seeded: bool = True) -> Relative:
        rel = str(d.get("relation", "sibling"))
        dies = d.get("dies_at_years")
        rv = Relative(name=str(d.get("name") or TITLE.get(rel, rel)), relation=rel,
                      born=-int(round(float(d.get("age_at_his_birth", 30)) * 12)),
                      closeness=clip(float(d.get("closeness", 0.6))),
                      joined=int(round(float(d.get("joins_at_years", 0)) * 12)),
                      dies_at=None if dies in (None, "", "null") else int(round(float(dies) * 12)),
                      seeded=seeded)
        if rel == "pet":
            rv.lifespan = int(round(float(d.get("lifespan_years", 13)) * 12))
        self.people.append(rv)
        return rv

    def _seed(self, F: FactorSet, n_siblings: int) -> None:
        r = self.rng
        warm = F["caregiver_warmth"]
        mum = clip(r.gauss(29, 5), 17, 45)
        dad = clip(mum + r.gauss(2.5, 3), 17, 60)
        self.people.append(Relative("Mum", "mother", -int(mum * 12), clip(0.55 + 0.4 * warm + r.gauss(0, 0.05))))
        self.people.append(Relative("Dad", "father", -int(dad * 12), clip(0.45 + 0.4 * warm + r.gauss(0, 0.08))))
        close = 0.3 + 0.5 * F["grandparent_caregivers"]
        for title, parent in (("Nana", mum), ("Grandad", mum), ("Grandma", dad), ("Grandpa", dad)):
            if r.random() < 0.85:                 # not every grandparent is still alive when he is born
                g = clip(parent + r.gauss(29, 4), parent + 16, parent + 45)
                self.people.append(Relative(title, "grandparent", -int(g * 12), clip(close + r.gauss(0, 0.1))))
        names = [n for n in NAMES]
        r.shuffle(names)
        for i in range(n_siblings):
            gap = r.choice([-1, 1]) * r.uniform(1.5, 7)
            self.people.append(Relative(names[i], "sibling", int(gap * 12), clip(r.gauss(0.55, 0.15))))
        if r.random() < 0.45:
            got = int(r.uniform(0, 10) * 12)
            self.people.append(Relative(r.choice(PETS), "pet", got, clip(r.gauss(0.6, 0.1)), joined=got,
                                        lifespan=int(r.uniform(10, 16) * 12)))

    def backfill(self, now: int) -> None:
        """For a life that began before families existed: who would already have died by now, quietly, with their
        grief already lived through (it no longer weighs on him, but it is part of his story)."""
        r = self.rng
        for rv in self.people:
            for m in range(max(0, rv.joined), now):
                a = rv.age(m)
                if rv.relation == "pet":
                    gone = m - rv.joined >= (rv.lifespan or 156)
                else:
                    gone = a > 0 and r.random() < monthly_death_risk(a)
                if gone:
                    rv.alive, rv.died, rv.cause = False, m, "after an illness" if rv.relation != "pet" else "of old age"
                    w = clip(LOSS_WEIGHT.get(rv.relation, 0.5) * (0.4 + 0.6 * rv.closeness))
                    self.losses.append(Loss(rv.name, rv.relation, "death", m, w, "recovering", over=True))
                    break

    # ------------------------------------------------------------------ queries
    def alive(self, relation: str) -> bool:
        return any(p.relation == relation and p.alive and not p.gone for p in self.people)

    def present(self, month: int) -> List[Relative]:
        return [p for p in self.people if p.present(month)]

    def on_mind(self, month: int) -> Optional[str]:
        """Who he is grieving most right now, if anyone."""
        live = [(l.intensity(month, True), l) for l in self.losses if not l.over]
        live = [x for x in live if x[0] > 0.2]
        return max(live, key=lambda x: x[0])[1].who if live else None

    def to_json(self, month: int) -> dict:
        return {"people": [p.to_json(month) for p in sorted(self.people, key=lambda p: p.born)],
                "grief": round(self.grief, 3),
                "losses": [{"who": l.who, "relation": l.relation, "kind": l.kind, "at_years": round(l.month / 12, 1),
                            "path": l.path, "sudden": l.sudden,
                            "now": round(l.intensity(month, True) / 1.25, 3)} for l in self.losses]}

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        """Ages and loses the people around him, then sets this month's grief. Returns what happened, as dicts for
        Person.note, and applies grief's pull on his state through p (which owns the state)."""
        r, m, s = self.rng, p.age, p.s
        out: List[dict] = []
        for rv in self.people:
            if not rv.alive or m < rv.joined:
                continue
            if rv.dies_at is not None:
                die = m >= rv.dies_at
                sudden = r.random() < 0.4
            elif rv.relation == "pet":
                die = m - rv.joined >= (rv.lifespan or 156)
                sudden = False
            else:
                a = rv.age(m)
                risk = monthly_death_risk(a) * (2.5 if rv.dementia else 1.0)
                if a < 55:
                    risk += 0.00004                # accidents and sudden illness at any age
                die = r.random() < risk
                sudden = r.random() < (0.5 if a < 60 else 0.2)
            if die:
                rv.alive, rv.died = False, m
                rv.cause = "suddenly" if sudden else "after an illness" if rv.relation != "pet" else "of old age"
                suicide = sudden and rv.relation != "pet" and 15 <= rv.age(m) < 65 and r.random() < SUICIDE_SHARE
                if suicide:
                    rv.cause = "by suicide"
                if not rv.gone:
                    out.append(self._lose(p, rv, "death", sudden))
                    if suicide:
                        self._suicide(out[-1], rv)
                continue
            if rv.relation == "grandparent" and not rv.dementia and rv.age(m) > 75 and r.random() < 0.0015:
                rv.dementia = True                 # alive, and slowly no longer there
                out.append(self._lose(p, rv, "dementia", False))
        out += self._partners(p, F)
        out += self._children(p, F)
        out += self._friends(p)
        # this month's grief: each loss on its own course, combined
        facing = r.random() < 0.5
        g = 1.0
        hazard = 1.0
        for l in self.losses:
            if l.over:
                continue
            x = l.intensity(m, facing)
            if x < 0.01 and m - l.month > 24:
                l.over = True
                continue
            g *= 1 - x
            t = m - l.month
            if l.relation == "partner" and l.kind == "death":
                hazard *= 1.41 if t < 6 else 1.14 if t < 36 else 1.0
            elif l.kind == "death" and t == 0 and l.weight >= 0.75 and p.years > 40:
                hazard *= 1 + 0.6 * l.weight       # the first month's heart risk, averaged over the month
        self.grief = 1 - g
        self.extra_hazard = hazard
        G = self.grief
        s["grief"] = G
        if G > 0.01:
            p.apply({"anxiety": 0.025 * G, "allostatic_load": 0.012 * G, "loneliness": 0.02 * G,
                     "nihilism": 0.004 * G}, fades=True)
            s["mood"] = clip(s["mood"] - 0.06 * G)
            s["sleep"] = clip(s["sleep"] - 0.03 * G)
        return out

    def _suicide(self, h: dict, rv: Relative) -> None:
        """A loss to suicide: guilt, 'why', and silence around it; the grief is more often prolonged."""
        h["text"] = h["text"].replace(" dies suddenly", " dies by suicide")
        if self.losses and self.rng.random() < 0.5:
            self.losses[-1].path = "prolonged"

    def _lose(self, p, rv: Relative, kind: str, sudden: bool) -> dict:
        """He loses someone: choose the grief's course from who he is, and change his life where it changes."""
        s, y, r = p.s, p.years, self.rng
        w = clip(LOSS_WEIGHT.get(rv.relation, 0.5) * (0.4 + 0.6 * rv.closeness) * (OTHER_LOSS.get(kind, 1.0)))
        p_prolonged = clip(0.02 + 0.07 * w + 0.12 * (s["neuroticism"] - 0.5) + 0.06 * (1 - s["attachment"]) * w
                           + 0.2 * sudden * w - 0.08 * (s["community_support"] - 0.5), 0.0, 0.6)
        p_resilient = clip(0.8 - 0.32 * w + 0.15 * (s["resilience"] - 0.3), 0.15, 0.9)
        u = r.random()
        path = "prolonged" if u < p_prolonged else "resilient" if u < p_prolonged + p_resilient else "recovering"
        self.losses.append(Loss(rv.name, rv.relation, kind, p.age, w, path, sudden))
        d: Dict[str, float] = {}
        child = y < 18
        if kind == "death" and rv.relation in ("mother", "father"):
            if child:
                d.update(caregiver_attention=-0.25 * w, household_friction=0.08, attachment=-0.08 * w,
                         wealth=-0.06 * (1 - s["wealth"]))
                d["neuroticism"] = 0.04 * w * (2.0 if sudden else 1.0)   # the lasting tilt toward low mood
            else:
                d.update(wealth=0.05, identity_crisis=0.05 * w)          # an inheritance; a generation gone
        elif kind == "death" and rv.relation == "partner":
            d.update(income=-0.12, identity_crisis=0.25, loneliness=0.25, community_support=-0.05)
        elif kind == "death" and rv.relation == "grandparent" and child:
            d.update(caregiver_attention=-0.1 * rv.closeness)
        elif kind == "divorce":
            d.update(household_friction=-0.15, caregiver_attention=-0.08, neuroticism=0.02)
        elif kind == "breakup":
            d.update(loneliness=0.15, identity_crisis=0.08)
        elif kind in ("miscarriage", "stillbirth"):
            d.update(anxiety=0.06, community_support=-0.03)     # a quiet loss: few people know, fewer ask him
        p.apply(d, fades=True)
        who = rv.name if rv.relation in ("mother", "father", "grandparent") else f"{TITLE.get(rv.relation, 'his')} {rv.name}"
        what = {"miscarriage": "they lose the pregnancy; the baby they were already imagining is gone",
                "stillbirth": "their baby is stillborn", "death": f"{who} dies{' suddenly' if sudden else ''}",
                "dementia": f"{rv.name} no longer knows who he is",
                "divorce": "his parents separate", "breakup": f"{rv.name} and he break up"}[kind]
        return {"text": what, "valence": -(0.4 + 0.6 * w), "arousal": 0.5 + 0.5 * w, "who": [rv.name],
                "key": "death" if kind == "death" else kind, "deltas": d | {"grief": round(w, 3)}}

    def _partners(self, p, F: FactorSet) -> List[dict]:
        r, m, y, out = self.rng, p.age, p.years, []
        mum = next((x for x in self.people if x.relation == "mother"), None)
        dad = next((x for x in self.people if x.relation == "father"), None)
        if y < 18 and mum and dad and mum.alive and dad.alive and not mum.gone and not dad.gone \
                and r.random() < 0.0011 * (0.5 + 1.5 * p.s["household_friction"]):
            dad.gone = True                       # a separation: he stays with his mother
            out.append(self._lose(p, dad, "divorce", False))
        partner = next((x for x in self.people if x.relation == "partner" and x.alive and not x.gone), None)
        if partner is None and 20 <= y < 60 and not any(x.relation == "partner" and x.seeded is False for x in self.people):
            if r.random() < 0.008 * (0.3 + F["partner_support"]) * (1.0 if y < 40 else 0.4):
                name = r.choice([n for n in NAMES if n not in {x.name for x in self.people}] or NAMES)
                partner = Relative(name, "partner", m - int(r.gauss(0, 3) * 12), clip(r.gauss(0.75, 0.1)), joined=m)
                self.people.append(partner)
                out.append({"text": f"falls in love with {name}", "valence": 0.7, "arousal": 0.7, "who": [name],
                            "key": "partner", "deltas": {}})
        elif partner is not None and partner.seeded and m - partner.joined < 120 and \
                r.random() < 0.003 * (1.3 - F["partner_support"]):
            partner.gone = True
            out.append(self._lose(p, partner, "breakup", False))
        return out

    def _children(self, p, F: FactorSet) -> List[dict]:
        """Wanting a child, the wait, the birth, the sleepless first year, and the milestones after.
        Parents' life satisfaction rises before a birth, drops in the first year (~1.4 points of 10 on average, with
        a third losing 2+), then usually recovers (Margolis & Myrskylä 2015)."""
        r, m, y, s, out = self.rng, p.age, p.years, p.s, []
        kids = [x for x in self.people if x.relation == "child"]
        partner = any(x.relation == "partner" and x.present(m) for x in self.people)
        lose_at = getattr(self, "lose_at", None)
        if self.expecting is not None and lose_at is not None and m >= lose_at:
            kind = self.lose_kind
            self.expecting, self.lose_at = None, None
            self.pregnancy_losses = getattr(self, "pregnancy_losses", 0) + 1
            baby = Relative("their baby", "pregnancy" if kind == "miscarriage" else "child", m, 0.8, alive=False,
                            died=m, cause=kind)
            out.append(self._lose(p, baby, kind, kind == "stillbirth"))
            if kind == "stillbirth":
                self.losses[-1].weight = clip(LOSS_WEIGHT["child"] * 0.9)
            return out
        if self.expecting is not None and m >= self.expecting:
            self.expecting = None
            if partner and r.random() < MATERNAL_DEATH:
                mum = next(x for x in self.people if x.relation == "partner" and x.present(m))
                mum.alive, mum.died, mum.cause = False, m, "in childbirth"
                out.append(self._lose(p, mum, "death", True))
            name = r.choice([n for n in NAMES if n not in {x.name for x in self.people}] or NAMES)
            kid = Relative(name, "child", m, clip(r.gauss(0.85, 0.08)), joined=m)
            self.people.append(kid)
            s["children"] = clip(0.5 + 0.25 * len(kids))
            d = {"oxytocin": 0.2, "dopamine": 0.1, "sleep": -0.1}
            parent = "a father: his" if F["sex"] >= 0.5 else "a mother: her"
            out.append({"text": f"becomes {parent} baby {name} is born", "valence": 0.9, "arousal": 0.95,
                        "who": [name], "key": "child", "deltas": d})
        elif self.expecting is None and 18 <= y < 46:
            chose = s["children"] >= 0.5 and not kids                    # he decided to have a child (scenarios)
            if chose:
                chance = 0.12 * (0.3 + s["fertility"])
            elif partner and len(kids) < 3:
                chance = 0.05 * (0.3 + s["fertility"]) * (1.0 - 0.45 * len(kids)) * (0.4 + F["partner_support"])
            else:
                chance = 0.0
            if not hasattr(self, "subfertile"):
                self.subfertile = r.random() < 0.15 + 0.1 * max(0.0, y - 32) / 8   # ~1 in 6 (WHO), more with age
            if self.subfertile and chance > 0:
                chance *= 0.15 * (3.0 if getattr(self, "ivf", False) else 1.0)
            if r.random() < chance:
                self.expecting = m + 9
                self.trying = 0
                u = r.random()
                if u < MISCARRIAGE * (1 + max(0.0, y - 35) / 10):          # rises with age
                    self.lose_at, self.lose_kind = m + r.randint(1, 3), "miscarriage"
                elif u < MISCARRIAGE + STILLBIRTH:
                    self.lose_at, self.lose_kind = m + 8, "stillbirth"
                out.append({"text": "learns they are expecting a baby", "valence": 0.7, "arousal": 0.7, "who": [],
                            "key": "child", "deltas": {"dopamine": 0.1}})
            elif chance > 0 and (chose or not kids):
                self.trying = getattr(self, "trying", 0) + 1
                if self.trying == 12 and self.subfertile:
                    d = {"anxiety": 0.06, "identity_crisis": 0.04}
                    p.apply(d, fades=True)
                    out.append({"text": "a year of trying for a baby, and nothing; every month hurts a little more",
                                "valence": -0.6, "arousal": 0.5, "who": [], "key": "infertility", "deltas": d})
                elif self.trying == 24 and not getattr(self, "ivf", False) and s["wealth"] > 0.35 \
                        and F["healthcare_access"] > 0.4 and r.random() < 0.6:
                    self.ivf = True
                    s["wealth"] = clip(s["wealth"] - 0.08)
                    out.append({"text": "they start IVF: injections, waiting, hoping", "valence": -0.1, "arousal": 0.6,
                                "who": [], "key": "infertility", "deltas": {"wealth": -0.08}})
        for k in kids:
            if not k.alive:
                continue
            a = m - k.born
            if a < 12:                                       # the first year: no sleep, worry, and love
                p.apply({"anxiety": 0.004, "allostatic_load": 0.003}, fades=True)
                s["sleep"] = clip(s["sleep"] - 0.05)
            moment = {12: f"{k.name} takes their first steps", 60: f"{k.name} starts school",
                      216: f"{k.name} leaves home", 264: f"{k.name} graduates"}.get(a)
            if moment and (a != 264 or r.random() < 0.5):
                out.append({"text": moment, "valence": 0.6 if a != 216 else 0.2, "arousal": 0.6, "who": [k.name],
                            "key": "child", "deltas": {}})
            if 336 <= a < 480 and self.grandchildren < 3 and r.random() < 0.004:
                self.grandchildren += 1
                out.append({"text": f"becomes a grandfather: {k.name} has a baby", "valence": 0.85, "arousal": 0.8,
                            "who": [k.name], "key": "child", "deltas": {"oxytocin": 0.15}})
            infant = 0.0004 if a < 12 else 0.0
            if r.random() < monthly_death_risk(a / 12) + infant + (0.00003 if a < 55 * 12 else 0.0):
                k.alive, k.died, k.cause = False, m, "suddenly"
                out.append(self._lose(p, k, "death", True))
        return out

    def _friends(self, p) -> List[dict]:
        out = []
        if not p.circle:
            return out
        for f in p.circle.friends:
            if f.present(p.age) and not getattr(f, "died", False):
                if self.rng.random() < monthly_death_risk(p.years) + (0.00003 if p.years < 55 else 0.0):
                    f.died, f.left = True, p.age
                    rv = Relative(f.name, "friend", p.age - 12 * int(p.years), f.closeness, alive=False, died=p.age,
                                  cause="suddenly")
                    out.append(self._lose(p, rv, "death", p.years < 60))
                    if p.years < 60 and self.rng.random() < SUICIDE_SHARE:
                        f.cause = "by suicide"
                        self._suicide(out[-1], rv)
        return out
