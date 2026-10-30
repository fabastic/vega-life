"""Vega's body, mind, relationships and money, advanced one month at a time from birth.

Everything that happens to him comes from the factors (factors.py) and from what he chooses in the scenarios
(scenarios.py). Each block in `step_month` is labelled with the factor it implements. Values are in [0, 1]
unless noted.

Three state variables are not simulated but measured on the model itself (trainer.py writes them):
  language          from his loss on held-out speech
  problem_solving   from his success rate on verifiable problems
  cognition         from his loss after neurodegeneration damage
"""
from __future__ import annotations

import copy
import math
import random
from typing import Dict, List, Optional, Tuple

from .factors import FactorSet, school_effectiveness, stage_of
from .family import Family
from .chemistry import HORMONES, Chemistry
from .career import Career
from .conscious import Conscious
from .schooling import Schooling
from .mental import MentalHealth
from .digital import Online
from .bonds import Bonds
from .prejudice import Prejudice
from .seasons import Seasons
from .illness import Illness, mortality_norm
from .hormones import Hormones
from .hardships import Hardships

GROUPS = {
    "body": ["health", "inflammation", "microbiome", "autoimmune_risk", "methylation_risk", "telomere", "cardio",
             "motor", "puberty", "pfc_maturity", "allostatic_load", "insulin_resistance", "fertility",
             "neurodegeneration", "testosterone", "adiposity", "bone_density"],
    "mind": ["attachment", "anxiety", "language", "problem_solving", "resilience", "nihilism", "goal_horizon",
             "identity_rigidity", "loneliness", "felt_loneliness", "autonomy", "identity_crisis",
             "financial_paranoia", "digital_literacy", "ai_literacy", "cognition", "school_belonging", "grief"],
    "social": ["caregiver_attention", "caregiver_anxiety", "elder_template", "household_friction", "peer_isolation",
               "community_support", "social_isolation", "peer_support", "peer_risk", "peer_study"],
    "economy": ["academic", "employed", "skill_value", "income", "wealth", "housing", "pension", "children",
                "schooling", "credential"],
    "chemistry": list(HORMONES),
    "personality": ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
                    "sleep", "mood", "mood_baseline"],
}

GENES = 8


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def toward(cur: float, target: float, rate: float) -> float:
    return cur + rate * (target - cur)


