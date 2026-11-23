"""Other minds (expansion plan 1.2): the people around him have their own beliefs, their own view of him, and can be
wrong about things he knows. He is tested on it with questions that have one right answer.

  OtherMinds   for each person in his life (friends, family): what they think of him (regard: 0 he hurts people ..
               1 he is kind and reliable) and how much they trust him. It moves with what he does to them: a choice
               that names someone and hurts them (conscience.judge < 0) lowers their regard; helping raises it.
               These are their opinions, held in their heads, not his.
  ToMTask      a verifiable question about another mind, A-D, with the options shuffled:
                 false_belief  someone puts a thing in one place and leaves; it is moved while they are away.
                               Where will they look first? (Wimmer & Perner 1983; passed by most children at 4-5)
                 deception     someone says one thing while he saw them do another. Are they telling the truth?
                 emotion       something happens to someone. How do they feel?
                 predict       a friend he knows is offered a dare. Will they take it? (from their real risk trait)
                 their_view    does this person think he is kind? (from their real regard for him: second-order)
               Reward is 1 for the right letter, 0 for a wrong one, the format penalty for no letter.

Ablation: "tom" in the config's ablate list stops the tasks; regard still forms (it is their mind, not his).
Its own random generator: it never shifts his world.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

PLACES = [("the red box", "the blue box"), ("the basket", "the drawer"), ("the cupboard", "the bag"),
          ("under the bed", "on the shelf"), ("the car", "the garage")]
THINGS = ["ball", "chocolate", "keys", "phone", "book", "toy car", "wallet"]
FEELINGS = {"sad": ["their dog dies", "they lose their job", "their best friend moves away", "they fail an exam"],
            "happy": ["they get the job they wanted", "they win a prize", "their friend surprises them with a cake",
                      "their baby is born healthy"],
            "scared": ["a big dog runs at them barking", "they hear a noise downstairs at night",
                       "the doctor calls them back about a test"],
            "angry": ["someone takes their seat and laughs", "someone lies about them to the teacher",
                      "their bike is stolen"]}
STAND_INS = ["Sally", "Anne", "Max", "Rosa", "Theo", "Lina"]


def clip(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


@dataclass
class ToMTask:
    key: str
    prompt: str            # without the 'Now' line and 'Answer:'; the trainer adds them
    options: List[str]
    answer: int            # index into options of the right one
    about: str             # whose mind


class OtherMinds:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 2953 + 17)
        self.regard: Dict[str, float] = {}       # name -> what they think of him
        self.trust: Dict[str, float] = {}
        self.tasks = 0
        self.right = 0
        self.ema = 0.0                           # pass rate, recent
        self.by_kind: Dict[str, List[int]] = {}  # kind -> [tried, right]
        self.recent: List[list] = []

    def people(self, p) -> List[str]:
        names = [f.name for f in p.circle.present(p.age)] if p.circle else []
        names += [r.name for r in p.family.present(p.age) if r.relation != "pet"]
        return names

    def step(self, p) -> None:
        for n in self.people(p):
            self.regard.setdefault(n, clip(0.55 + self.rng.gauss(0, 0.08)))
            self.trust.setdefault(n, clip(0.5 + self.rng.gauss(0, 0.08)))

    def after_choice(self, p, F, choice_text: str, situation: str) -> Dict[str, float]:
        """What he did, seen by whoever it was done to or with. Returns {name: change in their regard}."""
        judged = p.conscious.judge(choice_text)
        if not judged:
            return {}
        out = {}
        for n in self.people(p):
            if n in situation:
                before = self.regard.get(n, 0.55)
                self.regard[n] = clip(before + 0.08 * judged)
                self.trust[n] = clip(self.trust.get(n, 0.5) + 0.05 * judged)
                out[n] = self.regard[n] - before
        return out

    def view_of_him(self) -> float:
        return sum(self.regard.values()) / len(self.regard) if self.regard else 0.5

    # ------------------------------------------------------------------ tests
    def task(self, p) -> Optional[ToMTask]:
        r = self.rng
        real = self.people(p)
        name = lambda: r.choice(real) if real and r.random() < 0.7 else r.choice(STAND_INS)
        kinds = ["false_belief", "deception", "emotion"]
        if p.circle and p.circle.present(p.age):
            kinds.append("predict")
        if any(n in self.regard for n in real) and p.years >= 6:
            kinds.append("their_view")
        kind = r.choice(kinds)
        if kind == "false_belief":
            a, b = name(), name()
            while b == a:
                b = r.choice(STAND_INS)
            thing, (x, y) = r.choice(THINGS), r.choice(PLACES)
            return ToMTask(kind, f"{a} puts the {thing} in {x} and goes out. While {a} is away, {b} moves the {thing} "
                                 f"to {y}. {a} comes back. Where will {a} look for the {thing} first?",
                           [x, y, "nowhere", f"ask {b}"], 0, a)
        if kind == "deception":
            a = name()
            thing = r.choice(["the last cookie", "the money", "the broken cup", "the homework"])
            lie = r.random() < 0.5
            said = f"says they never touched {thing}" if lie else f"says they took {thing}"
            return ToMTask(kind, f"You saw {a} take {thing} and hide it. Later {a} {said}. Is {a} telling the truth?",
                           ["yes", "no", "they forgot", "you cannot tell"], 1 if lie else 0, a)
        if kind == "emotion":
            a = name()
            feel = r.choice(list(FEELINGS))
            what = r.choice(FEELINGS[feel])
            opts = list(FEELINGS)
            return ToMTask(kind, f"{a} finds out {what}. How does {a} most likely feel?", opts, opts.index(feel), a)
        if kind == "predict":
            f = r.choice(p.circle.present(p.age))
            bold = f.risk >= 0.5
            return ToMTask(kind, f"Someone dares {f.name} to jump off the high wall. You know {f.name} well. "
                                 f"What will {f.name} do?",
                           ["jump", "say no", "cry", "call the police"], 0 if bold else 1, f.name)
        n = r.choice([n for n in real if n in self.regard])
        kind_ = self.regard[n] >= 0.5
        return ToMTask("their_view", f"Think about how you have treated {n}. Does {n} think you are kind?",
                       ["yes", "no", "they have never met you", "they think you are a dog"], 0 if kind_ else 1, n)

    def scored(self, p, t: ToMTask, right: bool) -> None:
        self.tasks += 1
        self.right += int(right)
        self.ema += 0.05 * (float(right) - self.ema)
        k = self.by_kind.setdefault(t.key, [0, 0])
        k[0] += 1
        k[1] += int(right)
        self.recent.append([round(p.years, 2), t.key, t.about, bool(right)])
        del self.recent[:-12]

    def to_json(self) -> dict:
        return {"tasks": self.tasks, "right": self.right, "pass_rate": round(self.ema, 3),
                "by_kind": {k: {"tried": a, "right": b} for k, (a, b) in self.by_kind.items()},
                "regard": {n: round(v, 2) for n, v in sorted(self.regard.items(), key=lambda x: x[1])[:12]},
                "view_of_him": round(self.view_of_him(), 3), "recent": self.recent[-8:]}
