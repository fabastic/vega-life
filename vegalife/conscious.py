"""What he is aware of, who he thinks he is, and his conscience.

A working model of awareness, after Global Workspace Theory (Baars; Dehaene): many things compete for his attention
each month (how he feels, what just happened, who he misses, what he is worried about or wants, a memory that came
back, a twinge of conscience), and the few most salient win and are "broadcast": they become his thoughts. Those
thoughts are what he can report, so they are what he talks from.

  workspace    this month's 1-3 thoughts, chosen by salience from everything competing for attention
  self-model   slow-changing beliefs about himself ("I am shy", "I am good at maths", "I am a father"), built from
               what is true of him; children's self-concepts form from about 3 and settle in adolescence
  metacognition he knows how sure he is: a faded memory is said with "I think" / "I am not sure"
  conscience   a moral sense that grows with age and maturity, warm caregiving (internalised standards), and his
               agreeableness and conscientiousness (Kochanska: early conscience; Kohlberg: stages with age). It
               weighs his choices: hurting someone brings guilt, helping brings quiet pride, and it enters how
               he feels an outcome when he decides (rlvr), so his conscience shapes what he learns to choose.

Every month he hears his own thoughts as "Thought:" lines in his language, and the chat shows them to him when you
talk to him, so he answers from what is on his mind. Its own random generator: it never shifts his world.
"""
from __future__ import annotations

import random
import re
from typing import List, Optional, Tuple

# Choices that hurt or help someone else, by what they say. Crude but transparent: these are the choice texts in
# scenarios.py, read the way a person would read them.
HARM = re.compile(r"\b(hit|lie|lies|steal|cheat|copy|blame|yell|shout|mock|laugh at|call (?:him|her|them) names|"
                  r"ghost|cut (?:him|her|them) off|keep the money|push (?:him|her|them))\b", re.I)
