"""The language around him: what he hears and later reads, month by month. This is his pretraining data.

How much he gets is set by the factors: talk at home, how much attention he gets, parents' education, school,
crisis news in his feed, work. Any .txt files in the run's corpus folder become things he can read from school
age on, in the amount his access to education allows.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

from .factors import FactorSet, school_effectiveness
from .present import problem_scene
from .scenarios import MEMORY_BYTES
from .world import Person

KIN = {"mother": ["Mama", "Mum", "Amma"], "father": ["Dada", "Papa", "Baba"], "grandma": ["Nana", "Grandma", "Dadi"]}
OBJECTS = ["ball", "cup", "spoon", "dog", "cat", "shoe", "milk", "bed", "book", "car", "bird", "tree", "water", "bath"]
ADJ = ["big", "little", "red", "warm", "soft", "loud", "wet", "happy", "sleepy", "funny"]
VERBS = ["look at", "hold", "throw", "eat", "find", "see", "push", "give me", "show me", "touch"]
PLACES = ["school", "the park", "the shop", "the bus stop", "grandma's house", "the clinic", "the library", "work"]
FEEL_WORDS = ["happy", "sad", "scared", "angry", "tired", "proud", "lonely", "calm", "worried", "excited"]
HEADLINES = ["Record heat again this summer", "Rents rise faster than wages for the tenth year",
             "Experts warn of economic collapse", "Floods displace thousands", "AI expected to replace millions of jobs",
             "Sea levels rising faster than predicted", "Young people say they will never own a home",
             "Another species declared extinct"]
WORK = ["Please review the report before the meeting.", "The system flagged your ticket as resolved.",
        "Your shift starts at seven tomorrow.", "We are restructuring the team.", "Your application was not selected.",
        "Training on the new software is mandatory.", "Thanks for staying late."]


class Speech:
    def __init__(self, F: FactorSet, seed: int, corpus_dir: Optional[Path] = None):
        self.mem = None                               # memory.Memory, set by the trainer
        self.present = None                           # present.Present, set by the trainer
        self.r = random.Random(seed * 31337 + 5)
        self.name = "Vega"
        self.kin = {k: self.r.choice(v) for k, v in KIN.items()}
        self.corpus: List[str] = []
        if corpus_dir and corpus_dir.exists():
            for f in sorted(corpus_dir.glob("*.txt")):
                text = f.read_text(encoding="utf-8", errors="replace")
                self.corpus += [p.strip() for p in text.split("\n\n") if len(p.strip()) > 40]

    # one utterance, richer with parents' education and his age
    def _caregiver(self, p: Person, F: FactorSet) -> str:
        r, y = self.r, p.years
        who = self.kin["grandma"] if F["grandparent_caregivers"] > 0.5 and r.random() < 0.6 else \
            self.kin["mother"] if r.random() < 0.55 else self.kin["father"]
        from .present import living_carer
        who = living_carer(p, self.kin, who)               # nobody speaks to him after they have died
        o, a, v = r.choice(OBJECTS), r.choice(ADJ), r.choice(VERBS)
        simple = [f"{self.name}, {v} the {o}.", f"Look, a {a} {o}!", f"Where is the {o}?", f"{who} loves you.",
                  f"Good job, {self.name}!", f"Say {o}. {o.capitalize()}.", f"Time for {r.choice(['milk', 'bath', 'bed'])}."]
        if y < 2 or F["parent_education"] < 0.3:
            return f"{who}: {r.choice(simple)}"
        rich = [f"{who}: The {o} is {a} because it was left in the sun.",
                f"{who}: Do you feel {r.choice(FEEL_WORDS)}? It is okay to feel that way.",
                f"{who}: Tomorrow we will go to {r.choice(PLACES)} and see the {o}.",
                f"{who}: If you {v} the {o}, what do you think will happen?",
                f"{who}: I was {r.choice(FEEL_WORDS)} today, but talking about it helps."]
        return r.choice(rich if r.random() < 0.3 + 0.6 * F["parent_education"] else simple)

    def _school(self, p: Person, F: FactorSet) -> str:
        """A line from school. The curriculum factors decide which kind of lesson it is; teacher warmth sets the tone."""
        r = self.r
        a, b = r.randint(1, 20), r.randint(1, 20)
        kind = r.choices(["math", "language", "feelings", "play"],
                         [F["curr_math"] + 0.05, F["curr_language"] + 0.05, F["curr_social_emotional"] + 0.05,
                          F["curr_arts_play"] + 0.05])[0]
        warm = F["teacher_warmth"] > 0.5
        if kind == "math":
            line = r.choice([f"{a} plus {b} is {a + b}.", f"{a} times 3 is {a * 3}.", f"{a + b} take away {b} is {a}."])
            tail = r.choice(["Well done.", "Good, again.", "See how it works?"]) if warm else r.choice(["Again.", "Wrong ones lose marks.", "Pay attention."])
            return f"Teacher: {line} {tail}"
        if kind == "language":
            return r.choice([f"Teacher: A {r.choice(OBJECTS)} is a noun. To {r.choice(VERBS).split()[0]} is a verb.",
                             f"Story: Once there was a {r.choice(ADJ)} {r.choice(OBJECTS)} who lived near {r.choice(PLACES)}.",
                             f"Teacher: Read the next paragraph aloud, {self.name}."])
        if kind == "feelings":
            return f"Teacher: When you feel {r.choice(FEEL_WORDS)}, " + \
                ("take a breath and name the feeling." if warm else "keep it to yourself and get on with it.")
        return r.choice([f"Teacher: Let us draw a {r.choice(ADJ)} {r.choice(OBJECTS)}.",
                         f"Teacher: Everyone sing together, then outside to play.",
                         f"Teacher: Build the tallest tower you can with the blocks."])

    def _friend(self, p: Person, F: FactorSet) -> str:
        """A line from one of his friends, in that friend's character."""
        r = self.r
        f = p.circle.pick(p.age, r) if p.circle else None
        if f is None:
            return ""
        o, v = r.choice(OBJECTS), r.choice(VERBS)
        if f.risk > 0.55 and r.random() < 0.6:
            line = r.choice([f"Bet you cannot {v} the {o} from up there.", "Come on, nobody will find out.",
                             "Do not be boring, just try it."])
        elif f.studiousness > 0.6 and r.random() < 0.6:
            line = r.choice([f"Want to practise the sums together? I got {r.randint(2, 9)} times {r.randint(2, 9)} wrong.",
                             "Did you finish the reading? I will explain the hard bit.", "Study group at the library?"])
        elif f.kindness > 0.65 and r.random() < 0.6:
            line = r.choice([f"Are you okay, {self.name}? You looked {r.choice(['sad', 'tired', 'worried'])}.",
                             "I saved you a seat.", f"You can come to mine after {r.choice(PLACES)}."])
        else:
            line = f"Want to go to {r.choice(PLACES)} {r.choice(['later', 'this weekend', 'after school'])}?"
        return f"{f.name}{' (online)' if f.online else ''}: {line}"

    def _now(self, p: Person, F: FactorSet, scene: str):
        """The Now line for a lesson, so lessons and real decisions look the same. None without a present."""
        return self.present.moment(p, F, self.r, scene, keep=False).line() if self.present is not None else None

    def _worked_example(self, p: Person, F: FactorSet, pick_tier=None) -> str:
        """Someone shows him how an answer is given: a teacher solving a problem, or a caregiver or peer choosing in a
        situation. The format and the sums come from the world; whether a choice is good is left to his own experience,
        with only a tilt toward the better option when the parents are educated."""
        from .scenarios import ALL_SCENARIOS, problem, render_problem, render_scenario_ex, shuffled_order
        r = self.r
        if r.random() < F["curr_math"] / (F["curr_math"] + F["curr_social_emotional"] + 0.2):
            # Teachers work at his level, but keep earlier material in view so it is not forgotten.
            pr = problem(p, r, pick_tier() if pick_tier and r.random() < 0.6 else None)
            if pr:
                return render_problem(pr, p, self._now(p, F, problem_scene(p))) + f" {pr.answer}\n"
        pool = [sc for sc in ALL_SCENARIOS if p.stage in sc.stages]
        if not pool:
            return ""
        sc = r.choice(pool)
        order = shuffled_order(sc, r)
        text = render_scenario_ex(sc, p, F, r, self.mem, rehearse=False, now=self._now(p, F, sc.key), order=order)[0]
        if r.random() < 0.5 * F["parent_education"]:
            from .rlvr import score_scenario
            scores = [score_scenario(sc, p, F, i, r, draws=2) for i in range(len(sc.choices))]
            pick = max(range(len(scores)), key=scores.__getitem__)
        else:
            pick = r.randrange(len(sc.choices))
        return text + f" {'ABCD'[order.index(pick)]}\n"

    def month_parts(self, p: Person, F: FactorSet, events: List[str], budget_bytes: int, pick_tier=None):
        """(lessons, life): the month's text in two lists of lines. Lessons are worked examples; they are skills, so they
        are never faded. Life is everything else he lives and hears; it is what memory fades."""
        r, s, y = self.r, p.s, p.years
        life: List[str] = [f"({e})" for e in events]
        lessons: List[str] = []
        size = sum(len(l) + 1 for l in life)
        if y >= 2.5:                                  # worked examples: most of what school teaches
            if s["schooling"] > 0.5:
                share = 0.4 * (0.4 + 0.9 * school_effectiveness(F))     # a poor school teaches less of it
            else:
                share = 0.15 if y < 19 else 0.12
            target = size + int(budget_bytes * share)
            while size < target:
                ex = self._worked_example(p, F, pick_tier)
                if not ex:
                    break
                lessons.append(ex.rstrip("\n"))
                size += len(ex)
        if self.present is not None:                  # the moment he is in, as a Now line and in his own words
            for i in range(3 if y >= 3 else 1):
                m = self.present.moment(p, F, r, keep=(i == 0))
                add = [m.line()] + (m.narrate() if y >= 3 else [])
                life.extend(add)
                size += sum(len(x) + 1 for x in add)
        if self.mem is not None and y >= 3:           # memories that come to mind unasked, in the format he is asked in
            rate = (0.25 + 0.6 * F["rumination"]) * (0.3 if y < 6 else 1.0)
            for _ in range(2):
                if r.random() < rate:
                    for rec in self.mem.reminisce(s, MEMORY_BYTES):
                        life.append("Memory: " + rec.text)
                        size += len(rec.text) + 9
        if self.present is not None and y >= 3:      # someone asks him about himself; the true answer is said back
            from .selftalk import conversation
            cs = getattr(p, "conscious", None)
            if cs is not None and cs.thoughts:                      # his own inner voice, as he would put it
                life.append(cs.line())
                size += len(life[-1]) + 1
            for _ in range(1 if y < 6 else 6):
                add = conversation(p, F, self.present, self.mem, self.name, r)
                life.extend(add)
                size += sum(len(x) + 1 for x in add)
        while size < budget_bytes:
            u = r.random()
            if y < 12 and u < 0.7:
                line = self._caregiver(p, F)
            elif s["schooling"] > 0.5 and u < 0.7:
                line = self._school(p, F)
            elif y >= 3 and p.circle and p.circle.present(p.age) and r.random() < 0.35:
                line = self._friend(p, F)
            elif y >= 11 and r.random() < F["crisis_news"] * 0.5:
                line = "News: " + r.choice(HEADLINES) + "."
            elif y >= 19 and s["employed"] > 0.5 and r.random() < 0.5:
                line = "Work: " + r.choice(WORK)
            elif y >= 19 and r.random() < F["parasocial_companions"] * 0.4:
                line = f"Companion app: I am always here for you, {self.name}."
            elif y >= 5 and self.corpus and r.random() < (0.3 + 0.5 * F["parent_education"]) * (0.5 + F["curr_language"]):
                line = r.choice(self.corpus)[:600]
            else:
                line = self._caregiver(p, F) if y < 19 else \
                    f"Friend: {r.choice(['Want to', 'We should'])} go to {r.choice(PLACES)} {r.choice(['later', 'this weekend'])}?"
            life.append(line)
            size += len(line) + 1
        return lessons, life

    def month(self, p: Person, F: FactorSet, events: List[str], budget_bytes: int, pick_tier=None) -> str:
        """Text for one month, up to the byte budget the factors allow."""
        lessons, life = self.month_parts(p, F, events, budget_bytes, pick_tier)
        return "\n".join(lessons + life)

    def budget(self, p: Person, F: FactorSet, base: int) -> int:
        """Bytes of language this month. Phone-distracted caregivers mean fewer words reach him."""
        y, s = p.years, p.s
        if y < 12:
            amount = F["household_speech"] * (0.25 + 0.75 * s["caregiver_attention"])
        elif y < 23:
            amount = 0.6 + 0.3 * F["parent_education"] - 0.3 * s["peer_isolation"]
        else:
            amount = 0.4 + 0.3 * s["employed"] + 0.3 * s["community_support"] - 0.3 * s["social_isolation"]
        return int(base * max(0.05, amount))
