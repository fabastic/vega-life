"""Every factor around Vega, from before birth to old age.

A factor is an exposure in [0, 1]: 0 means absent, 1 means as strong as it gets. Each one is either seeded from
the run's seed (and the family background it is born into) or fixed by the user. The user can also schedule a
factor to change at a given age, or change it live while the run is going.

The dynamics that turn these exposures into changes in body, mind, relationships and money live in world.py.
`effect` here is the plain description of what that code does, shown in the UI next to each factor.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

STAGES = ["infancy", "childhood", "adolescence", "early_adult", "middle_adult", "late_adult"]
STAGE_LABEL = {
    "infancy": "Infancy (0-2)", "childhood": "Early-middle childhood (3-11)", "adolescence": "Adolescence (12-18)",
    "early_adult": "Early adulthood (19-35)", "middle_adult": "Middle adulthood (36-55)",
    "late_adult": "Late adulthood (56+)", "family": "Family he is born into",
    "school": "School and education", "friends": "Friends and peers",
    "surroundings": "Home, neighbourhood and wider world",
    "temperament": "His own make-up (memory and feeling)",
}
DOMAINS = ["biological", "mental", "social", "socioeconomic", "technological", "background"]


def stage_of(age_months: int) -> str:
    if age_months < 36:
        return "infancy"
    if age_months < 144:
        return "childhood"
    if age_months < 228:
        return "adolescence"
    if age_months < 432:
        return "early_adult"
    if age_months < 672:
        return "middle_adult"
    return "late_adult"


@dataclass(frozen=True)
class Factor:
    key: str
    stage: str          # the stage where it acts most (it may keep acting later)
    domain: str
    label: str
    effect: str
    mean: float = 0.4
    sd: float = 0.2
    ses: float = 0.0    # how much a poorer family pushes it up (+) or down (-)


# The family background is sampled first; most exposures are correlated with it.
FAMILY: List[Factor] = [
    Factor("ses", "family", "background", "Family socioeconomic status",
           "Wealth and stability of the household. Shifts the odds of almost every other exposure.", 0.5, 0.22),
    Factor("parent_education", "family", "background", "Parents' education",
           "How rich and varied the language he hears is, and how much reading there is at home.", 0.5, 0.22),
    Factor("caregiver_warmth", "family", "background", "Caregiver warmth",
           "How responsive the people raising him are when they are paying attention.", 0.65, 0.18),
    Factor("household_speech", "family", "background", "Talk at home",
           "How many words a day are spoken around and to him. This is literally his training data.", 0.55, 0.2),
    Factor("sex", "family", "background", "Sex (0 female, 1 male)",
           "Shifts puberty timing and fertility curves.", 0.5, 0.5),
    Factor("genetic_risk", "family", "background", "Inherited risk",
           "How many of his 8 risk genes are loaded. Epigenetic exposures decide whether they switch on.", 0.4, 0.2),
]

EXPOSURES: List[Factor] = [
    # Infancy
    Factor("microplastics_placental", "infancy", "biological", "Microplastic placental transfer",
           "Raises baseline inflammatory markers at birth.", 0.4, 0.2, 0.2),
    Factor("early_antibiotics", "infancy", "biological", "Early antibiotic exposure",
           "Each course cuts gut microbiome diversity and adds a modest lasting immune risk (asthma and allergy are"
           " well supported; most autoimmune links are weak).", 0.35, 0.2, 0.1),
    Factor("caregiver_phubbing", "infancy", "mental", "Caregiver phone distraction",
           "Fragments eye-contact windows: fewer words heard, slower emotional mirroring and language.", 0.45, 0.2, 0.1),
    Factor("local_pollution", "infancy", "socioeconomic", "Local pollution (zip code)",
           "Drives DNA methylation that switches his risk genes on, mostly in early life.", 0.4, 0.2, 0.35),
    Factor("extreme_weather", "infancy", "socioeconomic", "Extreme weather events",
           "Heat waves, floods and storms: acute stress and further methylation.", 0.3, 0.2, 0.15),
    Factor("smart_nursery", "infancy", "technological", "Smart nursery surveillance",
           "Constant biometric alerts make the caregivers anxious; that anxiety is passed on.", 0.35, 0.25, -0.15),
    # Childhood
    Factor("low_walkability", "childhood", "biological", "Non-walkable neighbourhood",
           "Sedentary daily life lowers the cardiovascular baseline and gross motor resilience.", 0.45, 0.25, 0.15),
    Factor("frictionless_tech", "childhood", "mental", "Frictionless technology",
           "Removes everyday challenges: fewer problems are thrown at him, so he trains on fewer of them.", 0.5, 0.2, -0.05),
    Factor("grandparent_caregivers", "childhood", "social", "Grandparents as primary caregivers",
           "Older behavioural models shape how he relates to peers.", 0.3, 0.3, 0.1),
    Factor("household_stress", "childhood", "socioeconomic", "Chronic household stress",
           "Raises allostatic load and shortens telomeres.", 0.4, 0.2, 0.3),
    Factor("housing_instability", "childhood", "socioeconomic", "Housing instability",
           "Forced moves reset friendships and add stress.", 0.3, 0.22, 0.35),
    Factor("structural_violence", "childhood", "socioeconomic", "Exposure to structural violence",
           "Violence in the neighbourhood: strongest single driver of cellular ageing here.", 0.25, 0.2, 0.35),
    # Adolescence
    Factor("endocrine_disruptors", "adolescence", "biological", "Endocrine disruptors (diet, plastics)",
           "Brings puberty earlier, widening the gap with prefrontal maturity, which drives risk-taking.", 0.4, 0.2, 0.2),
    Factor("crisis_news", "adolescence", "mental", "Unfiltered crisis news",
           "Climate and economic doom in his feed: nihilism up, planning horizon down. The headlines are also text he reads.",
           0.45, 0.22, 0.0),
    Factor("echo_chambers", "adolescence", "social", "Algorithmic echo chambers",
           "Hardens identity early: household friction and isolation in narrow peer niches.", 0.4, 0.22, 0.05),
    Factor("ai_tool_access", "adolescence", "socioeconomic", "Access to paid AI tools",
           "Gates AI literacy and the advanced school track.", 0.5, 0.25, -0.35),
    # Early adulthood
    Factor("fertility_disruptors", "early_adult", "biological", "Fertility disruptors",
           "Chronic stress, microplastics and metabolic syndrome lower fertility; delaying children raises later risks.",
           0.4, 0.2, 0.15),
    Factor("parasocial_companions", "early_adult", "mental", "Parasocial ties and AI companions",
           "Masks loneliness: he feels less lonely than he is while local support erodes.", 0.45, 0.22, 0.0),
    Factor("housing_unaffordable", "early_adult", "social", "Unaffordable housing",
           "Forces him to keep living with his parents, delaying adult autonomy.", 0.5, 0.22, 0.3),
    Factor("algorithmic_hiring", "early_adult", "socioeconomic", "Algorithmic hiring filters",
           "Automated resume filters gatekeep jobs and cap class mobility.", 0.55, 0.2, 0.0),
    Factor("ai_entry_automation", "early_adult", "technological", "AI doing entry-level work",
           "Removes the apprentice phase: fewer work problems to learn from.", 0.5, 0.22, 0.0),
    # Middle adulthood
    Factor("shift_work", "middle_adult", "biological", "Shift work and broken sleep",
           "Raises insulin resistance and allostatic load.", 0.3, 0.25, 0.25),
    Factor("skill_obsolescence", "middle_adult", "mental", "Rapid skill obsolescence",
           "Automation devalues his expertise, triggering a mid-career identity crisis.", 0.45, 0.22, 0.05),
    Factor("boomerang_children", "middle_adult", "social", "Boomerang children",
           "Adult children move back in, draining money.", 0.3, 0.22, 0.15),
    Factor("parent_care_costs", "middle_adult", "social", "Costs of caring for ageing parents",
           "Long-term medical care for his parents competes for the same money.", 0.4, 0.22, 0.15),
    Factor("geographic_entrapment", "middle_adult", "socioeconomic", "Geographic entrapment",
           "An underwater mortgage or caregiving keeps him from moving for better work.", 0.35, 0.22, 0.25),
    # Late adulthood
    Factor("ai_scams", "late_adult", "mental", "AI-generated scams and targeted fraud",
           "Exploits cognitive decline: fraud losses and constant financial paranoia.", 0.45, 0.2, 0.0),
    Factor("third_space_erosion", "late_adult", "social", "Loss of third spaces and transport",
           "Closing community spaces and losing the car accelerate lethal isolation.", 0.45, 0.22, 0.2),
    Factor("pension_volatility", "late_adult", "socioeconomic", "Market-tied pension and inflation",
           "Inflation outruns fixed income and can force him back to work in decline.", 0.45, 0.22, 0.2),
    Factor("digital_only_services", "late_adult", "technological", "Digital-only healthcare, banking, government",
           "Without digital literacy he loses access to care and money.", 0.55, 0.2, 0.0),
]

SCHOOL: List[Factor] = [
    Factor("school_quality", "school", "education", "School quality",
           "Teaching, resources and results. Sets how much of what is taught he can learn, and how rich his lessons are.",
           0.5, 0.22, -0.3),
    Factor("teacher_warmth", "school", "education", "Teacher warmth",
           "Warm teachers raise his sense of belonging at school and lower stress; harsh ones do the opposite.", 0.55, 0.2, -0.1),
    Factor("class_crowding", "school", "education", "Class crowding",
           "Large classes cut the attention each child gets, which lowers the effective quality of lessons.", 0.45, 0.22, 0.25),
    Factor("curriculum_rigor", "school", "education", "Curriculum rigour",
           "How demanding the material is. Raises learning when quality is high; raises stress when it is not.", 0.5, 0.2, 0.0),
    Factor("homework_load", "school", "education", "Homework load",
           "More practice raises academic results a little and adds chronic stress and exam pressure.", 0.4, 0.22, 0.0),
    Factor("tracking", "school", "education", "Ability tracking",
           "Streaming by ability: strong students are pushed ahead and weak ones are held back, widening the gap.",
           0.4, 0.25, 0.0),
    Factor("bullying", "school", "education", "Bullying at school",
           "Chance of being bullied: anxiety, isolation and lost belonging.", 0.3, 0.2, 0.1),
    Factor("extracurriculars", "school", "education", "Clubs, sport and arts",
           "Raises motor skills, resilience and the number of friends he makes.", 0.4, 0.22, -0.3),
    Factor("tutoring_access", "school", "education", "Tutoring and extra help",
           "Paid or family help with schoolwork; raises academic results.", 0.3, 0.22, -0.4),
    Factor("school_ai_policy", "school", "education", "AI policy at school",
           "How openly AI tools are used. Raises AI literacy but means fewer problems he must solve unaided.",
           0.5, 0.25, 0.0),
    Factor("higher_ed_path", "school", "education", "Path after school (0 none, 0.5 vocational, 1 university)",
           "Decides whether he studies until 21 or 23. A degree raises job odds; study costs money.", 0.5, 0.3, -0.3),
    Factor("student_debt", "school", "education", "Student debt",
           "How much of the cost of study is borrowed; it drains his wealth for years.", 0.4, 0.22, 0.1),
    Factor("curr_math", "school", "education", "Curriculum: maths and problem solving",
           "Share of lessons on numbers. Raises how many problems he is set and how many worked examples he sees.",
           0.5, 0.2, 0.0),
    Factor("curr_language", "school", "education", "Curriculum: reading and language",
           "Share of lessons on stories, grammar and reading. Raises how much he reads.", 0.5, 0.2, 0.0),
    Factor("curr_social_emotional", "school", "education", "Curriculum: feelings and relationships",
           "Lessons that name and handle feelings. Raises resilience and lowers anxiety.", 0.4, 0.2, 0.0),
    Factor("curr_arts_play", "school", "education", "Curriculum: arts and play",
           "Time for play, music and drawing; raises motor skills and attachment to school.", 0.4, 0.2, 0.0),
]

FRIENDS: List[Factor] = [
    Factor("friend_count", "friends", "social", "Number of friends",
           "Seeds how many friends he makes over his life (0 to about 8). Ignored if you list friends yourself.",
           0.5, 0.2, 0.0),
    Factor("friend_closeness", "friends", "social", "Closeness of friendships",
           "How close his friends are. Close friends give far more support and influence him more.", 0.5, 0.2, 0.0),
    Factor("peer_risk_culture", "friends", "social", "Risk-taking among friends",
           "Friends who dare and drink make risky choices more likely and the cost of refusing higher.", 0.35, 0.2, 0.1),
    Factor("peer_academic_culture", "friends", "social", "Studiousness among friends",
           "Studious friends raise his academic results; the opposite pulls them down.", 0.5, 0.2, -0.15),
    Factor("friend_diversity", "friends", "social", "Diversity of friends",
           "Friends with different backgrounds and views slow the hardening of his identity.", 0.4, 0.22, 0.0),
    Factor("online_friend_share", "friends", "social", "Share of friends who are online-only",
           "Online friends give less support than the same friends in person.", 0.4, 0.22, 0.0),
]

SURROUNDINGS: List[Factor] = [
    Factor("siblings", "surroundings", "social", "Siblings (0 none, 1 three)",
           "Siblings share caregiver attention but lower loneliness.", 0.4, 0.3, 0.1),
    Factor("neighbourhood_safety", "surroundings", "socioeconomic", "Neighbourhood safety",
           "Unsafe streets add chronic stress for children and teenagers.", 0.6, 0.2, -0.2),
    Factor("screen_time", "surroundings", "technological", "Screen time",
           "More screens mean less activity and less caregiver attention.", 0.5, 0.22, 0.1),
    Factor("cultural_strictness", "surroundings", "social", "Cultural and religious strictness",
           "Stricter households cut risky choices and friend variety, but raise friction and slow his independence.",
           0.4, 0.25, 0.0),
    Factor("healthcare_access", "surroundings", "socioeconomic", "Healthcare access",
           "Lowers illness, slows physical decline and lowers the death rate.", 0.6, 0.2, -0.3),
    Factor("workplace_security", "surroundings", "socioeconomic", "Job security",
           "Insecure work means more job losses and more chronic stress.", 0.5, 0.2, -0.2),
    Factor("partner_support", "surroundings", "social", "Partner support",
           "A supportive partner buffers stress and loneliness in adulthood.", 0.5, 0.25, 0.0),
    Factor("community_ties", "surroundings", "social", "Community ties (clubs, faith, neighbours)",
           "Raises everyday support and protects against isolation in old age.", 0.5, 0.22, 0.0),
]

TEMPERAMENT: List[Factor] = [
    Factor("memory_strength", "temperament", "mental", "Memory strength",
           "How long his memories of what happened last. Low: events fade within a few years. High: he keeps them for decades.",
           0.5, 0.18, 0.0),
    Factor("rumination", "temperament", "mental", "Rumination",
           "How often unpleasant memories come back unasked, and how easily recalling them rewrites them.", 0.35, 0.2, 0.0),
    Factor("emotional_intensity", "temperament", "mental", "Emotional intensity",
           "How strongly feelings mark what he lives through. Intense feelings make memories vivid and long-lasting.",
           0.5, 0.2, 0.0),
    # Innate seeds of the Big Five. Each sets about half of the trait (twin heritability is roughly 40-60%);
    # the other half is formed by what he lives through, and all traits drift toward maturity with age.
    Factor("trait_openness", "temperament", "mental", "Innate openness",
           "Curiosity and taste for the new. Raises his pull toward choices he has not tried.", 0.5, 0.18, 0.0),
    Factor("trait_conscientiousness", "temperament", "mental", "Innate conscientiousness",
           "Self-control and planning. Makes later consequences count for more when he chooses.", 0.5, 0.18, 0.0),
    Factor("trait_extraversion", "temperament", "mental", "Innate extraversion",
           "Pull toward people. Shapes how much friends and company build him up.", 0.5, 0.18, 0.0),
    Factor("trait_agreeableness", "temperament", "mental", "Innate agreeableness",
           "Warmth and cooperation with others.", 0.5, 0.18, 0.0),
    Factor("trait_neuroticism", "temperament", "mental", "Innate neuroticism",
           "Emotional reactivity. Losses hurt more, stress builds faster, and bad memories return more often.",
           0.5, 0.18, 0.0),
]

# Added later, and sampled after everything above so older seeds keep every value they had.
WORLD: List[Factor] = [
    Factor("region", "family", "background", "Where in the world he grows up",
           "Sets how schooling works (start age, exam pressure, tutoring, who gets to university and what it costs),"
           " how mental illness is treated, and how accepting people are (schooling.py).", 0.5, 0.3, 0.0),
    Factor("iq", "temperament", "mental", "Measured intelligence (IQ)",
           "General ability on tests: faster learning at school, better exam results, more doors at 18. Explains about a"
           " quarter of the spread in school results, not destiny.", 0.4, 0.2, 0.0),
    Factor("adaptability", "temperament", "mental", "Ability to adapt",
           "How well he copes with change: new schools, moving, a new job. Shortens the dip after each transition.",
           0.5, 0.18, 0.0),
    Factor("minority_status", "family", "background", "Majority or minority where he lives",
           "Being a visible minority exposes him to prejudice at school, in hiring (about 1 in 3 fewer callbacks in"
           " field experiments) and on the street, which adds stress (prejudice.py).", 0.25, 0.3, 0.1),
    Factor("migrant_background", "family", "background", "Migrant background",
           "Born elsewhere or to parents who were: language and belonging at school, accent bias, and a family"
           " that often pushes education hard.", 0.25, 0.3, 0.1),
    Factor("prejudice_climate", "surroundings", "social", "How prejudiced society around him is",
           "How often people are judged for who they are. Raises what he faces, and what he absorbs and may act out.",
           0.4, 0.2, 0.05),
    Factor("phone_rules", "surroundings", "technological", "Phone rules at home",
           "Limits on phones: a later first phone, phones out of the bedroom at night, less scrolling (digital.py).",
           0.4, 0.22, 0.0),
]

EXPOSURES += SCHOOL + FRIENDS + SURROUNDINGS + TEMPERAMENT + WORLD

ALL: Dict[str, Factor] = {f.key: f for f in FAMILY + EXPOSURES}


def school_effectiveness(F) -> float:
    """How much of the teaching reaches him: quality, less crowding, more with warm teachers."""
    return min(1.0, max(0.0, F["school_quality"] * (1 - 0.35 * F["class_crowding"]) * (0.7 + 0.3 * F["teacher_warmth"])))


@dataclass
class FactorSet:
    """The values in force at the current age, plus where each one came from."""
    values: Dict[str, float]
    source: Dict[str, str]                         # 'seeded' | 'user' | 'timeline' | 'live'
    timeline: List[dict] = field(default_factory=list)   # [{"age_years": 30, "key": "...", "value": 0.9}]

    def __getitem__(self, k: str) -> float:
        v = self.values.get(k)
        return ALL[k].mean if v is None else v      # a life saved before a factor existed: its average

    def apply_timeline(self, age_months: int) -> List[str]:
        """Applies scheduled changes whose age has arrived. Returns descriptions of the ones applied."""
        done = []
        for item in self.timeline:
            if item.get("_applied"):
                continue
            if age_months >= int(round(float(item["age_years"]) * 12)):
                self.set(item["key"], float(item["value"]), "timeline")
                item["_applied"] = True
                done.append(f"{ALL[item['key']].label} set to {float(item['value']):.2f}")
        return done

    def set(self, key: str, value: float, source: str) -> None:
        if key not in ALL:
            raise KeyError(key)
        self.values[key] = min(1.0, max(0.0, value))
        self.source[key] = source

    def to_json(self) -> dict:
        return {k: {"value": round(v, 3), "source": self.source[k]} for k, v in self.values.items()}

    def copy(self) -> "FactorSet":
        return FactorSet(dict(self.values), dict(self.source), [dict(t) for t in self.timeline])


def sample(seed: int, overrides: Optional[Dict[str, float]] = None,
           timeline: Optional[List[dict]] = None) -> FactorSet:
    """Seeds every factor. User overrides win; exposures not overridden are correlated with family status."""
    rng = random.Random(seed * 7919 + 17)
    overrides = dict(overrides or {})
    for k in overrides:
        if k not in ALL:
            raise KeyError(f"unknown factor {k!r}")
    values: Dict[str, float] = {}
    source: Dict[str, str] = {}

    def clip(x: float) -> float:
        return min(1.0, max(0.0, x))

    for f in FAMILY:
        if f.key in overrides:
            values[f.key], source[f.key] = clip(float(overrides[f.key])), "user"
        elif f.key == "sex":
            values[f.key], source[f.key] = float(rng.random() < 0.5), "seeded"
        else:
            values[f.key], source[f.key] = clip(rng.gauss(f.mean, f.sd)), "seeded"
    # Richer families talk and read more.
    if "parent_education" not in overrides:
        values["parent_education"] = clip(0.6 * values["parent_education"] + 0.4 * values["ses"])
    poverty = 0.5 - values["ses"]
    for f in EXPOSURES:
        if f.key in overrides:
            values[f.key], source[f.key] = clip(float(overrides[f.key])), "user"
        else:
            values[f.key], source[f.key] = clip(rng.gauss(f.mean + 2 * f.ses * poverty, f.sd)), "seeded"
    if "region" not in overrides:                  # a place, not a level: one of the regions
        values["region"] = rng.randrange(len(REGION_NAMES)) / (len(REGION_NAMES) - 1)
    for k in ("minority_status", "migrant_background"):
        if k not in overrides:                     # choices: snap to the nearest option
            values[k] = min((0.0, 0.5, 1.0), key=lambda o: abs(o - values[k]))
    return FactorSet(values, source, [dict(t) for t in (timeline or [])])


# How each factor is shown and set in the UI, in what it means rather than as a bare 0-1 number. The model still
# uses 0-1 inside; these only translate. kinds:
#   count   a whole number of things: value = n / max
#   choice  one of a few options: value = the option's number
#   scale   a real quantity: value = (x - lo) / (hi - lo)
#   level   a judgement with no natural unit: shown in words (none .. very high)
UNITS: Dict[str, dict] = {
    "siblings": {"kind": "count", "max": 3, "unit": "brothers or sisters"},
    "friend_count": {"kind": "count", "max": 8, "unit": "friends over his life (clubs add more)"},
    "genetic_risk": {"kind": "count", "max": 8, "unit": "of 8 risk genes, on average"},
    "sex": {"kind": "choice", "options": [[0, "female"], [1, "male"]]},
    "parent_education": {"kind": "choice", "options": [[0, "no schooling"], [0.25, "school"], [0.5, "vocational"],
                                                       [0.75, "degree"], [1, "postgraduate"]]},
    "higher_ed_path": {"kind": "choice", "options": [[0, "work after school"], [0.5, "vocational, to 21"],
                                                     [1, "university, to 23"]]},
    "school_ai_policy": {"kind": "choice", "options": [[0, "banned"], [0.5, "some use"], [1, "used openly"]]},
    "ses": {"kind": "scale", "lo": 1, "hi": 99, "step": 1, "unit": "income percentile"},
    "household_speech": {"kind": "scale", "lo": 5000, "hi": 30000, "step": 500, "unit": "words a day around him"},
    "local_pollution": {"kind": "scale", "lo": 5, "hi": 35, "step": 1, "unit": "µg/m³ PM2.5"},
    "screen_time": {"kind": "scale", "lo": 0, "hi": 8, "step": 0.5, "unit": "hours of screens a day"},
    "caregiver_phubbing": {"kind": "scale", "lo": 0, "hi": 6, "step": 0.5, "unit": "hours a day carers spend on phones"},
    "class_crowding": {"kind": "scale", "lo": 15, "hi": 40, "step": 1, "unit": "pupils per class"},
    "homework_load": {"kind": "scale", "lo": 0, "hi": 15, "step": 0.5, "unit": "hours of homework a week"},
    "shift_work": {"kind": "scale", "lo": 0, "hi": 20, "step": 1, "unit": "night shifts a month"},
    "early_antibiotics": {"kind": "scale", "lo": 0, "hi": 2.2, "step": 0.1, "unit": "antibiotic courses before 3, expected"},
    "extreme_weather": {"kind": "scale", "lo": 0, "hi": 2.4, "step": 0.1, "unit": "disasters a decade, expected"},
    "online_friend_share": {"kind": "scale", "lo": 0, "hi": 100, "step": 5, "unit": "% of friends online-only"},
    "student_debt": {"kind": "scale", "lo": 0, "hi": 100, "step": 5, "unit": "% of study costs borrowed"},
    "curr_math": {"kind": "scale", "lo": 0, "hi": 100, "step": 5, "unit": "% weight on maths"},
    "curr_language": {"kind": "scale", "lo": 0, "hi": 100, "step": 5, "unit": "% weight on reading"},
    "curr_social_emotional": {"kind": "scale", "lo": 0, "hi": 100, "step": 5, "unit": "% weight on feelings"},
    "curr_arts_play": {"kind": "scale", "lo": 0, "hi": 100, "step": 5, "unit": "% weight on arts and play"},
}
REGION_NAMES = ["North America", "Latin America", "Western Europe", "Nordic countries", "Eastern Europe",
                "Middle East and North Africa", "Sub-Saharan Africa", "South Asia", "East Asia", "Southeast Asia",
                "Oceania"]
UNITS.update({
    "region": {"kind": "choice", "options": [[round(i / (len(REGION_NAMES) - 1), 4), n] for i, n in enumerate(REGION_NAMES)]},
    "iq": {"kind": "scale", "lo": 70, "hi": 145, "step": 1, "unit": "IQ points (100 is average)"},
    "minority_status": {"kind": "choice", "options": [[0, "majority"], [0.5, "a minority"], [1, "a visible minority"]]},
    "migrant_background": {"kind": "choice", "options": [[0, "local family"], [0.5, "child of migrants"],
                                                         [1, "migrated himself"]]},
})
LEVEL_WORDS = ["none", "very low", "low", "moderate", "high", "very high"]


def catalogue() -> List[dict]:
    """The factor list for the UI, with how each one is shown (UNITS)."""
    return [{"key": f.key, "stage": f.stage, "stage_label": STAGE_LABEL[f.stage], "domain": f.domain,
             "label": f.label.split(" (0")[0], "effect": f.effect, "mean": f.mean,
             "ui": UNITS.get(f.key, {"kind": "level", "words": LEVEL_WORDS})} for f in FAMILY + EXPOSURES]