class Person:
    def __init__(self, F: FactorSet, seed: int, circle=None, family: Optional[list] = None):
        self.rng = random.Random(seed * 104729 + 3)
        self.circle = circle                     # people.Circle: his friends
        self.n_siblings = round(3 * F["siblings"])
        self.tertiary_until = 0                  # month his studies after school end; 0 = not studying
        self.tertiary_degree = 0.0
        self.age = 0          # months
        self.alive = True
        self.cause_of_death = ""
        r = self.rng
        self.genes_loaded = [r.random() < F["genetic_risk"] for _ in range(GENES)]
        self.metabolic = r.lognormvariate(0.0, 0.45)   # inborn metabolic susceptibility: spreads who gets diabetes
        self.hazard = 0.0                              # this month's chance of dying (for calibration and the UI)
        self.genes_on = [False] * GENES
        s: Dict[str, float] = {k: 0.0 for g in GROUPS.values() for k in g}
        # Born, not spawned: everything starts at its newborn value.
        s.update(health=0.9, telomere=1.0, microbiome=0.75, cardio=0.6, motor=0.05, pfc_maturity=0.05,
                 attachment=0.3, anxiety=0.3, goal_horizon=0.5, digital_literacy=0.0, cognition=1.0,
                 community_support=0.5, housing=0.0, wealth=clip(0.5 * F["ses"]), fertility=0.0)
        # Microplastic placental transfer: inflammatory baseline at birth.
        s["inflammation"] = clip(0.1 + 0.55 * F["microplastics_placental"] + r.gauss(0, 0.04))
        for t in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            s[t] = F[f"trait_{t}"]                 # temperament at birth: the innate seed (character.py shapes it)
        s.update(sleep=0.8, mood=0.5, mood_baseline=0.5)
        self.s = s
        self.events: List[str] = []
        self.pending: List[dict] = []              # memorable events this month, drained by the trainer
        self.happenings: List[dict] = []           # everything that happened this month, for his brain map
        self.due: List[tuple] = []                 # (month, deltas, text, valence): consequences still to come
        self.transient: Dict[str, float] = {}      # what is left of recent choices' passing effects
        self.history: List[Tuple[int, str]] = []
        self.family = Family(F, seed, family, self.n_siblings)   # the people he is born among, and losing them
        self.chem = Chemistry(seed)                              # hormones and the good moments behind them
        self.work = Career(seed)                                 # job hunting, hours, promotions, burnout, retiring
        self.conscious = Conscious(seed)                         # his thoughts, his self-model, his conscience
        self._new_parts(F, seed)
        for k, v in self.chem.level.items():
            self.s[k] = v
        self.s["joy"] = 0.5

    def upgrade(self, F: FactorSet, seed: int) -> None:
        """A life saved by older code (a checkpoint from before family, chemistry and work existed) carries on with
        them: his family is seeded as it would have been, everyone who is still alive is still alive, and the new
        states start from their resting values."""
        for g in GROUPS.values():
            for k in g:
                self.s.setdefault(k, 0.0)
        if not hasattr(self, "family"):
            self.family = Family(F, seed, None, self.n_siblings)
            self.family.backfill(self.age)
        if not hasattr(self, "chem"):
            self.chem = Chemistry(seed)
            for k, v in self.chem.level.items():
                self.s[k] = v
            self.s["joy"] = 0.5
        if not hasattr(self, "work"):
            self.work = Career(seed)
            self.work.was_employed = self.s["employed"] > 0.5
        if not hasattr(self, "conscious"):
            self.conscious = Conscious(seed)
        self._new_parts(F, seed)

    PARTS = ("school", "mind", "online", "bonds", "prejudice", "seasons", "illness", "hormones", "hardships")

    def _new_parts(self, F: FactorSet, seed: int) -> None:
        """School as it runs where he lives, his mental health, his phone, how each relationship goes, and the
        prejudice he meets and carries. Added to older lives too, from where they are."""
        if not hasattr(self, "school"):
            self.school = Schooling(F, seed)
            if self.age >= 19 * 12:
                self.school.stage = "done"
        if not hasattr(self, "mind"):
            self.mind = MentalHealth(F, seed, self.school.region)
        if not hasattr(self, "online"):
            self.online = Online(F, seed)
        if not hasattr(self, "bonds"):
            self.bonds = Bonds(seed)
        if not hasattr(self, "prejudice"):
            self.prejudice = Prejudice(F, seed, self.school.region)
        if not hasattr(self, "seasons"):
            self.seasons = Seasons(seed)                 # the joys, sorrows, yearnings and regrets of each age
        if not hasattr(self, "illness"):
            self.illness = Illness(seed)                 # diseases of each age, and living with them
        if not hasattr(self, "hormones"):
            self.hormones = Hormones(F, seed, self.school.region)   # puberty, cycles, menopause, ageing
            if not self.s.get("bone_density"):
                self.s["bone_density"] = 0.3 + 0.35 * min(1.0, self.age / 360)
        if not hasattr(self, "hardships"):
            self.hardships = Hardships(F, seed, self.school.region)   # substances, crime, accidents, war, faith

    @property
    def years(self) -> float:
        return self.age / 12.0

    @property
    def stage(self) -> str:
        return stage_of(self.age)

    def note(self, text: str, valence: float = -0.1, arousal: float = 0.3, who=None, memorable: bool = True,
             key: str = "", cause: Optional[str] = None, deltas: Optional[Dict[str, float]] = None) -> None:
        """Something happens to him. `valence` (-1 bad .. 1 good) and `arousal` (0 calm .. 1 intense) say how it felt;
        memorable events are taken into his autobiographical memory (memory.py). Everything, memorable or not, goes
        to `happenings` for his brain map; `cause` is the brain-map id of what led to it, when known."""
        h = {"text": text, "valence": valence, "arousal": arousal, "who": list(who or []),
             "key": key or text.split(" ")[0], "cause": cause, "deltas": dict(deltas or {}), "memorable": memorable}
        self.events.append(text)
        self.history.append((self.age, text))
        self.happenings.append(h)
        if memorable:
            self.pending.append(h)

    def clone(self) -> "Person":
        """A copy that can live one month differently without touching him (same randomness from here on)."""
        c = copy.copy(self)
        c.s = dict(self.s)
        c.rng = random.Random()
        c.rng.setstate(self.rng.getstate())
        c.circle = copy.deepcopy(self.circle) if self.circle else None
        c.family = copy.deepcopy(self.family)
        c.chem = copy.deepcopy(self.chem)
        c.work = copy.deepcopy(self.work)
        c.conscious = copy.deepcopy(self.conscious)
        for k in self.PARTS:
            setattr(c, k, copy.deepcopy(getattr(self, k)))
        c.genes_on = list(self.genes_on)
        c.due = list(self.due)
        c.transient = dict(self.transient)
        c.events, c.pending, c.history, c.happenings = [], [], [], []
        return c

    # ------------------------------------------------------------------ the month
    def schedule(self, delay: int, deltas: Dict[str, float], text: str, valence: float,
                 cause: Optional[str] = None) -> None:
        """A consequence that arrives later: the cost of partying shows up at exam time, not at the party."""
        # self.age is already the next month to be lived, so a delay of 1 arrives in that month.
        self.due.append((self.age + max(1, delay) - 1, dict(deltas), text, valence, cause))

    def step_month(self, F: FactorSet) -> List[str]:
        self.events = []
        s, r, y = self.s, self.rng, self.years
        stg = self.stage

        self._fade()                               # yesterday's ups and downs wear off

        # --- consequences of earlier choices arriving now ------------------------------------------------
        arrived = [d for d in self.due if d[0] <= self.age]
        self.due = [d for d in self.due if d[0] > self.age]
        for _, deltas, text, valence, cause in arrived:
            self.apply(deltas)
            self.note(text, valence, 0.3 + 0.5 * abs(valence), key="consequence", cause=cause, deltas=deltas)

        # --- friends: who is around this month and what they are like -----------------------------------
        if self.circle:
            for text, val, aro, who in self.circle.step(self.age, F):
                self.note(text, val, aro, who, key="friend")
            s["peer_support"] = self.circle.support(self.age)
            s["peer_risk"] = self.circle.risk(self.age)
            s["peer_study"] = self.circle.study(self.age)
        sup, prisk, pstudy = s["peer_support"], s["peer_risk"], s["peer_study"]

        # --- caregivers (infancy and childhood) ------------------------------------------------------
        if y < 12:
            # Caregiver phone distraction fragments eye-contact windows; siblings and screens share the rest.
            s["caregiver_attention"] = clip(F["caregiver_warmth"] * (1 - 0.7 * F["caregiver_phubbing"])
                                            * (1 - 0.08 * self.n_siblings) * (1 - 0.2 * F["screen_time"]))
            # Emotional mirroring follows the attention he actually gets.
            s["attachment"] = toward(s["attachment"], s["caregiver_attention"], 0.06 if y < 3 else 0.02)
            # Smart nursery: constant biometric alerts, anxious caregivers, anxiety passed on.
            s["caregiver_anxiety"] = clip(0.15 + 0.6 * F["smart_nursery"] * (1 if y < 3 else 0.4)
                                          + 0.3 * F["household_stress"])
            s["anxiety"] = toward(s["anxiety"], 0.5 * s["caregiver_anxiety"] + 0.4 * (1 - s["attachment"]), 0.04)
        else:
            s["caregiver_attention"] = toward(s["caregiver_attention"], 0.0, 0.02)
            # From adolescence his anxiety is his own: driven by stress load, temperament, support and conflict at
            # home, not frozen at whatever childhood left.
            own = 0.12 + 0.35 * s["allostatic_load"] + 0.3 * s["neuroticism"] + 0.15 * (1 - s["community_support"]) \
                + 0.1 * s["household_friction"]
            s["anxiety"] = toward(s["anxiety"], clip(own), 0.03)

        # --- early antibiotics: microbiome, and immune-related risk -----------------------------------
        # Evidence: asthma and allergy risk rise (asthma OR about 2, eczema 1.26, food allergy 1.33-1.42), more with
        # repeated courses; links to most autoimmune diseases were minimal in a 2025 study of 1.09M children. So
        # each course adds a modest, lasting immune risk rather than a large autoimmune one.
        if y < 3 and r.random() < 0.06 * F["early_antibiotics"]:
            s["microbiome"] = clip(s["microbiome"] - 0.15)
            s["autoimmune_risk"] = clip(s["autoimmune_risk"] + 0.04 * (1 - s["microbiome"]))
            s["inflammation"] = clip(s["inflammation"] + 0.03)
            self.note("a course of antibiotics; gut diversity drops", -0.2, 0.3, key="illness")
        elif y < 3:
            s["microbiome"] = toward(s["microbiome"], 0.8, 0.01)

        # --- pollution and extreme weather: epigenetic methylation, mostly early ----------------------
        plasticity = 1.0 if y < 3 else 0.4 if y < 12 else 0.1
        for g in range(GENES):
            if self.genes_loaded[g] and not self.genes_on[g]:
                if r.random() < 0.004 * plasticity * (F["local_pollution"] + 0.6 * F["extreme_weather"]):
                    self.genes_on[g] = True
                    self.note(f"risk gene {g + 1} switched on by methylation", memorable=False, key="gene")
        s["methylation_risk"] = sum(self.genes_on) / GENES
        if r.random() < 0.02 * F["extreme_weather"]:
            kind = r.choice(["a heat wave", "a flood", "a storm", "wildfire smoke"])
            s["allostatic_load"] = clip(s["allostatic_load"] + 0.02)
            s["anxiety"] = clip(s["anxiety"] + 0.05)
            self.note(f"{kind} hits the neighbourhood", -0.5, 0.7, key="disaster")

        # --- childhood body: walkability ---------------------------------------------------------------
        if 3 <= y < 19:
            active = 1 - 0.75 * F["low_walkability"] - 0.2 * F["screen_time"] + 0.15 * F["extracurriculars"]
            s["cardio"] = toward(s["cardio"], 0.35 + 0.6 * active, 0.02)
            s["motor"] = toward(s["motor"], 0.3 + 0.7 * active, 0.025)
        elif y < 3:
            s["motor"] = toward(s["motor"], 0.35, 0.05)

        # --- grandparents as caregivers: older behavioural template ------------------------------------
        if 3 <= y < 12:
            s["elder_template"] = toward(s["elder_template"], F["grandparent_caregivers"], 0.03)

        # --- chronic stress, housing instability, structural violence: allostatic load, telomeres ------
        chronic = (0.5 * F["household_stress"] + 0.3 * F["housing_instability"] + 0.45 * F["structural_violence"]
                   + 0.25 * (1 - F["neighbourhood_safety"]))
        if y >= 19:
            chronic = (0.25 * chronic + 0.3 * (1 - s["employed"]) * (1 - s["wealth"]) + 0.2 * s["identity_crisis"]
                       + 0.25 * (1 - F["workplace_security"]) * s["employed"])
        buffer = 0.5 * s["attachment"] + 0.5 * s["community_support"]
        if y >= 22:
            buffer = 0.4 * s["attachment"] + 0.4 * s["community_support"] + 0.2 * F["partner_support"]
        s["allostatic_load"] = clip(s["allostatic_load"] + 0.004 * chronic
                                    - 0.006 * (0.3 + buffer) * s["allostatic_load"])
        s["telomere"] = clip(s["telomere"] - 0.00025 * (1 + 1.5 * chronic + 1.0 * s["allostatic_load"]))
        if y < 19 and r.random() < 0.015 * F["housing_instability"]:
            s["community_support"] = clip(s["community_support"] - 0.2)
            s["anxiety"] = clip(s["anxiety"] + 0.05)
            self.note("the family is forced to move; friends are left behind", -0.6, 0.7, key="move")
        if y >= 3:
            # Everyday support: friends, community ties, and (as an adult) a partner.
            partner = 0.2 * F["partner_support"] if y >= 22 else 0.0
            target = (0.1 + 0.25 * F["community_ties"] + 0.45 * sup + partner) * (1 - 0.5 * s["peer_isolation"])
            s["community_support"] = toward(s["community_support"], min(1.0, target), 0.01 if y < 19 else 0.006)

        # --- adolescence: endocrine disruptors, puberty vs prefrontal cortex ---------------------------
        onset = 11.8 + 0.8 * F["sex"] - 2.2 * F["endocrine_disruptors"]   # boys later; disruptors earlier
        if y >= onset:
            s["puberty"] = clip(s["puberty"] + 1 / 36)
        s["pfc_maturity"] = clip(0.05 + 0.95 * (y / 25.0) ** 1.3 * (1 - 0.25 * s["allostatic_load"]))

        # --- crisis news: nihilism and goal horizon ----------------------------------------------------
        if y >= 11:
            exposure = F["crisis_news"] * (1.0 if y < 25 else 0.5)
            s["nihilism"] = clip(s["nihilism"] + 0.006 * exposure - 0.002 * (s["community_support"] + s["attachment"]))
            s["goal_horizon"] = toward(s["goal_horizon"], 0.9 - 0.75 * s["nihilism"], 0.02)

        # --- echo chambers: identity rigidity, household friction, peer niches -------------------------
        if 12 <= y < 30:
            s["identity_rigidity"] = clip(s["identity_rigidity"] + 0.006 * F["echo_chambers"] - 0.001
                                          - 0.002 * F["friend_diversity"])
            s["household_friction"] = toward(s["household_friction"],
                                             s["identity_rigidity"] * (0.5 + 0.6 * F["cultural_strictness"]), 0.03)
            s["peer_isolation"] = toward(s["peer_isolation"], 0.7 * F["echo_chambers"] * s["identity_rigidity"], 0.02)

        # --- AI tool access: AI literacy and the advanced track -----------------------------------------
        if 12 <= y < 23:
            s["ai_literacy"] = toward(s["ai_literacy"], F["ai_tool_access"] * (0.5 + 0.5 * F["school_ai_policy"]), 0.02)

        # --- school and study: quality, warmth, crowding, rigour, homework, tracking, bullying, clubs, curriculum ---
        for h in self.school.step(self, F):                 # where he lives sets how school runs (schooling.py)
            self.note(h["text"], h["valence"], h["arousal"], who=h["who"], key=h["key"], deltas=h["deltas"])
        if self.age == 228:
            # what he wants to study, and whether his results, his family's money and the people around him let him
            got = self.school.decide(self, F)
            if got:
                self.tertiary_degree = got
                self.tertiary_until = self.age + (48 if got == 1.0 else 24)
                what = self.school.course if got == 1.0 else self.school.course or "vocational training"
                self.note(f"starts {what}" + ("" if self.school.course == self.school.wanted or got < 1 else
                          f", though he wanted {self.school.wanted}"), 0.4, 0.6, key="study")
            elif self.school.why and self.school.why != ["he chose to work"]:
                self.note("does not go on to study: " + self.school.why[-1], -0.4, 0.5, key="study")
        studying = 3 <= y < 19 or self.age < self.tertiary_until
        s["schooling"] = 1.0 if studying else 0.0
        if studying:
            q = school_effectiveness(F) * (0.7 if y < 6 else 1.0)
            belong = 0.15 + 0.5 * F["teacher_warmth"] + 0.3 * sup + 0.1 * F["curr_arts_play"] - 0.45 * F["bullying"] * (1 - sup)
            s["school_belonging"] = toward(s["school_belonging"], clip(belong), 0.03)
            target = (0.12 + 0.4 * q + 0.12 * s["problem_solving"] + 0.12 * pstudy + 0.08 * F["tutoring_access"]
                      + 0.06 * F["curriculum_rigor"] * q + 0.06 * F["homework_load"] + 0.05 * s["school_belonging"]
                      - 0.1 * s["allostatic_load"])
            if F["tracking"] > 0.3:      # streaming: strong students pulled ahead, weak ones held back
                target += 0.12 * (F["tracking"] - 0.3) * (1 if s["academic"] > 0.5 else -1)
            s["academic"] = toward(s["academic"], clip(target), 0.02)
            s["allostatic_load"] = clip(s["allostatic_load"] + 0.0015 * F["homework_load"] * (0.4 + F["curriculum_rigor"])
                                        + 0.002 * F["bullying"] - 0.0006 * s["school_belonging"])
            s["resilience"] = clip(s["resilience"] + 0.0006 * F["extracurriculars"] + 0.0008 * F["curr_social_emotional"])
            s["anxiety"] = clip(s["anxiety"] - 0.0015 * F["curr_social_emotional"]
                                + 0.0015 * F["homework_load"] * F["curriculum_rigor"])
            s["motor"] = clip(s["motor"] + 0.0006 * (F["extracurriculars"] + F["curr_arts_play"]))
            if 6 <= y < 19 and r.random() < 0.03 * F["bullying"] * (1 - 0.5 * sup):
                s["anxiety"] = clip(s["anxiety"] + 0.05)
                s["peer_isolation"] = clip(s["peer_isolation"] + 0.03)
                s["school_belonging"] = clip(s["school_belonging"] - 0.05)
                self.note("is bullied at school", -0.7, 0.7, key="bullied")
        if self.tertiary_until and self.age == self.tertiary_until and not self.school.dropped_out:
            s["credential"] = self.tertiary_degree
            self.note("finishes his studies", 0.6, 0.6, key="study")
        # Studying is paid for: a degree costs more than vocational training, and the debt takes years to clear.
        if self.age < self.tertiary_until and self.tertiary_degree == 1.0:
            s["wealth"] = clip(s["wealth"] - 0.004 * F["student_debt"])
        elif self.tertiary_degree and 23 <= y < 35:
            s["wealth"] = clip(s["wealth"] - 0.0012 * F["student_debt"] * self.tertiary_degree)
        if y >= 6:
            target = 0.85 if y < 60 else 0.85 - 0.8 * s["neurodegeneration"]
            s["digital_literacy"] = toward(s["digital_literacy"], target * (0.5 + 0.5 * F["parent_education"]), 0.01)

        # --- early adulthood ----------------------------------------------------------------------------
        if 19 <= y < 45:
            base = 1.0 if y < 30 else max(0.0, 1 - (y - 30) / 15)
            s["fertility"] = clip(base * (1 - 0.35 * F["fertility_disruptors"] - 0.25 * s["allostatic_load"]
                                          - 0.2 * s["insulin_resistance"]))
        elif y >= 45:
            s["fertility"] = toward(s["fertility"], 0.0, 0.05)
        if y >= 19:
            # Parasocial ties hide loneliness: he feels less lonely than he is, and local support erodes.
            s["community_support"] = clip(s["community_support"] - 0.003 * F["parasocial_companions"])
            s["loneliness"] = toward(s["loneliness"], 0.8 * (1 - s["community_support"]) * (1 - 0.3 * s["children"])
                                     * (1 - 0.08 * self.n_siblings), 0.03)
            s["felt_loneliness"] = clip(s["loneliness"] * (1 - 0.65 * F["parasocial_companions"]))
            # Unaffordable housing keeps him at his parents'.
            if s["housing"] < 0.5 and r.random() < 0.01 * (1 - F["housing_unaffordable"]) * (0.3 + s["income"]):
                s["housing"] = 1.0
                self.note("moves into a place of his own", 0.6, 0.6, key="home")
            s["autonomy"] = toward(s["autonomy"], clip(0.5 * s["housing"] + 0.3 * s["employed"] + 0.2 * s["wealth"]
                                                       - 0.1 * F["cultural_strictness"]), 0.02)
        if y >= 19 and s["employed"] > 0.5:
            # AI doing entry-level work removes the apprentice phase.
            learn = 0.012 * (1 - 0.7 * F["ai_entry_automation"]) if y < 36 else 0.003
            s["skill_value"] = clip(s["skill_value"] + learn)
            s["income"] = toward(s["income"], 0.3 + 0.7 * s["skill_value"], 0.05)
        elif y >= 19:
            s["income"] = toward(s["income"], 0.05, 0.1)

        # --- middle adulthood ---------------------------------------------------------------------------
        if y >= 25:
            # Insulin resistance builds with age, inborn susceptibility and chronic stress; night shifts add a modest
            # amount (pooled OR about 1.09 for type 2 diabetes, up to 1.44 for usual night work).
            nights = F["shift_work"] * s["employed"]
            s["insulin_resistance"] = clip(s["insulin_resistance"]
                                           + 0.00045 * self.metabolic * (1 + 0.22 * nights + 0.8 * s["allostatic_load"]))
            s["allostatic_load"] = clip(s["allostatic_load"] + 0.0015 * nights)
        if 36 <= y < 70:
            s["skill_value"] = clip(s["skill_value"] - 0.004 * F["skill_obsolescence"])
            s["identity_crisis"] = toward(s["identity_crisis"], F["skill_obsolescence"] * (1 - s["skill_value"]), 0.02)
        if 40 <= y < 65:
            drain = 0.003 * F["boomerang_children"] * s["children"] + 0.003 * F["parent_care_costs"]
            s["wealth"] = clip(s["wealth"] - drain)

        # --- money -------------------------------------------------------------------------------------
        if 18 <= y < 66:
            # Background labour market: some work turns up without a scenario; jobs are also lost.
            if s["employed"] < 0.5 and r.random() < 0.01 * (0.3 + s["academic"] + 0.4 * s["credential"]) \
                    * (1 - 0.5 * F["algorithmic_hiring"]) and s["schooling"] < 0.5:
                s["employed"] = 1.0
                self.note("finds work", 0.5, 0.5, key="work")
            elif s["employed"] > 0.5 and r.random() < 0.004 * (1 + F["skill_obsolescence"] * (y > 36)) \
                    * (1.6 - 1.2 * F["workplace_security"]):
                s["employed"] = 0.0
                self.note("loses his job", -0.7, 0.7, key="work")
        if y >= 19:
            spend = 0.004 + 0.003 * (1 - s["housing"] * 0.5)
            s["wealth"] = clip(s["wealth"] + 0.006 * s["income"] * s["employed"] - spend * 0.5)
            if y >= 66:
                s["employed"] = 0.0 if r.random() < 0.05 else s["employed"]
                s["pension"] = toward(s["pension"], 0.5 * s["wealth"] + 0.3, 0.05)
                # Pension tied to volatile markets; inflation outruns it.
                s["pension"] = clip(s["pension"] - 0.004 * F["pension_volatility"] * r.random())
                s["wealth"] = clip(s["wealth"] + 0.003 * s["pension"] - 0.004)

        # --- late adulthood: epigenetic wear sets the speed of neurodegeneration -------------------------
        if y >= 56:
            wear = 0.45 * (1 - s["telomere"]) + 0.3 * s["methylation_risk"] + 0.25 * s["allostatic_load"]
            s["neurodegeneration"] = clip(s["neurodegeneration"] + 0.0003 * (1 + 4 * wear) * (1 + (y - 56) / 15))
            # Loss of third spaces and transport: isolation.
            no_car = clip((y - 70) / 15) * 0.7 + 0.3 * s["neurodegeneration"]
            s["social_isolation"] = toward(s["social_isolation"],
                                           F["third_space_erosion"] * (0.4 + 0.6 * no_car) * (1 - 0.4 * s["children"])
                                           * (1 - 0.4 * F["community_ties"]), 0.02)
            # Digital-only services lock out the digitally illiterate.
            missed = F["digital_only_services"] * (1 - s["digital_literacy"])
            s["inflammation"] = clip(s["inflammation"] + 0.0015 * missed)
            s["financial_paranoia"] = toward(s["financial_paranoia"], 0.6 * F["ai_scams"] * (0.3 + s["neurodegeneration"]), 0.01)
        else:
            s["social_isolation"] = toward(s["social_isolation"], 0.5 * s["peer_isolation"] + 0.3 * s["loneliness"], 0.02)

        # --- ageing and health --------------------------------------------------------------------------
        s["inflammation"] = clip(s["inflammation"] + 0.0003 * (y > 40) + 0.001 * s["autoimmune_risk"] * r.random()
                                 - 0.0006 * s["microbiome"])
        if y > 30:
            s["cardio"] = clip(s["cardio"] - 0.0003 * (1 + F["low_walkability"]))
        s["health"] = clip(1.0
                           - 0.18 * s["inflammation"] - 0.12 * s["autoimmune_risk"] - 0.2 * s["allostatic_load"]
                           - 0.18 * s["insulin_resistance"] - 0.25 * s["neurodegeneration"]
                           - 0.15 * (1 - s["cardio"]) - 0.12 * s["methylation_risk"] * (y / 80)
                           - 0.14 * s["social_isolation"] * (y > 56) - 0.06 * s["loneliness"] * (y > 30)
                           - 0.25 * (1 - s["telomere"]) - 0.25 * self.illness.burden()
                           - 0.08 * (1 - F["healthcare_access"]) * (s["inflammation"] + s["allostatic_load"]))
        # --- the people around him: ageing, dying, leaving; and the grief that follows (family.py) -------
        for h in (self.family.step(self, F) + self.work.step(self, F) + self.bonds.step(self, F)
                  + self.mind.step(self, F) + self.online.step(self, F) + self.prejudice.step(self, F)
                  + self.seasons.step(self, F) + self.illness.step(self, F) + self.hormones.step(self, F)
                  + self.hardships.step(self, F)):
            self.note(h["text"], h["valence"], h["arousal"], who=h["who"], key=h["key"], deltas=h["deltas"])
        bright = self.chem.step(self, F, self.family, self.work)    # the month's chemistry, and its best moment
        if bright:
            self.note(bright["text"], bright["valence"], bright["arousal"], who=bright["who"], key="joy",
                      deltas=bright["deltas"])

        # Mortality: a Gompertz hazard (risk of death doubles about every 8 years of adult age), scaled by health and
        # access to care, and by two exposures with well-measured direct effects:
        #   unemployment in working age: all-cause mortality HR about 1.63 (Roelfs et al. 2011)
        #   air pollution: about 1 year of life per 10 ug/m3 PM2.5 (AQLI); 0 here is clean air, 1 is about 35 ug/m3,
        #   a hazard x1.26 that costs about 3 years over a life
        hazard = 3.4e-6 * math.exp(0.085 * y) * (1.6 - s["health"]) ** 3 * (1.3 - 0.6 * F["healthcare_access"])
        if 25 <= y < 65 and s["employed"] < 0.5 and s["schooling"] < 0.5:
            hazard *= 1.55         # direct part; stress and poverty add the rest, toward the unadjusted figure
        hazard *= 1 + 0.26 * F["local_pollution"]
        hazard *= self.family.extra_hazard        # widowhood, and the heart in the month of a close death
        hazard *= self.work.hazard()              # long hours (Kivimäki 2015)
        hazard *= self.mind.hazard()              # depression ~1.5x, alcohol ~1.8x, psychosis ~2x, untreated ADHD
        # Named diseases: the life table already holds them, so they shift risk onto the sick rather than adding it.
        hazard *= self.illness.hazard() / mortality_norm(y)
        hazard *= 1 + 0.6 * max(0.0, s["cortisol"] - 0.45)   # chronic stress physiology (flattened cortisol rhythm)
        if y < 1:
            hazard += 0.0004 * (1 - s["health"])
        self.hazard = hazard
        if self.illness.fatal or self.hardships.fatal or r.random() < hazard or s["health"] <= 0.02:
            self.alive = False
            named = self.hardships.fatal or self.illness.cause()
            self.cause_of_death = named if named else "his body gave out" if s["health"] < 0.3 else "natural causes"
            self.note(f"dies at {y:.1f} ({self.cause_of_death})", memorable=False)
        self.age += 1
        return self.events

    # ------------------------------------------------------------------ outcomes
    # How fast the effect of a single choice on a fast-moving state fades (share of what remains, per month). How a
    # day went passes, while circumstances set the long-run trend. Money, jobs, housing, children, grades, skills and
    # health risks are not listed: those consequences last.
    FADE = {"anxiety": 0.25, "attachment": 0.15, "community_support": 0.15, "peer_isolation": 0.2,
            "household_friction": 0.2, "nihilism": 0.15, "goal_horizon": 0.15, "identity_rigidity": 0.1,
            "financial_paranoia": 0.15, "social_isolation": 0.2, "loneliness": 0.2, "school_belonging": 0.2,
            "allostatic_load": 0.1, "motor": 0.1, "cardio": 0.1, "resilience": 0.05}

    def apply(self, deltas: Dict[str, float], fades: bool = False) -> None:
        """Changes his state. fades=True for a lived choice: its effect on fast-moving states wears off over months."""
        for k, d in deltas.items():
            before = self.s[k]
            self.s[k] = clip(before + d)
            if fades and k in self.FADE:
                self.transient[k] = self.transient.get(k, 0.0) + (self.s[k] - before)

    def _fade(self) -> None:
        for k, v in list(self.transient.items()):
            back = self.FADE[k] * v
            self.s[k] = clip(self.s[k] - back)
            self.transient[k] = v - back
            if abs(self.transient[k]) < 1e-4:
                del self.transient[k]

    def wellbeing(self, s: Dict[str, float] = None) -> float:
        """The verifiable outcome score that scenario rewards are computed from. Weights shift with the stage."""
        s = s or self.s
        health = s["health"]
        calm = 1 - s["anxiety"] - 0.5 * s["allostatic_load"] - 0.25 * s.get("grief", 0.0) + 0.3 * (s.get("joy", 0.5) - 0.5)
        connection = (s["attachment"] + s["community_support"] + (1 - s["loneliness"]) + (1 - s["social_isolation"])) / 4
        growth = (s["problem_solving"] + s["resilience"] + s["academic"] + s["skill_value"] + s["motor"]) / 5
        security = (s["wealth"] + s["housing"] + s["employed"] + s["pension"]) / 4 - 0.3 * s["financial_paranoia"]
        agency = s["autonomy"] * (1 - s["identity_crisis"]) + s["goal_horizon"] * (1 - s["nihilism"]) - 0.5 * s["household_friction"]
        w = {
            "infancy": (0.35, 0.3, 0.3, 0.05, 0.0, 0.0),
            "childhood": (0.25, 0.2, 0.25, 0.25, 0.0, 0.05),
            "adolescence": (0.2, 0.15, 0.2, 0.25, 0.05, 0.15),
            "early_adult": (0.15, 0.15, 0.2, 0.2, 0.15, 0.15),
            "middle_adult": (0.2, 0.15, 0.2, 0.1, 0.2, 0.15),
            "late_adult": (0.3, 0.15, 0.25, 0.05, 0.2, 0.05),
        }[stage_of(self.age)]
        return sum(a * b for a, b in zip(w, (health, calm, connection, growth, security, agency)))

    def snapshot(self) -> dict:
        return {g: {k: round(self.s[k], 3) for k in ks} for g, ks in GROUPS.items()} | {
            "genes": {"loaded": self.genes_loaded, "on": self.genes_on}}
