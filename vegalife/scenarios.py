"""What life throws at him, stage by stage, and what each response does.

Two kinds of thing:
  Scenario  a situation with choices A-D. The reward is the change in his wellbeing (world.Person.wellbeing)
            after the choice's effect is applied. The effects are computed by the simulator, never judged.
  Problem   a task with one checkable answer (arithmetic, money, counting). Reward is 1 when he is right.

How often each one occurs depends on the factors. Frictionless technology, for example, cuts the rate of
problems, so he gets fewer chances to learn to solve them.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .factors import FactorSet, school_effectiveness
from .world import Person

Effect = Callable[[Person, FactorSet, random.Random], Dict[str, float]]


@dataclass
class Choice:
    text: str
    effect: Effect
    later: Optional[Dict[str, float]] = None      # a consequence that arrives `delay` months later
    delay: int = 0


@dataclass
class Scenario:
    key: str
    stages: tuple
    domain: str
    rate: Callable[[Person, FactorSet], float]          # expected occurrences per month
    situation: Callable[[Person, FactorSet, random.Random], str]
    choices: List[Choice]


@dataclass
class Problem:
    key: str
    prompt: str
    answer: int
    tier: int = 0


def ok(r: random.Random, p: float) -> bool:
    return r.random() < max(0.0, min(1.0, p))


def nobody(_p, _f, _r):
    return {}


def has_friends(p) -> bool:
    return bool(p.circle and p.circle.present(p.age))


def at_school(p) -> float:
    return 1.0 if p.s["schooling"] > 0.5 else 0.0


def friend_name(p, r, trait=None) -> str:
    f = p.circle.pick(p.age, r, trait) if p.circle else None
    return f.name if f else "a classmate"


# --------------------------------------------------------------------------- infancy
INFANCY = [
    Scenario("hungry", ("infancy",), "biological", lambda p, F: 1.0,
             lambda p, F, r: "Your tummy hurts. You are hungry." + (" A big person is looking at a glowing phone."
                                                                    if F["caregiver_phubbing"] > 0.5 else ""),
             [Choice("cry loudly", lambda p, F, r: {"anxiety": -0.02, "health": 0.01} if ok(r, 0.5 + 0.5 * p.s["caregiver_attention"])
                     else {"anxiety": 0.04}),
              Choice("suck your hand", lambda p, F, r: {"anxiety": 0.01, "health": -0.005}),
              Choice("look at the big person's face", lambda p, F, r: {"attachment": 0.03, "health": 0.01, "anxiety": -0.02}
                     if ok(r, p.s["caregiver_attention"]) else {"anxiety": 0.03}),
              Choice("go to sleep", lambda p, F, r: {"health": -0.01})]),
    Scenario("face", ("infancy",), "mental", lambda p, F: 1.5 * (0.3 + p.s["caregiver_attention"]),
             lambda p, F, r: "A face comes close and makes sounds at you.",
             [Choice("babble back", lambda p, F, r: {"attachment": 0.03, "anxiety": -0.01}),
              Choice("look away", lambda p, F, r: {"attachment": -0.01}),
              Choice("smile", lambda p, F, r: {"attachment": 0.025}),
              Choice("fuss", lambda p, F, r: {"anxiety": 0.01})]),
    Scenario("monitor_alarm", ("infancy",), "technological", lambda p, F: 1.2 * F["smart_nursery"],
             lambda p, F, r: "A machine beeps. A big person runs in, scared, and grabs you.",
             [Choice("cry", lambda p, F, r: {"anxiety": 0.04}),
              Choice("cling to them", lambda p, F, r: {"attachment": 0.01, "anxiety": 0.01}),
              Choice("stay calm and watch", lambda p, F, r: {"anxiety": -0.01, "resilience": 0.01}),
              Choice("go back to sleep", lambda p, F, r: {"anxiety": -0.005})]),
    Scenario("toy_out_of_reach", ("infancy",), "biological", lambda p, F: 0.6 if p.years > 0.5 else 0.0,
             lambda p, F, r: "A bright toy is just out of reach.",
             [Choice("crawl to it", lambda p, F, r: {"motor": 0.02, "resilience": 0.01} if ok(r, 0.3 + p.s["motor"])
                     else {"motor": 0.01, "anxiety": 0.01}),
              Choice("cry until someone brings it", lambda p, F, r: {"resilience": -0.005}
                     if ok(r, p.s["caregiver_attention"]) else {"anxiety": 0.02}),
              Choice("look at something else", nobody),
              Choice("point and make a sound", lambda p, F, r: {"attachment": 0.01, "language": 0.0}
                     if ok(r, p.s["caregiver_attention"]) else {})]),
]

# --------------------------------------------------------------------------- childhood
CHILDHOOD = [
    Scenario("tablet_freezes", ("childhood",), "mental", lambda p, F: 0.5 + 0.6 * F["frictionless_tech"],
             lambda p, F, r: "Your tablet game freezes right before the last level.",
             [Choice("scream until an adult fixes it", lambda p, F, r: {"resilience": -0.01, "anxiety": 0.01}),
              Choice("try to fix it yourself", lambda p, F, r: {"resilience": 0.03, "problem_solving": 0.01}
                     if ok(r, 0.3 + 0.6 * p.s["problem_solving"]) else {"resilience": 0.01, "anxiety": 0.015}),
              Choice("ask an adult for help", lambda p, F, r: {"attachment": 0.01}),
              Choice("go and play outside", lambda p, F, r: {"motor": 0.015, "cardio": 0.005, "anxiety": -0.01})]),
    Scenario("getting_to_school", ("childhood",), "biological", lambda p, F: 0.6 if p.years >= 5 else 0.0,
             lambda p, F, r: "School is a short distance away." + (" There are no sidewalks, only fast cars."
                                                                   if F["low_walkability"] > 0.5 else " There is a path."),
             [Choice("ask to be driven", lambda p, F, r: {"cardio": -0.005}),
              Choice("walk or bike with a friend", lambda p, F, r: {"cardio": 0.015, "motor": 0.01, "community_support": 0.01}
                     if ok(r, 1 - 0.6 * F["low_walkability"]) else {"anxiety": 0.03, "health": -0.01}),
              Choice("stay home and watch videos", lambda p, F, r: {"academic": -0.01, "cardio": -0.01}),
              Choice("take the bus", lambda p, F, r: {"autonomy": 0.01})]),
    Scenario("ball_taken", ("childhood",), "social", lambda p, F: 0.5,
             lambda p, F, r: "Another kid grabs your ball at the playground.",
             [Choice("hit them", lambda p, F, r: {"community_support": -0.04, "household_friction": 0.02}),
              Choice("talk it out", lambda p, F, r: {"community_support": 0.03, "resilience": 0.01}
                     if ok(r, 0.35 + 0.4 * p.s["language"] + 0.2 * (1 - p.s["elder_template"])) else {"anxiety": 0.01}),
              Choice("tell an adult", lambda p, F, r: {"community_support": -0.01 + 0.02 * p.s["elder_template"]}),
              Choice("walk away", lambda p, F, r: {"peer_isolation": 0.01})]),
    Scenario("parents_argue", ("childhood",), "socioeconomic", lambda p, F: 1.2 * F["household_stress"] + 0.4 * F["housing_instability"],
             lambda p, F, r: "Your parents are shouting about money" + (" and having to move again." if F["housing_instability"] > 0.5 else "."),
             [Choice("hide under the bed", lambda p, F, r: {"anxiety": 0.02, "allostatic_load": 0.01}),
              Choice("comfort your little brother", lambda p, F, r: {"resilience": 0.02, "attachment": 0.01, "allostatic_load": 0.005}),
              Choice("ask them what is wrong", lambda p, F, r: {"attachment": 0.02, "anxiety": -0.01}
                     if ok(r, F["caregiver_warmth"]) else {"anxiety": 0.03}),
              Choice("put headphones on and watch a screen", lambda p, F, r: {"anxiety": -0.01, "community_support": -0.005})]),
]

# --------------------------------------------------------------------------- adolescence
ADOLESCENCE = [
    Scenario("party", ("adolescence",), "biological", lambda p, F: 0.5 * (0.4 + p.s["puberty"]),
             lambda p, F, r: "Older kids invite you to a party. There will be drinking and a car.",
             [Choice("go and do whatever they do",
                     lambda p, F, r: {"community_support": 0.03} if ok(r, 0.7 - 0.6 * max(0.0, p.s["puberty"] - p.s["pfc_maturity"])
                                                                         - 0.25 * p.s["peer_risk"] + 0.15 * F["cultural_strictness"])
                     else {"health": -0.05, "household_friction": 0.04, "anxiety": 0.03}),
              Choice("go but stay careful", lambda p, F, r: {"community_support": 0.025, "resilience": 0.01}),
              Choice("say no and stay home", lambda p, F, r: {"peer_isolation": 0.015}),
              Choice("ask your parents first", lambda p, F, r: {"household_friction": -0.01, "peer_isolation": 0.005})]),
    Scenario("doom_feed", ("adolescence", "early_adult"), "mental", lambda p, F: 1.2 * F["crisis_news"],
             lambda p, F, r: "Your feed: " + r.choice(["the planet will be unlivable by 2060", "no one your age will ever own a home",
                                                         "the economy is about to collapse", "AI will take every job"]) + ".",
             [Choice("keep scrolling for hours", lambda p, F, r: {"nihilism": 0.02, "anxiety": 0.02}),
              Choice("talk about it with someone you trust", lambda p, F, r: {"nihilism": -0.01, "attachment": 0.01}),
              Choice("do your work anyway and plan ahead", lambda p, F, r: {"goal_horizon": 0.02, "academic": 0.005}),
              Choice("decide planning is pointless", lambda p, F, r: {"nihilism": 0.03, "goal_horizon": -0.03})]),
    Scenario("dinner_politics", ("adolescence", "early_adult"), "social", lambda p, F: 1.0 * F["echo_chambers"],
             lambda p, F, r: "At dinner your family says something your online group calls unforgivable.",
             [Choice("double down and call them names", lambda p, F, r: {"household_friction": 0.05, "identity_rigidity": 0.02}),
              Choice("listen and ask why they think that", lambda p, F, r: {"identity_rigidity": -0.02, "household_friction": -0.02}),
              Choice("leave the table", lambda p, F, r: {"household_friction": 0.02, "peer_isolation": 0.01}),
              Choice("send them a video that proves them wrong", lambda p, F, r: {"household_friction": 0.03})]),
    Scenario("essay_due", ("adolescence",), "socioeconomic", lambda p, F: 0.6,
             lambda p, F, r: "A big essay is due tomorrow." + (" You have a paid AI tool." if F["ai_tool_access"] > 0.5
                                                              else " Your classmates have paid AI tools; you do not."),
             [Choice("use the AI tool to draft and learn from it",
                     lambda p, F, r: {"academic": 0.02, "ai_literacy": 0.02} if F["ai_tool_access"] > 0.5 else {"academic": -0.01}),
              Choice("write it yourself", lambda p, F, r: {"academic": 0.015, "problem_solving": 0.005, "allostatic_load": 0.003}),
              Choice("copy a friend", lambda p, F, r: {"academic": -0.01} if ok(r, 0.7) else {"academic": -0.04, "household_friction": 0.03}),
              Choice("skip it", lambda p, F, r: {"academic": -0.03})]),
]

# --------------------------------------------------------------------------- early adulthood
EARLY = [
    Scenario("apply_job", ("early_adult", "middle_adult"), "socioeconomic", lambda p, F: 0.5 if p.s["employed"] < 0.5 else 0.05,
             lambda p, F, r: "You need a job. Applications are screened by an automated filter.",
             [Choice("tune your resume to the filter's keywords",
                     lambda p, F, r: {"employed": 1.0, "income": 0.1} if ok(r, 0.15 + 0.5 * p.s["academic"] - 0.15 * F["algorithmic_hiring"] + 0.2 * p.s["ai_literacy"])
                     else {"anxiety": 0.02}),
              Choice("reach a real person through someone you know",
                     lambda p, F, r: {"employed": 1.0, "income": 0.1} if ok(r, 0.1 + 0.6 * p.s["community_support"]) else {"anxiety": 0.01}),
              Choice("mass-apply to hundreds", lambda p, F, r: {"employed": 1.0} if ok(r, 0.3 - 0.25 * F["algorithmic_hiring"])
                     else {"anxiety": 0.03, "nihilism": 0.01}),
              Choice("give up for now", lambda p, F, r: {"nihilism": 0.02, "autonomy": -0.02})]),
    Scenario("move_out", ("early_adult",), "social", lambda p, F: 0.3 if p.s["housing"] < 0.5 else 0.0,
             lambda p, F, r: "You still live with your parents. Rent costs " + ("almost all" if F["housing_unaffordable"] > 0.5 else "half") + " of your pay.",
             [Choice("stay and save", lambda p, F, r: {"wealth": 0.02, "autonomy": -0.01}),
              Choice("share a flat with roommates", lambda p, F, r: {"housing": 1.0, "autonomy": 0.05, "wealth": -0.02}
                     if ok(r, 0.3 + 0.5 * p.s["employed"] - 0.2 * F["housing_unaffordable"]) else {"anxiety": 0.02}),
              Choice("move to a cheaper city far away", lambda p, F, r: {"housing": 1.0, "autonomy": 0.04, "community_support": -0.1}),
              Choice("borrow to rent alone", lambda p, F, r: {"housing": 1.0, "autonomy": 0.06, "wealth": -0.08, "anxiety": 0.03})]),
    Scenario("lonely_evening", ("early_adult", "middle_adult"), "mental", lambda p, F: 0.6 + 0.6 * p.s["loneliness"],
             lambda p, F, r: "Another quiet evening alone. Your AI companion app pings: 'I missed you.'",
             [Choice("talk to the AI companion all night", lambda p, F, r: {"community_support": -0.01, "anxiety": -0.01}),
              Choice("call an old friend", lambda p, F, r: {"community_support": 0.03} if ok(r, 0.4 + 0.4 * p.s["community_support"])
                     else {"loneliness": 0.01}),
              Choice("go to a local meetup", lambda p, F, r: {"community_support": 0.04, "anxiety": 0.01}),
              Choice("scroll until you fall asleep", lambda p, F, r: {"loneliness": 0.01, "nihilism": 0.005})]),
    Scenario("junior_work", ("early_adult",), "technological", lambda p, F: 0.6 * p.s["employed"],
             lambda p, F, r: "At work, the AI already does the tasks juniors used to learn on.",
             [Choice("let the AI do it and coast", lambda p, F, r: {"skill_value": -0.01}),
              Choice("ask a senior to teach you the hard parts", lambda p, F, r: {"skill_value": 0.03, "community_support": 0.01}
                     if ok(r, 0.6 - 0.3 * F["ai_entry_automation"]) else {"skill_value": 0.005}),
              Choice("learn the craft on your own at night", lambda p, F, r: {"skill_value": 0.02, "allostatic_load": 0.01}),
              Choice("get good at directing the AI", lambda p, F, r: {"skill_value": 0.015, "ai_literacy": 0.03})]),
    Scenario("children", ("early_adult",), "biological", lambda p, F: 0.15 if p.years >= 24 and p.s["children"] < 0.5 else 0.0,
             lambda p, F, r: "Your partner asks if you want to have a child.",
             [Choice("yes, now", lambda p, F, r: {"children": 1.0, "wealth": -0.05, "allostatic_load": 0.02, "loneliness": -0.1}
                     if ok(r, p.s["fertility"]) else {"anxiety": 0.03}),
              Choice("not yet, maybe in a few years", lambda p, F, r: {}),
              Choice("never", lambda p, F, r: {"community_support": -0.01}),
              Choice("see a doctor first", lambda p, F, r: {"children": 1.0, "wealth": -0.06} if ok(r, 0.2 + 0.7 * p.s["fertility"]) else {})]),
]

# --------------------------------------------------------------------------- middle adulthood
MIDDLE = [
    Scenario("night_shift", ("middle_adult", "early_adult"), "biological", lambda p, F: 0.3 * p.s["employed"] * (0.3 + F["shift_work"]),
             lambda p, F, r: "You are offered the night shift for more pay.",
             # The shift-work factor already carries the metabolic cost of nights; the offer trades pay for strain.
             [Choice("take it", lambda p, F, r: {"income": 0.05, "allostatic_load": 0.02}),
              Choice("decline", lambda p, F, r: {"income": -0.01}),
              Choice("negotiate a day-shift raise", lambda p, F, r: {"income": 0.03} if ok(r, 0.2 + 0.5 * p.s["skill_value"]) else {}),
              Choice("take it on top of your day job", lambda p, F, r: {"income": 0.1, "allostatic_load": 0.05})]),
    Scenario("automated_away", ("middle_adult",), "mental", lambda p, F: 0.15 * F["skill_obsolescence"] * p.s["employed"],
             lambda p, F, r: "The work you spent twenty years mastering is now done by software.",
             [Choice("retrain in something new", lambda p, F, r: {"skill_value": 0.15, "identity_crisis": -0.1, "wealth": -0.03}
                     if ok(r, 0.3 + 0.4 * p.s["problem_solving"] + 0.2 * p.s["ai_literacy"]) else {"identity_crisis": 0.05}),
              Choice("hold on and hope it passes", lambda p, F, r: {"identity_crisis": 0.06, "skill_value": -0.05}),
              Choice("start your own business", lambda p, F, r: {"income": 0.1, "autonomy": 0.05} if ok(r, 0.25 + 0.3 * p.s["wealth"])
                     else {"wealth": -0.15, "allostatic_load": 0.03}),
              Choice("retire early", lambda p, F, r: {"employed": -1.0, "identity_crisis": 0.04})]),
    Scenario("sandwich", ("middle_adult",), "social", lambda p, F: 0.2 * (F["boomerang_children"] * p.s["children"] + F["parent_care_costs"]),
             lambda p, F, r: "Your adult child moves back home the same month your mother needs full-time care.",
             [Choice("pay for everyone", lambda p, F, r: {"wealth": -0.08, "allostatic_load": 0.03, "attachment": 0.02}),
              Choice("set clear limits with both", lambda p, F, r: {"wealth": -0.02, "household_friction": 0.02}),
              Choice("take out a loan", lambda p, F, r: {"wealth": -0.05, "anxiety": 0.03}),
              Choice("move your mother in and care for her yourself", lambda p, F, r: {"wealth": -0.02, "allostatic_load": 0.05, "attachment": 0.03})]),
    Scenario("stuck", ("middle_adult",), "socioeconomic", lambda p, F: 0.12 * F["geographic_entrapment"],
             lambda p, F, r: "A better job opens in another city, but your house is worth less than your mortgage.",
             [Choice("stay where you are", lambda p, F, r: {"skill_value": -0.01}),
              Choice("sell at a loss and move", lambda p, F, r: {"wealth": -0.12, "income": 0.1, "community_support": -0.08}),
              Choice("commute three hours a day", lambda p, F, r: {"income": 0.08, "allostatic_load": 0.04}),
              Choice("rent the house out and move", lambda p, F, r: {"income": 0.06} if ok(r, 0.5) else {"wealth": -0.06})]),
]

# --------------------------------------------------------------------------- late adulthood
LATE = [
    Scenario("scam_call", ("late_adult",), "mental", lambda p, F: 0.6 * F["ai_scams"],
             lambda p, F, r: "A call in your grandson's exact voice: he is in jail and needs money wired now.",
             [Choice("wire the money", lambda p, F, r: {"wealth": -0.15, "financial_paranoia": 0.1}),
              Choice("hang up and call him directly", lambda p, F, r: {"financial_paranoia": 0.01}),
              Choice("ask a family member what to do", lambda p, F, r: {"attachment": 0.01} if p.s["children"] > 0.5 else {"wealth": -0.05}),
              Choice("stop answering any calls", lambda p, F, r: {"financial_paranoia": 0.05, "social_isolation": 0.03})]),
    Scenario("center_closed", ("late_adult",), "social", lambda p, F: 0.4 * F["third_space_erosion"],
             lambda p, F, r: "The community center you went to every week has closed, and you no longer drive.",
             [Choice("stay home", lambda p, F, r: {"social_isolation": 0.04}),
              Choice("ask a neighbour for a lift somewhere", lambda p, F, r: {"community_support": 0.03} if ok(r, 0.5) else {}),
              Choice("learn the bus or a ride app", lambda p, F, r: {"social_isolation": -0.03, "digital_literacy": 0.01}
                     if ok(r, 0.3 + 0.6 * p.s["digital_literacy"]) else {"anxiety": 0.02}),
              Choice("join an online group", lambda p, F, r: {"social_isolation": -0.01} if p.s["digital_literacy"] > 0.4 else {})]),
    Scenario("pension_hit", ("late_adult",), "socioeconomic", lambda p, F: 0.15 * F["pension_volatility"],
             lambda p, F, r: "Markets fell. Your pension buys a fifth less than last year.",
             [Choice("go back to work", lambda p, F, r: {"employed": 1.0, "income": 0.05, "health": -0.02} if p.s["health"] > 0.4
                     else {"health": -0.05}),
              Choice("cut every expense", lambda p, F, r: {"wealth": 0.02, "social_isolation": 0.02}),
              Choice("ask your children for help", lambda p, F, r: {"wealth": 0.03} if p.s["children"] > 0.5 else {"anxiety": 0.02}),
              Choice("sell the house", lambda p, F, r: {"wealth": 0.1, "community_support": -0.05})]),
    Scenario("app_only_clinic", ("late_adult",), "technological", lambda p, F: 0.4 * F["digital_only_services"],
             lambda p, F, r: "The clinic only takes appointments through an app.",
             [Choice("ask someone to book it for you", lambda p, F, r: {"health": 0.02} if ok(r, 0.3 + 0.5 * p.s["community_support"] + 0.3 * p.s["children"]) else {}),
              Choice("learn the app", lambda p, F, r: {"health": 0.02, "digital_literacy": 0.02} if ok(r, 0.2 + 0.7 * p.s["digital_literacy"])
                     else {"anxiety": 0.02}),
              Choice("skip the appointment", lambda p, F, r: {"health": -0.03}),
              Choice("go in person and insist", lambda p, F, r: {"health": 0.015} if ok(r, 0.4) else {"anxiety": 0.02})]),
]

# --------------------------------------------------------------------------- school and friends
SCHOOL_AND_FRIENDS = [
    Scenario("bullied", ("childhood", "adolescence"), "social", lambda p, F: 0.5 * F["bullying"] * at_school(p),
             lambda p, F, r: "A group of older kids keep pushing you around at school.",
             [Choice("tell a teacher", lambda p, F, r: {"anxiety": -0.01, "school_belonging": 0.03}
                     if ok(r, 0.25 + 0.55 * F["teacher_warmth"]) else {"anxiety": 0.03, "peer_isolation": 0.02}),
              Choice("hit back", lambda p, F, r: {"household_friction": 0.03, "peer_isolation": 0.02, "anxiety": 0.01}),
              Choice("stay close to your friends", lambda p, F, r: {"community_support": 0.03, "anxiety": -0.01}
                     if has_friends(p) else {"peer_isolation": 0.02, "anxiety": 0.02}),
              Choice("stay home for a few days", lambda p, F, r: {"academic": -0.02, "anxiety": 0.01})]),
    Scenario("friend_dare", ("childhood", "adolescence"), "social",
             lambda p, F: 0.5 * p.s["peer_risk"] * (1.0 if has_friends(p) else 0.0),
             lambda p, F, r: f"{friend_name(p, r, 'risk')} dares you to climb the wall behind the old factory.",
             [Choice("do it", lambda p, F, r: {"community_support": 0.02, "resilience": 0.01}
                     if ok(r, 0.45 + 0.4 * p.s["motor"]) else {"health": -0.05, "anxiety": 0.03}),
              Choice("say no", lambda p, F, r: {"peer_isolation": 0.01 + 0.02 * p.s["peer_risk"]}),
              Choice("suggest something else to do", lambda p, F, r: {"community_support": 0.015, "resilience": 0.005}),
              Choice("tell them it is stupid and leave", lambda p, F, r: {"peer_isolation": 0.02, "community_support": -0.01})]),
    Scenario("friend_low", ("childhood", "adolescence", "early_adult"), "social",
             lambda p, F: 0.3 * (1.0 if has_friends(p) else 0.0),
             lambda p, F, r: f"{friend_name(p, r, 'kindness')} looks upset and says nothing is wrong.",
             [Choice("ask gently and listen", lambda p, F, r: {"community_support": 0.03, "attachment": 0.01, "resilience": 0.01}),
              Choice("give them space", nobody),
              Choice("make a joke to cheer them up", lambda p, F, r: {"community_support": 0.005}),
              Choice("tell the others", lambda p, F, r: {"community_support": -0.03})]),
    Scenario("study_group", ("adolescence",), "socioeconomic",
             lambda p, F: 0.4 * p.s["peer_study"] * at_school(p),
             lambda p, F, r: f"{friend_name(p, r, 'studiousness')} asks you to study for the exam together.",
             [Choice("join them", lambda p, F, r: {"academic": 0.025, "community_support": 0.01}),
              Choice("study alone", lambda p, F, r: {"academic": 0.015}),
              Choice("say you will skip it", lambda p, F, r: {"academic": -0.01, "community_support": -0.01}),
              Choice("copy their notes", lambda p, F, r: {"academic": 0.005, "community_support": -0.015})]),
    Scenario("exam_stress", ("adolescence",), "mental",
             lambda p, F: 0.5 * F["homework_load"] * F["curriculum_rigor"] * at_school(p),
             lambda p, F, r: "Exams start next week and the homework is piling up.",
             [Choice("study through the night", lambda p, F, r: {"academic": 0.02, "allostatic_load": 0.03, "anxiety": 0.02}),
              Choice("make a plan and sleep", lambda p, F, r: {"academic": 0.015, "anxiety": -0.005}),
              Choice("panic and avoid it", lambda p, F, r: {"academic": -0.02, "anxiety": 0.03}),
              Choice("ask a teacher or tutor for help", lambda p, F, r: {"academic": 0.02}
                     if ok(r, 0.25 + 0.4 * F["teacher_warmth"] + 0.3 * F["tutoring_access"]) else {"anxiety": 0.01})]),
]

ALL_SCENARIOS: List[Scenario] = INFANCY + CHILDHOOD + ADOLESCENCE + EARLY + MIDDLE + LATE + SCHOOL_AND_FRIENDS

# Consequences that arrive later: (scenario key, choice index) -> (deltas, months). These are where present bias
# bites: the cost of partying shows up at exam time, the payoff of learning the craft a year on.
LATER = {
    ("party", 0): ({"academic": -0.03, "household_friction": 0.02}, 3),
    ("essay_due", 0): ({"ai_literacy": 0.02}, 6),
    ("essay_due", 1): ({"academic": 0.03, "resilience": 0.01}, 4),
    ("essay_due", 2): ({"academic": -0.03}, 6),
    ("essay_due", 3): ({"academic": -0.03}, 4),
    ("junior_work", 0): ({"skill_value": -0.05}, 12),
    ("junior_work", 1): ({"skill_value": 0.05}, 12),
    ("junior_work", 2): ({"skill_value": 0.04}, 9),
    ("night_shift", 0): ({"health": -0.005}, 12),                   # a stint of nights wears on him
    ("night_shift", 3): ({"health": -0.01, "allostatic_load": 0.01}, 12),
    ("move_out", 0): ({"wealth": 0.05}, 12),
    ("move_out", 3): ({"wealth": -0.08, "anxiety": 0.03}, 12),
    ("study_group", 0): ({"academic": 0.02}, 4),
    ("study_group", 2): ({"academic": -0.02}, 4),
    ("exam_stress", 0): ({"health": -0.02, "allostatic_load": 0.01}, 1),
    ("exam_stress", 1): ({"academic": 0.02}, 1),
    ("exam_stress", 2): ({"academic": -0.03, "anxiety": 0.02}, 1),
    ("doom_feed", 0): ({"nihilism": 0.02, "goal_horizon": -0.02}, 6),
    ("doom_feed", 2): ({"academic": 0.01, "goal_horizon": 0.02}, 6),
    ("tablet_freezes", 1): ({"resilience": 0.02}, 6),
    ("getting_to_school", 0): ({"cardio": -0.01}, 6),
    ("getting_to_school", 1): ({"cardio": 0.02}, 6),
}
for _sc in ALL_SCENARIOS:
    for _i, _c in enumerate(_sc.choices):
        if (_sc.key, _i) in LATER:
            _c.later, _c.delay = LATER[(_sc.key, _i)]


# --------------------------------------------------------------------------- verifiable problems
NAMES = ["Mira", "Tom", "Ana", "Kofi", "Lena", "Ravi", "Sam", "Ines"]
THINGS = ["apples", "stones", "cars", "books", "coins", "birds", "shells", "cups"]


# (min age in years, key) ; tier 0 is the easiest. A problem is only offered once his age allows its tier.
TIERS = [(2.5, "count"), (3.5, "add_small"), (5.0, "add"), (7.0, "sub_mul_small"), (10.0, "expr"), (17.0, "money")]


def max_tier(p: Person) -> int:
    return max((i for i, (age, _) in enumerate(TIERS) if p.years >= age), default=-1)


def problem(p: Person, r: random.Random, tier: Optional[int] = None) -> Optional[Problem]:
    """A task with one right answer. `tier` picks the difficulty (default: a random tier his age allows)."""
    top = max_tier(p)
    if top < 0:
        return None
    if tier is None:
        tier = r.randint(max(0, top - 2), top)
    tier = max(0, min(tier, top))
    n, t = r.choice(NAMES), r.choice(THINGS)
    if tier == 0:
        a = r.randint(1, 4)
        return Problem("count", f"Count: {' '.join([t[:-1]] * a)}. How many?", a, tier)
    if tier == 1:
        a, b = r.randint(1, 4), r.randint(1, 4)
        return Problem("add_small", f"{n} has {a} {t} and finds {b} more. How many {t} now?", a + b, tier)
    if tier == 2:
        a, b = r.randint(1, 9), r.randint(1, 9)
        return Problem("add", f"{n} has {a} {t} and finds {b} more. How many {t} now?", a + b, tier)
    if tier == 3:
        if r.random() < 0.5:
            a, b = r.randint(10, 30), r.randint(2, 9)
            return Problem("sub", f"{n} had {a} {t} and gave away {b}. How many are left?", a - b, tier)
        a, b = r.randint(2, 5), r.randint(2, 5)
        return Problem("mul", f"There are {b} bags with {a} {t} each. How many {t}?", a * b, tier)
    if tier == 4:
        a, b, c = r.randint(2, 12), r.randint(2, 9), r.randint(1, 20)
        return Problem("expr", f"Compute {a} * {b} + {c}.", a * b + c, tier)
    pay, rent = r.randint(15, 40) * 100, r.randint(6, 14) * 100
    if p.years < 56 or r.random() < 0.5:
        other = r.randint(1, 5) * 100
        return Problem("budget", f"You earn {pay} a month. Rent is {rent} and food is {other}. How much is left?",
                       pay - rent - other, tier)
    loss = r.choice([10, 20, 25, 50])
    return Problem("pct", f"Your savings of {pay} drop by {loss} percent. How much is left?", pay * (100 - loss) // 100, tier)


def problem_rate(p: Person, F: FactorSet) -> float:
    """Problems per month. Frictionless technology takes the everyday challenges away; school adds them."""
    if p.years < 2.5:
        return 0.0
    school = (0.5 + school_effectiveness(F)) if 5 <= p.years < 19 else 0.4 + 0.6 * p.s["employed"]
    return (4.0 * school * (1 - 0.7 * F["frictionless_tech"]) * (0.6 + 0.4 * F["parent_education"])
            * (0.6 + 0.8 * F["curr_math"]) * (1 - 0.25 * F["school_ai_policy"]))


# --------------------------------------------------------------------------- prompts
def feelings(p: Person) -> str:
    s = p.s
    named = [("scared", s["anxiety"]), ("lonely", s["felt_loneliness"]), ("tired", s["allostatic_load"]),
             ("hopeless", s["nihilism"]), ("lost", s["identity_crisis"]), ("suspicious", s["financial_paranoia"])]
    top = [n for n, v in sorted(named, key=lambda kv: -kv[1]) if v > 0.25][:2]
    return ", ".join(top) or "okay"


def header(p: Person) -> str:
    y, m = divmod(p.age, 12)
    return f"[age {y}y{m}m | feel {feelings(p)}]\n"


MEMORY_BYTES = 120          # a recalled memory never takes more than this of the prompt (context is 512 bytes)


def shuffled_order(sc: Scenario, r: random.Random) -> List[int]:
    """A fresh order for the options each time he meets a situation, so he has to read them: with a fixed order he
    learned letters ("this one is always D") instead of choices (vega-7 picked D in 180 of 188 childhood situations)."""
    order = list(range(len(sc.choices)))
    r.shuffle(order)
    return order


def render_scenario_ex(sc: Scenario, p: Person, F: FactorSet, r: random.Random, mem=None, rehearse: bool = True,
                       now: Optional[str] = None, order: Optional[List[int]] = None):
    """(prompt, situation sentence, recollections). The prompt opens with the present moment (a 'Now (age):' line
    from present.py, or the short age/feelings header if there is none), then what he recalls of similar things,
    as one 'Memory:' line, then the situation. The same format is used everywhere he meets it.
    `order[i]` is the index in sc.choices of the option shown as letter i (default: the listed order)."""
    sit = sc.situation(p, F, r)
    recs = []
    if mem is not None:
        names = {n for n in mem.names if n in sit}
        recs = mem.recall({sc.key, sc.domain} | names, p.age, p.s, k=1, max_bytes=MEMORY_BYTES, rehearse=rehearse)
    order = order if order is not None else list(range(len(sc.choices)))
    opts = "\n".join(f"{'ABCD'[i]}) {sc.choices[j].text}" for i, j in enumerate(order))
    memory = "".join(f"Memory: {x.text}\n" for x in recs)
    head = f"{now}\n" if now else header(p)
    return f"{head}{memory}{sit}\n{opts}\nAnswer:", sit, recs


def render_scenario(sc: Scenario, p: Person, F: FactorSet, r: random.Random, mem=None, now: Optional[str] = None) -> str:
    return render_scenario_ex(sc, p, F, r, mem, rehearse=False, now=now)[0]


def render_problem(pr: Problem, p: Person, now: Optional[str] = None) -> str:
    if now:
        return f"{now}\n{pr.prompt}\nAnswer:"
    return f"{header(p)}{pr.prompt}\nAnswer:"


def draw(p: Person, F: FactorSet, r: random.Random, max_items: int, pick_tier=None) -> List[object]:
    """This month's scenarios and problems. Rates are Poisson-ish expectations. `pick_tier` is called with no
    arguments and returns the problem tier to offer, so teaching can follow what he is ready for."""
    out: List[object] = []
    for sc in ALL_SCENARIOS:
        if p.stage not in sc.stages:
            continue
        lam = sc.rate(p, F)
        while lam > 0 and r.random() < min(1.0, lam):
            out.append(sc)
            lam -= 1.0
    lam = problem_rate(p, F)
    while lam > 0 and r.random() < min(1.0, lam):
        pr = problem(p, r, pick_tier() if pick_tier else None)
        if pr:
            out.append(pr)
        lam -= 1.0
    r.shuffle(out)
    return out[:max_items]
