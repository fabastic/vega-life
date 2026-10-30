"""The present moment: where he is, who is with him, what he is doing, how his body and feelings are, and what is on
his mind, right now.

Memory (memory.py) is the past as he can still recall it. This is the other half: the moment he is in. Every
decision he makes and much of what he hears comes with one "Now (age):" line, in the same format everywhere, so he
learns that what is happening now matters, not only what happened before. Example:

    Now (9y4m): Tuesday evening, at home with Grandma, doing homework. I feel tired and a bit worried.
    On my mind: Maya moved away.

The moment is built from his simulated state, the factors, his friends and family, the calendar, and what happened
to him in the last few months. When a situation implies a place (the night-shift offer happens at work), the moment
is set there.
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .factors import FactorSet
from .world import Person

NOW_BYTES = 130            # a Now line never takes more than this of a prompt (context is 512 bytes)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

# Where a situation happens, so the moment and the situation agree. (place, activity, part of day or "")
SCENE: Dict[str, tuple] = {
    "hungry": ("in his cot", "waking up", "night"), "face": ("in someone's arms", "being held", ""),
    "monitor_alarm": ("in his cot", "asleep", "night"), "toy_out_of_reach": ("on the floor", "playing", "morning"),
    "tablet_freezes": ("at home", "playing on the tablet", "afternoon"),
    "getting_to_school": ("at home", "getting ready for school", "morning"),
    "ball_taken": ("at the playground", "playing", "afternoon"), "parents_argue": ("at home", "in his room", "evening"),
    "party": ("at home", "on his phone", "evening"), "doom_feed": ("in bed", "scrolling", "night"),
    "dinner_politics": ("at home", "eating dinner", "evening"), "essay_due": ("at his desk", "studying", "evening"),
    "apply_job": ("at home", "on the laptop", "afternoon"), "move_out": ("at his parents' house", "doing the sums", "evening"),
    "lonely_evening": ("at home", "alone", "evening"), "junior_work": ("at work", "at his desk", "morning"),
    "children": ("at home", "talking with his partner", "evening"), "night_shift": ("at work", "on a break", "afternoon"),
    "automated_away": ("at work", "in a meeting", "morning"), "sandwich": ("at home", "on the phone", "evening"),
    "stuck": ("at home", "reading a job offer", "evening"), "scam_call": ("at home", "answering the phone", "afternoon"),
    "center_closed": ("at home", "looking out of the window", "morning"),
    "pension_hit": ("at home", "reading the bank letter", "morning"),
    "app_only_clinic": ("at home", "trying to book the clinic", "morning"),
    "bullied": ("at school", "at break", "morning"), "friend_dare": ("out with friends", "hanging around", "afternoon"),
    "friend_low": ("with a friend", "walking home", "afternoon"), "study_group": ("at school", "between classes", "afternoon"),
    "exam_stress": ("at his desk", "revising", "night"),
    # problems: where a sum is put to him
    "lesson": ("at school", "in maths class", "morning"), "play_count": ("at home", "playing with blocks", "afternoon"),
    "sums": ("at home", "doing the sums", "evening"),
}


IRREGULAR = {"is": ("am", "being"), "has": ("have", "having"), "does": ("do", "doing"), "goes": ("go", "going"),
             "sits": ("sit", "sitting"), "swims": ("swim", "swimming"), "ships": ("ship", "shipping"),
             "gets": ("get", "getting"), "runs": ("run", "running"), "dies": ("die", "dying"),
             "lies": ("lie", "lying"), "plans": ("plan", "planning"), "stops": ("stop", "stopping")}
PLACEHOLDERS = {"{carer}": "my mum", "{friend}": "a friend", "{pet}": "my pet", "{partner}": "my partner",
                "{child}": "my child"}


def base_verb(w: str) -> str:
    """'watches' -> 'watch', 'tries' -> 'try', 'laughs' -> 'laugh' (third person to first)."""
    if w in IRREGULAR:
        return IRREGULAR[w][0]
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "sses", "xes", "zes")):
        return w[:-2]
    return w[:-1] if w.endswith("s") and not w.endswith("ss") else w


def gerund(w: str) -> str:
    if w in IRREGULAR:
        return IRREGULAR[w][1]
    b = base_verb(w)
    if b.endswith("ie"):
        return b[:-2] + "ying"
    if b.endswith("e") and not b.endswith(("ee", "ye", "oe")):
        return b[:-1] + "ing"
    return b + "ing"


def as_his_own(text: str, form: str = "base") -> str:
    """The world's note about him ('goes for a long run', 'is held close by {carer}') as he would say it:
    form='base' -> 'go for a long run', form='gerund' -> 'going for a long run'. his -> my, him -> me."""
    for k, v in PLACEHOLDERS.items():
        text = text.replace(k, v)
    words = text.split(" ")
    if words and words[0].islower() and words[0].endswith("s"):
        words[0] = base_verb(words[0]) if form == "base" else gerund(words[0])
    out = " ".join(words)
    for a, b in ((" his ", " my "), (" himself", " myself"), (" him", " me"), (" he has ", " I have "), (" he is ", " I am "), (" he ", " I ")):
        out = out.replace(a, b)
    return out


def living_carer(p, kin: dict, carer: str) -> str:
    """The carer, or, if that person has died or left, one who is still there."""
    fam = getattr(p, "family", None)
    if fam is None:
        return carer
    rel = {kin["mother"]: "mother", kin["father"]: "father", kin["grandma"]: "grandparent"}
    if fam.alive(rel.get(carer, "mother")):
        return carer
    for k, r_ in (("mother", "mother"), ("father", "father"), ("grandma", "grandparent")):
        if fam.alive(r_):
            return kin[k]
    return "his aunt"


def problem_scene(p: Person) -> str:
    if p.s["schooling"] > 0.5:
        return "lesson"
    return "play_count" if p.years < 6 else "sums"


def _clip(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


@dataclass
class Moment:
    age: int
    when: str
    place: str
    doing: str
    with_: List[str]
    body: str
    feelings: List[str]
    mind: str

    def line(self, max_bytes: int = NOW_BYTES) -> str:
        """The canonical one-line form. Drops the least important parts until it fits."""
        y, m = divmod(self.age, 12)
        who = f" with {self._join(self.with_)}" if self.with_ else ""
        feel = self._join(self.feelings) if self.feelings else "okay"
        body = f"{self.body}, " if self.body else ""
        parts = [
            lambda: f"Now ({y}y{m}m): {self.when}, {self.place}{who}, {self.doing}. I feel {body}{feel}. On my mind: {self.mind}.",
            lambda: f"Now ({y}y{m}m): {self.when}, {self.place}{who}, {self.doing}. I feel {body}{feel}.",
            lambda: f"Now ({y}y{m}m): {self.when}, {self.place}, {self.doing}. I feel {feel}.",
            lambda: f"Now ({y}y{m}m): {self.place}. I feel {feel}.",
        ]
        for build in parts if self.mind else parts[1:]:
            text = build()
            if len(text.encode()) <= max_bytes:
                return text
        return parts[-1]()[:max_bytes]

    def narrate(self) -> List[str]:
        """The same moment as he would think it, in plain first-person sentences (for what he hears himself think)."""
        out = [f"I am {self.place}{' with ' + self._join(self.with_) if self.with_ else ''}, {self.doing}."]
        if self.feelings:
            out.append(f"I feel {self._join(self.feelings)}.")
        if self.body:
            out.append(f"My body feels {self.body}.")
        if self.mind:
            out.append(f"I keep thinking about {self.mind[0].lower() + self.mind[1:]}.")
        return out

    def to_json(self) -> dict:
        return {"line": self.line(), "when": self.when, "place": self.place, "doing": self.doing, "with": self.with_,
                "body": self.body, "feelings": self.feelings, "mind": self.mind}

    @staticmethod
    def _join(xs: List[str]) -> str:
        return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


class Present:
    def __init__(self, F: FactorSet, seed: int, kin: Optional[Dict[str, str]] = None):
        self.rng = random.Random(seed * 2741 + 13)
        self.birth_month = self.rng.randrange(12)
        self.kin = kin or {"mother": "Mum", "father": "Dad", "grandma": "Grandma"}
        self.recent: deque = deque(maxlen=12)     # (month, text, valence): what happened lately, his working memory
        self.last: Optional[Moment] = None

    def happened(self, age: int, text: str, valence: float) -> None:
        self.recent.append((age, text, valence))

    # ------------------------------------------------------------------ the parts of a moment
    def _when(self, age: int, part: str, r: random.Random, F: FactorSet) -> str:
        month = MONTHS[(self.birth_month + age) % 12]
        part = part or r.choice(["morning", "afternoon", "evening", "night"])
        weather = ""
        u = r.random()
        if u < 0.25 * F["extreme_weather"]:
            weather = r.choice(["a stifling", "a stormy", "a smoky"]) + " "
        elif u < 0.45:
            weather = r.choice(["a rainy", "a grey", "a sunny", "a cold", "a warm"]) + " "
        return f"{weather}{r.choice(DAYS)} {part} in {month}"

    def _scene(self, p: Person, F: FactorSet, r: random.Random) -> tuple:
        """Where he is and what he is doing, when no situation dictates it."""
        y, s = p.years, p.s
        if y < 3:
            return r.choice([("in his cot", "looking at the ceiling"), (f"in {self.kin['mother']}'s arms", "being fed"),
                             ("on the floor", "crawling" if y > 0.6 else "kicking"), ("in the bath", "splashing")])
        if s["schooling"] > 0.5 and y < 19 and r.random() < 0.45:
            return r.choice([("at school", "in maths class"), ("at school", "at break"), ("at school", "in reading class")])
        if s["schooling"] > 0.5 and y >= 19 and r.random() < 0.45:
            return ("at university" if s["credential"] < 1 else "at college", "in a lecture")
        if 19 <= y < 66 and s["employed"] > 0.5 and r.random() < 0.5:
            if F["shift_work"] > 0.5 and r.random() < 0.4:
                return ("at work", "on the night shift")
            return ("at work", r.choice(["at his desk", "in a meeting", "on a break"]))
        if y < 12:
            opts = [("at home", "eating dinner"), ("at home", "watching a screen" if F["screen_time"] > 0.4 else "drawing")]
            if F["low_walkability"] < 0.5:
                opts.append(("outside", "playing in the street"))
            if F["homework_load"] > 0.4 and y >= 6:
                opts.append(("at home", "doing homework"))
            return r.choice(opts)
        if y < 19:
            opts = [("in his room", "on his phone"), ("at home", "eating dinner")]
            if F["extracurriculars"] > 0.4:
                opts.append(("at practice", "training"))
            if p.circle and p.circle.present(p.age):
                opts.append(("out with friends", "hanging around"))
            return r.choice(opts)
        if y < 66:
            opts = [("at home", "making dinner"), ("at home", "on his phone")]
            if s["employed"] < 0.5:
                opts.append(("at home", "looking for work"))
            if s["children"] > 0.5:
                opts.append(("at home", "putting the kids to bed"))
            if s["community_support"] > 0.4:
                opts.append(("at a friend's place", "talking"))
            return r.choice(opts)
        opts = [("at home", "sitting by the window"), ("at home", "watching the news")]
        if F["third_space_erosion"] < 0.5 and s["social_isolation"] < 0.5:
            opts.append(("at the community centre", "playing cards"))
        if s["health"] < 0.5:
            opts.append(("at the clinic", "waiting to be seen"))
        if s["children"] > 0.5:
            opts.append(("at home", "on a call with his children"))
        return r.choice(opts)

    def _company(self, p: Person, F: FactorSet, place: str, r: random.Random) -> List[str]:
        y, s = p.years, p.s
        friends = p.circle.present(p.age) if p.circle else []
        if place in ("in his cot", "in bed", "in his room", "at his desk") or "alone" in place:
            return []
        if y < 12 and place.startswith("at home") or place.startswith("in ") and y < 3:
            carer = self.kin["grandma"] if F["grandparent_caregivers"] > 0.5 else r.choice([self.kin["mother"], self.kin["father"]])
            carer = living_carer(p, self.kin, carer)
            return [carer] if r.random() < 0.3 + 0.7 * s["caregiver_attention"] else []
        if place.startswith(("at school", "out with friends", "with a friend", "at practice", "outside", "at the playground")):
            close = sorted(friends, key=lambda f: -f.closeness)[:2]
            return [f.name for f in close if r.random() < 0.5 + 0.5 * f.closeness]
        if y >= 22 and place.startswith("at home"):
            who = []
            if F["partner_support"] > 0.4 and r.random() < 0.6:
                who.append("his partner")
            if s["children"] > 0.5 and y < 60 and r.random() < 0.5:
                who.append("his kids")
            return who
        return []

    def _body(self, p: Person, r: random.Random) -> str:
        s = p.s
        if p.years < 3 and r.random() < 0.3:
            return "hungry"
        if s["health"] < 0.35:
            return "unwell"
        if s["neurodegeneration"] > 0.35:
            return "foggy"
        if s["allostatic_load"] > 0.55:
            return "worn out"
        if s.get("sleep", 1.0) < 0.45:
            return "short of sleep"
        return ""

    def _feelings(self, p: Person) -> List[str]:
        s = p.s
        # Happiness is felt relative to what he has got used to (character.py adapts the baseline).
        w = s.get("mood", p.wellbeing())
        cand = [
            ("scared", s["anxiety"] - 0.2), ("lonely", s["felt_loneliness"] - 0.1), ("hopeless", s["nihilism"] - 0.1),
            ("lost", s["identity_crisis"]), ("suspicious", s["financial_paranoia"]), ("tired", s["allostatic_load"]),
            ("restless", max(0.0, s["puberty"] - s["pfc_maturity"]) * 1.5),
            ("calm", (1 - s["anxiety"]) * (1 - s["allostatic_load"]) - 0.25 + 0.4 * (s.get("serotonin", 0.45) - 0.45)),
            ("loved", 0.5 * (s["attachment"] + s["community_support"]) - 0.1 + 0.8 * (s.get("oxytocin", 0.3) - 0.3)),
            ("happy", w - 0.25 + 0.6 * (s.get("joy", 0.5) - 0.45)), ("low", 0.45 - w),
            ("proud", 0.5 * (s["academic"] + s["skill_value"]) - 0.2 + 0.6 * (s.get("dopamine", 0.35) - 0.35)),
            ("excited", 1.6 * (s.get("dopamine", 0.35) - 0.38)), ("full of energy", 1.6 * (s.get("endorphins", 0.25) - 0.3)),
            ("stressed", 1.5 * (s.get("cortisol", 0.3) - 0.42)), ("on edge", 2.0 * (s.get("adrenaline", 0.1) - 0.3)),
            ("grieving", 1.4 * s.get("grief", 0.0)),
        ]
        top = sorted(cand, key=lambda kv: -kv[1])
        out = []
        for name, v in top:
            if v > 0.25 and len(out) < 2:
                out.append(("very " if v > 0.7 else "a bit " if v < 0.4 else "") + name)
        return out or ["okay"]

    def _mind(self, p: Person, F: FactorSet, r: random.Random) -> str:
        """What is on his mind: the most striking thing that happened lately, or an ongoing worry."""
        recent = [(a, t, v) for a, t, v in self.recent if p.age - a <= 3]
        if recent:
            a, t, v = max(recent, key=lambda e: abs(e[2]) - 0.1 * (p.age - e[0]))
            if abs(v) > 0.25:
                return self._past_tense(t)
        s, y = p.s, p.years
        fam = getattr(p, "family", None)
        who = fam.on_mind(p.age) if fam else None
        if who and r.random() < 0.3 + s.get("grief", 0.0):
            return f"missing {who}"
        worries = []
        if 19 <= y < 66 and s["employed"] < 0.5 and s["schooling"] < 0.5:
            worries.append("finding work")
        if 12 <= y < 19 and F["homework_load"] * F["curriculum_rigor"] > 0.25:
            worries.append("the exams")
        if y >= 19 and s["wealth"] < 0.1:
            worries.append("money")
        if s["health"] < 0.45:
            worries.append("my health")
        if s["felt_loneliness"] > 0.5:
            worries.append("having nobody to talk to")
        if s["household_friction"] > 0.5:
            worries.append("the fights at home")
        return r.choice(worries) if worries else ""

    @staticmethod
    def _past_tense(text: str) -> str:
        """Turns the world's present-tense event notes into what he thinks: 'is bullied at school' -> 'being bullied
        at school', 'Maya moves away' -> 'Maya moving away'."""
        t = text.split(";")[0].strip()
        swaps = [("is bullied", "being bullied"), ("moves away", "moving away"), ("drifts away", "drifting away"),
                 ("goes to a different school", "going to a different school"), ("meets ", "meeting "),
                 ("finds work", "finding work"), ("loses his job", "losing my job"), ("starts ", "starting "),
                 ("finishes his studies", "finishing my studies"), ("moves into a place of his own", "my own place"),
                 ("the family is forced to move", "having to move"), ("hits the neighbourhood", "that hit us")]
        for a, b in swaps:
            if a in t:
                t = t.replace(a, b)
                break
        else:
            t = as_his_own(t, "gerund")             # 'goes for a long run' -> 'going for a long run'
        return t[0].upper() + t[1:] if t else t

    # ------------------------------------------------------------------ the moment
    def moment(self, p: Person, F: FactorSet, r: Optional[random.Random] = None, scene: Optional[str] = None,
               keep: bool = True) -> Moment:
        """The moment he is in now. `scene` is a situation key; if it implies a place, the moment is set there.
        keep=False builds a moment without making it the one shown as 'right now' (used for lessons)."""
        r = r or self.rng
        hint = SCENE.get(scene or "")
        if hint and (p.years >= 3 or hint[0].startswith(("in his cot", "in someone", "on the floor"))):
            place, doing, part = hint
        else:
            (place, doing), part = self._scene(p, F, r), ""
        m = Moment(p.age, self._when(p.age, part, r, F), place, doing, self._company(p, F, place, r), self._body(p, r),
                   self._feelings(p), self._mind(p, F, r))
        if keep:
            self.last = m
        return m