HELP = re.compile(r"\b(help (?:him|her|them|out|someone|a friend|your)|comfort|apologi[sz]e|share (?:it|your|with)|"
                  r"tell the truth|listen|stand up for|visit|call (?:an old friend|a friend|your)|forgive|give back|"
                  r"look after|ask (?:them|gently)|talk it out)\b", re.I)


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Conscious:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 4111 + 23)
        self.thoughts: List[str] = []
        self.self_model: List[str] = []
        self.guilt = 0.0
        self.pride = 0.0
        self.last_deed: Optional[Tuple[str, float]] = None     # (what he did, +help / -harm)
        self.last_harm: Optional[str] = None
        self.last_help: Optional[str] = None

    # ------------------------------------------------------------------ conscience
    def moral_sense(self, p, F) -> float:
        """0..1: how much right and wrong weigh on him. Grows from ~2-3 years, firms up through adolescence."""
        s, y = p.s, p.years
        age = clip((y - 2) / 16)
        warmth = F["caregiver_warmth"] if F is not None else 0.5
        return clip(age * (0.25 + 0.3 * s["agreeableness"] + 0.2 * s["conscientiousness"] + 0.15 * warmth
                           + 0.1 * s["pfc_maturity"]) * 1.4)

    def judge(self, text: str) -> float:
        """+1 helps someone, -1 hurts someone, 0 neither."""
        if HARM.search(text):                       # hurting someone outweighs anything kind said alongside it
            return -1.0
        return 1.0 if HELP.search(text) else 0.0

    def weigh(self, p, F, choice_text: str) -> float:
        """What his conscience adds to how a choice feels before he makes it (in rlvr units, about -0.3..+0.15)."""
        m, v = self.moral_sense(p, F), self.judge(choice_text)
        return 0.3 * m * v if v < 0 else 0.15 * m * v

    def after(self, p, F, choice_text: str) -> None:
        """He has acted: guilt or quiet pride, by his conscience."""
        m, v = self.moral_sense(p, F), self.judge(choice_text)
        if v < 0:
            self.guilt = clip(self.guilt + 0.5 * m)
            p.apply({"anxiety": 0.02 * m}, fades=True)
        elif v > 0:
            self.pride = clip(self.pride + 0.3 * m)
        if v:
            self.last_deed = (choice_text, v)
            if v < 0:
                self.last_harm = choice_text
            else:
                self.last_help = choice_text

    # ------------------------------------------------------------------ who he thinks he is
    def build_self_model(self, p) -> List[str]:
        s, y = p.s, p.years
        if y < 3:
            return []
        me = []
        trait = [("shy", 0.35 - s["extraversion"]), ("outgoing", s["extraversion"] - 0.65),
                 ("a worrier", s["neuroticism"] - 0.6), ("calm", 0.35 - s["neuroticism"]),
                 ("curious", s["openness"] - 0.62), ("careful and organised", s["conscientiousness"] - 0.62),
                 ("kind", s["agreeableness"] - 0.62)]
        me += [f"I am {w}." for w, v in sorted(trait, key=lambda t: -t[1]) if v > 0][:2]
        if s["problem_solving"] > 0.5:
            me.append("I am good at working things out.")
        if s["academic"] > 0.7 and y < 25:
            me.append("I do well at school.")
        if s["peer_support"] > 0.5 or s["community_support"] > 0.65:
            me.append("People like having me around.")
        elif s["felt_loneliness"] > 0.55:
            me.append("I am often on my own.")
        fam = getattr(p, "family", None)
        if fam:
            if any(x.relation == "child" for x in fam.people):
                me.append("I am a father.")
            if any(x.relation == "partner" and x.present(p.age) for x in fam.people):
                me.append("I have someone I love.")
        w = getattr(p, "work", None)
        if w and s["employed"] > 0.5 and not w.retired:
            me.append("I work hard." if w.hours > 48 else "I have a job I go to.")
        elif w and w.retired:
            me.append("I am retired.")
        return me[:5]

    # ------------------------------------------------------------------ the month's thoughts
    def step(self, p, F, moment=None, mem=None) -> List[str]:
        """Everything competing for his attention; the most salient become this month's thoughts."""
        r, s, y = self.rng, p.s, p.years
        self.guilt *= 0.85
        self.pride *= 0.8
        if y < 2:
            self.thoughts = []
            return []
        cands: List[Tuple[float, str]] = []
        if moment is not None and moment.feelings:
            f = moment.feelings[0].replace("very ", "")
            cands.append((0.4 + (0.3 if moment.feelings[0].startswith("very") else 0), f"I feel {f}."))
        if moment is not None and moment.mind and not moment.mind.startswith("missing"):
            mind = moment.mind[0].lower() + moment.mind[1:]
            cands.append((0.55, f"I keep thinking about {mind}."))
        fam = getattr(p, "family", None)
        if fam:
            who = fam.on_mind(p.age)
            if who:
                cands.append((0.4 + s.get("grief", 0.0), f"I miss {who}."))
            if fam.expecting:
                cands.append((0.7, "We are having a baby. I cannot stop thinking about it."))
        w = getattr(p, "work", None)
        if w and w.searching:
            cands.append((0.45 + min(0.3, w.searching / 20), "I need to find work."))
        if w and w.burnout > 0.5:
            cands.append((0.5, "I am so tired of work."))
        if s.get("cortisol", 0) > 0.5:
            cands.append((0.5, "Everything feels like too much right now."))
        if s.get("joy", 0) > 0.7:
            cands.append((0.45, "Life feels good right now."))
        harm, help_ = getattr(self, "last_harm", None), getattr(self, "last_help", None)
        if self.guilt > 0.15 and harm:
            cands.append((0.4 + self.guilt, f"I should not have chosen to {harm}."))
        elif self.pride > 0.15 and help_:
            cands.append((0.3 + self.pride, f"I am glad I chose to {help_}."))
        # school, his mental health, his phone, his relationships, and what people assume about him
        for part, sal, call in (("mind", 0.6, lambda o: o.line()), ("bonds", 0.5, lambda o: o.line(p.age)),
                                ("school", 0.45, lambda o: o.line()), ("prejudice", 0.45, lambda o: o.line()),
                                ("online", 0.35, lambda o: o.line()),
                                ("seasons", 0.4, lambda o: o.line(p, F)), ("illness", 0.5, lambda o: o.line()),
                                ("hormones", 0.35, lambda o: o.line()), ("hardships", 0.5, lambda o: o.line())):
            o = getattr(p, part, None)
            t = call(o) if o is not None else ""
            if t:
                cands.append((sal, t))
        if mem is not None and mem.episodes and r.random() < 0.5:
            ep = max(mem.episodes, key=lambda e: e.strength * e.salience * r.random())
            sure = "" if ep.detail >= 0.75 else "I think " if ep.detail >= 0.4 else "I am not sure, but "
            cands.append((0.3 + 0.4 * ep.salience, f"{sure}{mem.render(ep)}"))
        if y >= 6 and s["goal_horizon"] > 0.6:
            cands.append((0.25, "I want to do something good with my life."))
        cands.sort(key=lambda t: -t[0] * (0.85 + 0.3 * r.random()))
        k = 1 if y < 6 else 2 if y < 13 else 3
        self.thoughts = [t for _, t in cands[:k]]
        if p.age % 6 == 0 or not self.self_model:
            self.self_model = self.build_self_model(p)
        return self.thoughts

    def line(self) -> str:
        return "Thought: " + " ".join(self.thoughts) if self.thoughts else ""

    def to_json(self) -> dict:
        return {"thoughts": self.thoughts, "self_model": self.self_model, "guilt": round(self.guilt, 3),
                "pride": round(self.pride, 3), "last_deed": self.last_deed[0] if self.last_deed else None}
