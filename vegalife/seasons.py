"""The seasons of a life: the joys and sorrows that belong to each age, what he yearns for, what he comes to regret,
and the turns that remake who he is.

Most of a life is not made of big events. It is a first word, a lost tooth, being picked last, a first kiss, a first
pay cheque, eating dinner alone in a new city, finding a first grey hair, a week without speaking to anyone at 80.
MOMENTS is a catalogue of those, each tied to the age it belongs to and to his circumstances (no friends, no
partner, money worries...), gathered from developmental research and from what people say about their own lives
(Reddit threads such as r/AskOldPeople and "the struggle nobody talks about at 30": feeling behind, friends drifting
after the mid-twenties, the body starting to complain, being single at friends' weddings, the sandwich years).

The shape of the whole, from research:
  U-curve       wellbeing dips through midlife to a low around 47-48 and rises after (Blanchflower, 132 countries)
  friends       the number of friends peaks around 25 and then declines (3.2M phone users, Royal Society Open
                Science 2016); older people choose fewer, closer ties and attend to the good (Carstensen's
                socioemotional selectivity), which is part of why late life is often happier than midlife
  fatherhood    testosterone drops a median 26-34% in men who become fathers, more for those doing 3+ hours a day of
                care (Gettler et al. 2011, PNAS); oxytocin and prolactin rise with contact. About 10% of fathers have
                pre- or postnatal depression, most at 3-6 months (Paulson & Bazemore 2010, JAMA: 10.4%; 25.6% at
                3-6 months). Mothers: hormones crash after birth; postnatal depression ~13%
  sandwich      a quarter of US adults, and 54% of those in their 40s, care for an ageing parent and a child (Pew 2025);
                sandwich carers report more emotional strain (44% vs 32%)
  identity      the last child leaving (empty nest: a loss of role for those who lived for parenting, then often new
                freedom), retirement (career.py), widowhood (family.py), giving up driving
  scams         older adults report losing $2.4bn in 2024 (FTC), with median losses rising with age ($500 in their 60s,
                $1,600+ over 80); investment, romance, impostor and tech-support scams; AI voice clones. Shame keeps
                most victims quiet
  regret        in the long run people regret what they did not do about twice as often as what they did (Gilovich &
                Medvec 1995; Pink's World Regret Survey). Pink's four kinds: foundation (money, health, study),
                boldness (chances not taken), moral (harm done), connection (people let drift). The dying most
                often wish they had lived truer to themselves, worked less, said what they felt, kept in touch with
                friends and let themselves be happier (Bronnie Ware)

Its own random generator, so it never shifts the rest of his world.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .factors import FactorSet


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


# ------------------------------------------------------------------ who is around
def _present(p, rel: str):
    return [x for x in p.family.present(p.age) if x.relation == rel]


def _friend(p) -> Optional[str]:
    fs = sorted(p.circle.present(p.age), key=lambda f: -f.closeness) if p.circle else []
    return fs[0].name if fs else None


def _nfriends(p) -> int:
    return len(p.circle.present(p.age)) if p.circle else 0


def _partner(p) -> bool:
    return bool(_present(p, "partner"))


def _kids(p, lo=0, hi=1200) -> list:
    return [k for k in _present(p, "child") if lo <= p.age - k.born < hi]


def _old_parent(p, age=75):
    return [x for x in p.family.present(p.age) if x.relation in ("mother", "father") and x.age(p.age) >= age]


def _male(F) -> bool:
    return F["sex"] >= 0.5


@dataclass
class Moment:
    key: str
    ages: tuple                               # (from, to) years
    rate: Callable                            # (p, F) -> chance this month
    texts: List[str]
    valence: float
    deltas: Dict[str, float] = field(default_factory=dict)
    chem: Dict[str, float] = field(default_factory=dict)
    once: bool = False


J, S = 1, -1
MOMENTS: List[Moment] = [
    # --- infancy ---------------------------------------------------------------------------------------------------
    Moment("first_smile", (0.1, 0.3), lambda p, F: 0.5, ["smiles for the first time, at {parent}"], 0.8,
           chem={"oxytocin": 0.08}, once=True),
    Moment("first_laugh", (0.25, 0.6), lambda p, F: 0.4, ["laughs out loud for the first time when {parent} pulls a face"],
           0.8, chem={"endorphins": 0.06}, once=True),
    Moment("first_steps", (0.8, 1.6), lambda p, F: 0.18, ["takes his first wobbly steps into {parent}'s arms"], 0.8,
           {"motor": 0.03}, once=True),
    Moment("first_word", (0.8, 1.8), lambda p, F: 0.15 * (0.6 + F["household_speech"]), ["says his first word"], 0.7,
           once=True),
    Moment("separation", (0.6, 2.5), lambda p, F: 0.12, ["screams when {parent} leaves the room",
           "clings to {parent} at the nursery door"], -0.4, {"anxiety": 0.01}),
    Moment("teething", (0.4, 2), lambda p, F: 0.08, ["is up all night teething"], -0.3),
    Moment("tantrum", (1.5, 4.5), lambda p, F: 0.15, ["has a tantrum on the supermarket floor",
           "melts down because his toast was cut wrong"], -0.3),
    # --- childhood -------------------------------------------------------------------------------------------------
    Moment("reads", (4.5, 7.5), lambda p, F: 0.05 * (0.5 + F["parent_education"]), ["reads a whole book by himself"],
           0.7, {"academic": 0.02}, once=True),
    Moment("bike", (4, 8.5), lambda p, F: 0.035, ["rides a bike without stabilisers; {parent} lets go and he keeps going"],
           0.8, {"motor": 0.03, "resilience": 0.01}, once=True),
    Moment("tooth", (5.5, 7.5), lambda p, F: 0.06, ["loses his first tooth and finds a coin under his pillow"], 0.6,
           once=True),
    Moment("best_friend", (4, 11), lambda p, F: 0.03 * (_nfriends(p) > 0), ["decides {friend} is his best friend forever"],
           0.8, {"peer_isolation": -0.03}, {"oxytocin": 0.05}, once=True),
    Moment("nightmare", (3, 9), lambda p, F: 0.04, ["wakes from a nightmare and runs to {parent}'s bed",
           "is scared of what lives under the bed"], -0.3),
    Moment("picked_last", (6, 14), lambda p, F: 0.035 * (1.3 - p.s["motor"]), ["is picked last for the team again"], -0.5,
           {"school_belonging": -0.02}),
    Moment("not_invited", (6, 14), lambda p, F: 0.03 * (0.2 + p.s["peer_isolation"]),
           ["is the only one in class not invited to a birthday party"], -0.6, {"peer_isolation": 0.02}),
    Moment("sleepover", (7, 13), lambda p, F: 0.03 * (_nfriends(p) > 0), ["has his first sleepover at {friend}'s; they talk till 2am"],
           0.7, chem={"oxytocin": 0.04}, once=True),
    Moment("snow_day", (3, 14), lambda p, F: 0.03, ["gets a snow day: no school, sledging all morning",
           "spends a whole summer day at the beach"], 0.7, chem={"endorphins": 0.05}),
    Moment("lost_toy", (3, 8), lambda p, F: 0.025, ["loses his favourite toy and is inconsolable"], -0.4),
    Moment("parents_fight", (3, 18), lambda p, F: 0.08 * p.s["household_friction"],
           ["lies awake listening to his parents argue downstairs"], -0.6, {"anxiety": 0.02, "attachment": -0.01}),
    Moment("prize", (6, 18), lambda p, F: 0.015 * (0.3 + p.s["academic"] + p.s["motor"]),
           ["wins a prize at school and can't stop smiling", "scores the winning goal"], 0.8, {"resilience": 0.01},
           {"dopamine": 0.08}),
    # --- adolescence -----------------------------------------------------------------------------------------------
    Moment("crush", (10, 15), lambda p, F: 0.035, ["has his first crush and can't think about anything else"], 0.5,
           chem={"dopamine": 0.06}, once=True),
    Moment("first_kiss", (13, 20), lambda p, F: 0.015 * (0.5 + p.s["extraversion"]), ["has his first kiss"], 0.8,
           chem={"dopamine": 0.1, "oxytocin": 0.05}, once=True),
    Moment("heartbreak", (14, 23), lambda p, F: 0.01, ["has his heart broken for the first time; it feels like the end of the world"],
           -0.8, {"loneliness": 0.05, "anxiety": 0.03}, once=True),
    Moment("unrequited", (12, 22), lambda p, F: 0.008, ["likes someone who does not like him back"], -0.5),
    Moment("mirror", (12, 19), lambda p, F: 0.03 * (0.5 + p.s["neuroticism"]) * (1 + p.online.comparison),
           ["hates what he sees in the mirror: spots, height, everything", "won't take his shirt off at the pool"], -0.5,
           {"anxiety": 0.01}),
    Moment("concert", (13, 22), lambda p, F: 0.012 * (0.4 + p.s["wealth"]), ["goes to his first concert and screams every word"],
           0.9, chem={"endorphins": 0.08, "dopamine": 0.06}, once=True),
    Moment("licence", (17, 21), lambda p, F: 0.05 * (0.4 + p.s["wealth"]) * (0.4 + F["low_walkability"]),
           ["passes his driving test; the road is his"], 0.8, {"autonomy": 0.05}, once=True),
    Moment("first_wage", (15, 20), lambda p, F: 0.02, ["gets his first part-time job and his first pay packet"], 0.6,
           {"autonomy": 0.03}, once=True),
    Moment("first_drunk", (14, 20), lambda p, F: 0.012 * (0.2 + p.s["peer_risk"]) * (1 - F["cultural_strictness"]),
           ["gets drunk for the first time and is sick in a bush"], -0.1, once=True),
    Moment("misunderstood", (13, 18), lambda p, F: 0.035, ["feels like no one at home understands him at all"], -0.4,
           {"household_friction": 0.01}),
    Moment("who_am_i", (14, 23), lambda p, F: 0.015 * (0.5 + p.s["openness"]),
           ["lies awake wondering who he really is and what the point of any of it is"], -0.2),
    Moment("inside_jokes", (12, 22), lambda p, F: 0.04 * (_nfriends(p) >= 2), ["laughs at an inside joke with his friends that no one else gets"],
           0.7, {"peer_isolation": -0.01}, {"endorphins": 0.05}),
    Moment("pressure", (13, 19), lambda p, F: 0.03 * p.s["peer_risk"], ["is pushed by friends to do something he doesn't want to"],
           -0.3, {"anxiety": 0.01}),
    # --- early adulthood -------------------------------------------------------------------------------------------
    Moment("payday", (18, 27), lambda p, F: 0.1 * p.s["employed"], ["gets his first real pay cheque and stares at it"], 0.7,
           {"autonomy": 0.02}, once=True),
    Moment("solo_trip", (19, 35), lambda p, F: 0.005 * (p.s["openness"] + p.s["wealth"]),
           ["travels alone for the first time and finds out he can"], 0.9, {"resilience": 0.02}, {"dopamine": 0.1}, once=True),
    Moment("behind", (24, 34), lambda p, F: 0.015 * (1.5 - 0.5 * p.s["employed"] - 0.5 * _partner(p)) * (1 + p.online.comparison),
           ["scrolls past old classmates' weddings and promotions and feels hopelessly behind",
            "wonders whether everyone else got a manual for adulthood that he missed"], -0.5,
           {"identity_crisis": 0.03, "goal_horizon": -0.02}),
    Moment("alone_city", (19, 35), lambda p, F: 0.02 * p.s["felt_loneliness"],
           ["eats dinner alone again in a city where no one knows his name"], -0.5, {"loneliness": 0.02}),
    Moment("drift", (25, 45), lambda p, F: 0.01 * (_nfriends(p) > 0),
           ["realises he hasn't seen {friend} in a year; life just got in the way"], -0.4, {"community_support": -0.02}),
    Moment("single_wedding", (25, 40), lambda p, F: 0.01 * (not _partner(p)), ["goes to another friend's wedding on his own"],
           -0.3, {"loneliness": 0.01}),
    Moment("impostor", (22, 45), lambda p, F: 0.012 * p.s["employed"] * (0.3 + p.s["neuroticism"]),
           ["is sure that any day now someone will find out he has no idea what he is doing"], -0.4, {"anxiety": 0.015}),
    Moment("his_people", (18, 40), lambda p, F: 0.005 * (0.4 + p.s["extraversion"]),
           ["finds his people: a group where he can be completely himself"], 0.9, {"community_support": 0.05},
           {"oxytocin": 0.06}, once=True),
    Moment("ghosted", (18, 45), lambda p, F: 0.01 * (not _partner(p)), ["is ghosted after three great dates"], -0.4),
    Moment("swiping", (20, 50), lambda p, F: 0.01 * (not _partner(p)) * p.online.has_phone,
           ["swipes on dating apps for an hour and feels emptier than before"], -0.3),
    Moment("wedding", (22, 50), lambda p, F: 0.015 * any(p.age - x.joined > 18 for x in _present(p, "partner")),
           ["marries {partner}, surrounded by everyone they love"], 1.0, {"community_support": 0.03},
           {"oxytocin": 0.12, "dopamine": 0.1}, once=True),
    Moment("keys", (25, 55), lambda p, F: 0.006 * p.s["wealth"] * p.s["employed"] * (1 - F["housing_unaffordable"]),
           ["gets the keys to a home of his own and sits on the empty floor grinning"], 0.9, {"housing": 0.5}, once=True),
    Moment("bank_balance", (19, 45), lambda p, F: 0.02 * (1 - p.s["wealth"]) * (0.3 + F["student_debt"]),
           ["checks his bank balance before buying groceries", "lies awake doing sums about rent"], -0.4,
           {"financial_paranoia": 0.01, "anxiety": 0.01}),
    Moment("dream_job", (23, 50), lambda p, F: 0.004 * p.s["skill_value"] * p.s["employed"],
           ["is offered the job he always wanted"], 0.9, {"goal_horizon": 0.04}, {"dopamine": 0.12}, once=True),
    # --- middle adulthood ------------------------------------------------------------------------------------------
    Moment("is_this_it", (38, 56), lambda p, F: 0.012 * (1 + p.s["identity_crisis"]),
           ["sits in the car outside work and asks himself, 'is this it?'"], -0.5,
           {"identity_crisis": 0.03, "goal_horizon": -0.02}),
    Moment("body", (33, 65), lambda p, F: 0.02, ["hurts his back doing absolutely nothing", "finds his first grey hair",
           "needs reading glasses to read a menu", "is out of breath after one flight of stairs"], -0.2),
    Moment("scare", (38, 80), lambda p, F: 0.004 * (1.5 - p.s["health"]),
           ["finds a lump; two weeks of waiting for the scan. It's nothing, this time"], -0.6, {"anxiety": 0.04}),
    Moment("sandwich", (33, 62), lambda p, F: 0.05 * bool(_old_parent(p, 72)) * bool(_kids(p, 0, 216)),
           ["drives from the school run to {parent}'s hospital appointment and has nothing left for himself"], -0.4,
           {"allostatic_load": 0.008, "sleep": -0.02}),
    Moment("care_parent", (42, 75), lambda p, F: 0.02 * bool(_old_parent(p, 78)),
           ["helps {parent} with things they used to do for him", "sees {parent} looking small and old for the first time"],
           -0.3),
    Moment("passed_over", (38, 62), lambda p, F: 0.008 * p.s["employed"] * (p.work.level < 3),
           ["watches someone fifteen years younger get the promotion"], -0.5, {"identity_crisis": 0.02}),
    Moment("old_friend", (30, 90), lambda p, F: 0.004, ["hears from an old friend after years and they talk for hours"],
           0.8, {"loneliness": -0.02}, {"oxytocin": 0.05}),
    Moment("new_hobby", (32, 80), lambda p, F: 0.005 * (0.3 + p.s["openness"]),
           ["starts learning the piano just for the joy of it", "runs his first race at 45"], 0.7, {"goal_horizon": 0.02},
           {"dopamine": 0.08}),
    Moment("friends_split", (32, 60), lambda p, F: 0.006, ["helps a friend through a divorce and wonders about his own life"],
           -0.2),
    Moment("halfway", (44, 70), lambda p, F: 0.005, ["realises he has more years behind him than ahead"], -0.4,
           {"nihilism": 0.01}),
    Moment("thank_you", (45, 95), lambda p, F: 0.006 * bool(_kids(p, 240)),
           ["{child}, grown up now, thanks him for everything he did"], 1.0, chem={"oxytocin": 0.1}),
    # --- late adulthood --------------------------------------------------------------------------------------------
    Moment("hearing", (60, 100), lambda p, F: 0.003 * (p.years - 55) / 10,
           ["can no longer follow conversations in noisy rooms and gets hearing aids"], -0.3, {"social_isolation": 0.02},
           once=True),
    Moment("keys_away", (72, 100), lambda p, F: 0.004 * (1 + 3 * p.s["neurodegeneration"]),
           ["gives up his driving licence; the world gets smaller"], -0.6, {"autonomy": -0.1, "social_isolation": 0.05},
           once=True),
    Moment("fall", (70, 100), lambda p, F: 0.005 * (1.5 - p.s["motor"]),
           ["has a fall at home and lies on the floor a long time before anyone comes"], -0.7,
           {"anxiety": 0.04, "health": -0.02}),
    Moment("downsize", (65, 90), lambda p, F: 0.003, ["moves to a smaller place, packing a whole life into boxes"], -0.2,
           once=True),
    Moment("name_gone", (65, 100), lambda p, F: 0.01 * (0.5 + p.s["neurodegeneration"]),
           ["forgets the name of someone he has known for decades, and it frightens him"], -0.5, {"anxiety": 0.02}),
    Moment("peace", (60, 100), lambda p, F: 0.02, ["sits in the garden in the sun and feels, unexpectedly, at peace",
           "notices he worries less than he used to"], 0.8, {"anxiety": -0.02}, {"serotonin": 0.05}),
    Moment("stories", (60, 100), lambda p, F: 0.012 * (p.family.grandchildren > 0),
           ["tells his grandchildren a story from when he was young, and they beg for another"], 0.9, chem={"oxytocin": 0.08}),
    Moment("savings", (64, 95), lambda p, F: 0.01 * (1 - p.s["wealth"]),
           ["works out how long his savings will last, and it is not long enough"], -0.5, {"financial_paranoia": 0.02}),
    Moment("left_behind", (65, 100), lambda p, F: 0.01 * (1 - p.s["digital_literacy"]),
           ["cannot get the new banking app to work and feels the world has left him behind"], -0.4),
    Moment("silent_week", (70, 100), lambda p, F: 0.015 * p.s["social_isolation"],
           ["goes a whole week without speaking to anyone"], -0.6, {"loneliness": 0.02}),
    Moment("legacy", (65, 100), lambda p, F: 0.003, ["writes down the things he wants his family to know"], 0.5, once=True),
    # --- more of each age (LIFE_SEASONS.md) -------------------------------------------------------------------------
    Moment("colic", (0.03, 0.3), lambda p, F: 0.25, ["screams every evening for hours with colic while {parent} paces the hall"],
           -0.4, once=True),
    Moment("first_food", (0.45, 0.7), lambda p, F: 0.4, ["tries mashed banana and pulls a face, then opens his mouth for more"],
           0.6, once=True),
    Moment("peekaboo", (0.4, 1.2), lambda p, F: 0.15, ["shrieks with laughter at peekaboo"], 0.7, chem={"endorphins": 0.04}),
    Moment("potty", (2, 3.5), lambda p, F: 0.1, ["uses the potty by himself and is wildly proud"], 0.7, once=True),
    Moment("dethroned", (1.5, 6), lambda p, F: 0.2 * any(0 <= p.age - x.born < 3 for x in _present(p, "sibling")),
           ["is jealous of the new baby and wants to be carried again"], -0.4, {"attachment": -0.01}, once=True),
    Moment("why", (2.5, 5), lambda p, F: 0.04, ["asks 'why?' forty times in a row"], 0.3),
    Moment("first_death_talk", (4, 8), lambda p, F: 0.01, ["asks {parent} whether everyone dies, and whether they will too"],
           -0.3, once=True),
    Moment("glasses", (5, 14), lambda p, F: 0.006 * (1 + F["screen_time"]), ["gets glasses and is teased about them for a week"],
           -0.2, once=True),
    Moment("braces", (10, 15), lambda p, F: 0.02 * (0.3 + p.s["wealth"]), ["gets braces and can't eat anything chewy"], -0.2,
           once=True),
    Moment("dyslexia", (6, 10), lambda p, F: 0.005 * F["healthcare_access"], ["is found to be dyslexic, which explains a lot"],
           0.0, {"academic": -0.02}, once=True),
    Moment("climate_fear", (8, 25), lambda p, F: 0.01 * F["crisis_news"], ["lies awake worrying the world is ending"], -0.4,
           {"nihilism": 0.01}),
    Moment("collection", (6, 12), lambda p, F: 0.01, ["finishes his sticker album at last"], 0.7, once=True),
    Moment("den", (6, 12), lambda p, F: 0.02 * (_nfriends(p) > 0), ["builds a den in the woods with {friend}"], 0.7),
    Moment("residential", (9, 12), lambda p, F: 0.03, ["goes on his first school trip away from home and is homesick the first night"],
           0.4, once=True),
    Moment("taller", (13, 17), lambda p, F: 0.02 * (F["sex"] >= 0.5), ["realises he is taller than his mother now"], 0.5,
           once=True),
    Moment("private", (12, 16), lambda p, F: 0.02, ["puts a 'keep out' sign on his bedroom door"], 0.1, once=True),
    Moment("prom", (16, 18.5), lambda p, F: 0.05 * (0.3 + p.s["extraversion"]), ["dances badly at his school prom and doesn't care"],
           0.8, once=True),
    Moment("rejected_uni", (19, 19.3), lambda p, F: 0.5 * any("exam result" in w for w in p.school.why),
           ["opens a rejection letter from the place he wanted most"], -0.6, once=True),
    Moment("homesick", (18, 20), lambda p, F: 0.1 * (p.s["schooling"] > 0.5), ["cries on the phone to {parent} in his first term away"],
           -0.4, once=True),
    Moment("laundry", (18, 22), lambda p, F: 0.04, ["turns all his white shirts pink in the wash"], -0.1, once=True),
    Moment("first_funeral", (18, 30), lambda p, F: 0.006, ["goes to his first funeral as an adult and doesn't know what to say"],
           -0.4, once=True),
    Moment("flatmates", (19, 30), lambda p, F: 0.02 * (p.s["housing"] < 0.5), ["has a passive-aggressive note war with a flatmate over the washing-up"],
           -0.2),
    Moment("hangover_two_days", (28, 38), lambda p, F: 0.02, ["realises a hangover now lasts two days"], -0.1, once=True),
    Moment("when_kids", (26, 40), lambda p, F: 0.015 * (not _kids(p)) * (0.5 + F["cultural_strictness"]),
           ["is asked 'so when are you having kids?' at another family dinner"], -0.3),
    Moment("childcare_bill", (25, 45), lambda p, F: 0.03 * bool(_kids(p, 0, 60)), ["stares at the childcare bill: more than the rent"],
           -0.4, {"financial_paranoia": 0.01}),
    Moment("school_play", (30, 55), lambda p, F: 0.02 * bool(_kids(p, 48, 144)), ["watches {child} as a sheep in the school play and cries"],
           0.9, chem={"oxytocin": 0.06}),
    Moment("teen_eyeroll", (38, 60), lambda p, F: 0.03 * bool(_kids(p, 156, 216)), ["gets an eye-roll from {child} for existing"],
           -0.1),
    Moment("taller_child", (40, 60), lambda p, F: 0.02 * bool(_kids(p, 168, 216)), ["is overtaken in height by {child}"], 0.4,
           once=True),
    Moment("redundant", (45, 64), lambda p, F: 0.002 * p.s["employed"] * (1.5 - F["workplace_security"]),
           ["is made redundant after twenty years and told 'it's not personal'"], -0.8, {"identity_crisis": 0.06}),
    Moment("dinner_party", (28, 70), lambda p, F: 0.01 * (_nfriends(p) > 0), ["hosts a dinner where everyone stays far too late"],
           0.8, chem={"oxytocin": 0.04}),
    Moment("affair", (30, 60), lambda p, F: 0.0008 * _partner(p) * (0.5 + p.s["peer_risk"]) * (1.5 - p.s["agreeableness"]),
           ["has an affair and lies about it"], -0.5, {"anxiety": 0.04}, once=True),
    Moment("grey_divorce", (50, 70), lambda p, F: 0.0006 * _partner(p), ["decides with {partner} to separate after decades together"],
           -0.7, {"loneliness": 0.06, "identity_crisis": 0.05}, once=True),
    Moment("orphaned", (30, 80), lambda p, F: 0.3 * (not _present(p, "mother") and not _present(p, "father")),
           ["realises there is no one left who knew him as a baby: both his parents are gone"], -0.5, once=True),
    Moment("oldest_generation", (50, 85), lambda p, F: 0.02 * (not _present(p, "mother") and not _present(p, "father")),
           ["notices he is the oldest generation now at family gatherings"], -0.2, once=True),
    Moment("pills", (65, 100), lambda p, F: 0.02 * (len(p.illness.active) >= 3), ["sorts out his weekly pill organiser: nine tablets a day"],
           -0.2, once=True),
    Moment("elderspeak", (75, 100), lambda p, F: 0.01, ["is spoken to like a child by a receptionist"], -0.4),
    Moment("care_home", (78, 100), lambda p, F: 0.003 * (1 + 3 * p.s["neurodegeneration"]) * (p.s["autonomy"] < 0.4),
           ["moves into a care home with one suitcase and a photo of his family"], -0.7, {"autonomy": -0.1}, once=True),
    Moment("elder_abuse", (65, 100), lambda p, F: 0.0015 * (0.5 + p.s["neurodegeneration"]) * (1 - p.s["community_support"]),
           ["finds out someone he trusted has been taking his money"], -0.8, {"wealth": -0.05, "financial_paranoia": 0.1}),
    Moment("great_grandchild", (70, 100), lambda p, F: 0.002 * (p.family.grandchildren > 0),
           ["holds his great-grandchild, four generations in one room"], 1.0, chem={"oxytocin": 0.12}, once=True),
    Moment("old_song", (70, 105), lambda p, F: 0.02, ["hears a song from his youth and knows every word"], 0.8,
           chem={"dopamine": 0.04}),
    Moment("asked_past", (75, 105), lambda p, F: 0.01, ["is asked about the old days by someone who really wants to know"], 0.8),
    Moment("last_of_them", (85, 110), lambda p, F: 0.01, ["realises there is no one left alive who remembers his childhood"],
           -0.5, once=True),
    Moment("sleep_regression", (0.3, 1.0), lambda p, F: 0.12, ["was sleeping through, and now wakes every two hours again"],
           -0.3, once=True),
    Moment("stranger", (0.6, 1.5), lambda p, F: 0.1, ["howls when a stranger tries to hold him"], -0.2, once=True),
    Moment("nursery", (0.8, 3.5), lambda p, F: 0.05 * (p.s["employed"] >= 0) * (0.3 + F["ses"]),
           ["starts nursery: tears at the door, a painting at pick-up"], -0.1, once=True),
    Moment("late_talker", (1.8, 3), lambda p, F: 0.04 * (1.2 - F["household_speech"]), ["is slow to start talking, and his parents worry"],
           -0.2, once=True),
    Moment("biting", (1.2, 3), lambda p, F: 0.03, ["bites another child at nursery"], -0.2, once=True),
    Moment("bedtime", (2, 7), lambda p, F: 0.06, ["negotiates one more story, one more drink, one more song"], 0.1),
    Moment("bedwetting", (4, 8), lambda p, F: 0.02 * (0.5 + p.s["anxiety"]), ["wets the bed and hides the sheets"], -0.3),
    Moment("imaginary_friend", (3, 7), lambda p, F: 0.02 * (0.3 + p.s["openness"]), ["has an imaginary friend who needs a place set at dinner"],
           0.5, once=True),
    Moment("first_lie", (3, 5), lambda p, F: 0.05, ["tells his first lie, with chocolate all over his face"], 0.1, once=True),
    Moment("pocket_money", (6, 11), lambda p, F: 0.03, ["saves his pocket money for weeks to buy something himself"], 0.7,
           once=True),
    Moment("walks_alone", (8, 12), lambda p, F: 0.03 * F["neighbourhood_safety"], ["walks to school on his own for the first time"],
           0.6, {"autonomy": 0.02}, once=True),
    Moment("hero", (7, 13), lambda p, F: 0.02, ["has a hero whose poster goes up on his wall"], 0.5, once=True),
    Moment("times_tables", (7, 11), lambda p, F: 0.03 * (1.2 - p.s["academic"]), ["dreads the times-tables test"], -0.3),
    Moment("parent_die_fear", (6, 12), lambda p, F: 0.01 * (0.5 + p.s["anxiety"]), ["is suddenly terrified that {parent} might die"],
           -0.4),
    Moment("watched", (12, 16), lambda p, F: 0.03 * (0.5 + p.s["neuroticism"]), ["is sure everyone in the room is looking at him"],
           -0.3),
    Moment("first_sex", (15, 22), lambda p, F: 0.04 * (0.4 + p.s["extraversion"]) * (1.2 - F["cultural_strictness"]),
           ["has sex for the first time, nervous and clumsy"], 0.5, chem={"oxytocin": 0.06}, once=True),
    Moment("pregnancy_scare", (15, 25), lambda p, F: 0.004 * (0.5 + p.s["peer_risk"]), ["has a pregnancy scare and a week of panic"],
           -0.5, {"anxiety": 0.03}, once=True),
    Moment("fake_id", (16, 18), lambda p, F: 0.01 * p.s["peer_risk"] * (1 - F["cultural_strictness"]), ["gets into a club with a fake ID"],
           0.4, once=True),
    Moment("house_party", (16, 26), lambda p, F: 0.02 * (_nfriends(p) > 0) * (0.4 + p.s["extraversion"]), ["goes to a house party that ends at sunrise"],
           0.7, chem={"endorphins": 0.04}),
    Moment("credit_card", (18, 25), lambda p, F: 0.02, ["gets his first credit card, and his first credit card bill"], -0.1,
           once=True),
    Moment("moving_in", (20, 45), lambda p, F: 0.02 * any(p.age - x.joined > 10 for x in _present(p, "partner")),
           ["moves in with {partner}; they argue about how to load the dishwasher"], 0.7, once=True),
    Moment("long_distance", (18, 22), lambda p, F: 0.01 * (p.s["schooling"] > 0.5), ["breaks up with his school sweetheart by Christmas of the first year away"],
           -0.5, once=True),
    Moment("wedding_season", (26, 36), lambda p, F: 0.01, ["spends a month's pay on other people's weddings this summer"], -0.1),
    Moment("housework", (25, 60), lambda p, F: 0.02 * _partner(p) * bool(_kids(p, 0, 216)), ["argues with {partner} about who does more around the house"],
           -0.3),
    Moment("school_chat", (30, 55), lambda p, F: 0.02 * bool(_kids(p, 48, 132)), ["mutes the school parents' group chat after 200 messages about a lost jumper"],
           -0.1),
    Moment("boiler", (25, 90), lambda p, F: 0.004 * (p.s["housing"] > 0.5), ["the boiler breaks in January"], -0.3),
    Moment("will", (35, 80), lambda p, F: 0.004 * bool(_kids(p)), ["writes his will and chooses who would raise his children"],
           -0.1, once=True),
    Moment("ed", (42, 75), lambda p, F: 0.003 * _male(F) * (1 + p.illness.burden_now * 3), ["finds his body doesn't respond the way it used to in bed"],
           -0.3, once=True),
    Moment("screening", (45, 60), lambda p, F: 0.03 * F["healthcare_access"], ["has his first cancer screening and spends the morning nervous"],
           -0.1, once=True),
    Moment("reunion", (35, 70), lambda p, F: 0.003, ["goes to a school reunion and finds the popular kids are just people now"],
           0.5, once=True),
    Moment("overqualified", (50, 66), lambda p, F: 0.006 * (p.s["employed"] < 0.5), ["is told he is 'overqualified' for the fifth time"],
           -0.5),
    Moment("pension_plan", (55, 66), lambda p, F: 0.02, ["sits down with his pension statements and does the sums for the first time"],
           -0.1, once=True),
    Moment("senior_discount", (60, 70), lambda p, F: 0.03, ["gets his first senior discount without being asked"], 0.2, once=True),
    Moment("clearing_home", (35, 80), lambda p, F: 0.4 * any(x.relation in ("mother", "father") and x.died is not None
                                                                and 0 < p.age - x.died < 6 for x in p.family.people),
           ["clears out his parents' house, one box of memories at a time"], -0.5, once=True),
    Moment("allotment", (55, 90), lambda p, F: 0.006, ["grows his first tomatoes and is ridiculously proud"], 0.7),
    Moment("video_call", (62, 100), lambda p, F: 0.02 * (p.family.grandchildren > 0) * p.s["digital_literacy"],
           ["learns to video-call his grandchildren and waves too close to the camera"], 0.7, once=True),
    Moment("big_trip", (60, 80), lambda p, F: 0.006 * p.s["wealth"], ["takes the trip he always said he would"], 0.9,
           chem={"dopamine": 0.08}, once=True),
    Moment("volunteer", (60, 85), lambda p, F: 0.008 * (0.3 + p.s["agreeableness"]), ["starts volunteering and feels useful again"],
           0.7, {"identity_crisis": -0.03, "community_support": 0.03}, once=True),
    Moment("learns_late", (62, 90), lambda p, F: 0.005 * (0.3 + p.s["openness"]), ["starts learning a language at 70"], 0.7,
           once=True),
    Moment("stairlift", (78, 100), lambda p, F: 0.004 * (1.4 - p.s["motor"]), ["has a stairlift fitted and hates it, then loves it"],
           -0.1, once=True),
    Moment("meals_delivered", (80, 105), lambda p, F: 0.004 * (1 - p.s["autonomy"]), ["has hot meals delivered; the driver is the only person he sees some days"],
           -0.2, once=True),
    Moment("dementia_dx", (65, 100), lambda p, F: 0.05 * (p.s["neurodegeneration"] > 0.45), ["is told he has dementia, and asks the doctor to repeat it"],
           -0.9, once=True),
    Moment("hay_fever", (6, 50), lambda p, F: 0.03 * (p.chem.daylight(p.age) > 0.7) * (0.5 + p.s["autoimmune_risk"]),
           ["sneezes through every summer exam with hay fever"], -0.2),
    Moment("concussion", (8, 35), lambda p, F: 0.002 * (0.3 + p.s["motor"]), ["takes a knock to the head playing sport and is foggy for weeks"],
           -0.4),
    Moment("two_jobs", (19, 65), lambda p, F: 0.01 * (p.s["wealth"] < 0.15) * p.s["employed"], ["works two jobs and is still short at the end of the month"],
           -0.5, {"allostatic_load": 0.01}),
    Moment("court", (25, 80), lambda p, F: 0.0008, ["ends up in a legal fight with a landlord that drags on for months"], -0.4,
           {"anxiety": 0.03}),
    Moment("missing", (10, 90), lambda p, F: 0.0002, ["someone he knows goes missing and is never found"], -0.7,
           {"anxiety": 0.04}, once=True),
    Moment("national_team", (6, 95), lambda p, F: 0.003, ["watches his country win a big match and the whole street celebrates"],
           0.8, chem={"endorphins": 0.05}),
    # --- little joys and annoyances at any age ----------------------------------------------------------------------
    Moment("found_money", (6, 100), lambda p, F: 0.004, ["finds money in an old coat pocket"], 0.6),
    Moment("just_caught", (10, 100), lambda p, F: 0.006, ["catches the train with seconds to spare"], 0.4),
    Moment("first_warm_day", (4, 100), lambda p, F: 0.04 * (p.chem.daylight(p.age) > 0.6), ["sits outside on the first warm day of the year"],
           0.6, chem={"serotonin": 0.04}),
    Moment("first_snow", (3, 100), lambda p, F: 0.03 * (p.chem.daylight(p.age) < 0.2), ["wakes up to the first snow"], 0.5),
    Moment("stubbed_toe", (3, 100), lambda p, F: 0.01, ["stubs his toe on the bed in the dark"], -0.2),
    Moment("lost_keys", (12, 100), lambda p, F: 0.008, ["loses his keys and turns the house upside down"], -0.2),
    Moment("unexpected_bill", (19, 100), lambda p, F: 0.01, ["opens an unexpected bill"], -0.3),
    Moment("message", (12, 100), lambda p, F: 0.01, ["gets a message from someone he was just thinking about"], 0.6,
           chem={"oxytocin": 0.03}),
    Moment("forgotten_birthday", (10, 100), lambda p, F: 0.003, ["is forgotten on his birthday by someone who matters"], -0.5),
    Moment("good_book", (8, 100), lambda p, F: 0.01 * (0.3 + p.s["openness"]), ["stays up too late with a book he can't put down"],
           0.6),
    Moment("series_finale", (12, 90), lambda p, F: 0.006, ["watches the finale of a series he loved and feels oddly bereft"], 0.2),
    Moment("childhood_food", (15, 100), lambda p, F: 0.006, ["smells something cooking that takes him straight back to childhood"],
           0.6),
    Moment("team_wins", (6, 95), lambda p, F: 0.006, ["watches his team win in the last minute and hugs a stranger"], 0.8,
           chem={"endorphins": 0.06}),
    Moment("creation", (8, 95), lambda p, F: 0.006 * (0.3 + p.s["openness"]), ["finishes something he made himself: a song, a painting, a chair"],
           0.8, {"goal_horizon": 0.01}, {"dopamine": 0.06}),
    Moment("forgiven", (6, 100), lambda p, F: 0.003, ["is forgiven for something he thought he couldn't be"], 0.8),
    # --- any age ---------------------------------------------------------------------------------------------------
    Moment("flu", (3, 100), lambda p, F: 0.015, ["is in bed for a week with flu"], -0.3),
    Moment("broken_bone", (5, 70), lambda p, F: 0.002 * (1 + p.s["peer_risk"]), ["breaks his arm"], -0.5),
    Moment("stranger", (5, 100), lambda p, F: 0.008, ["a stranger is unexpectedly kind to him"], 0.6,
           chem={"oxytocin": 0.03}),
    Moment("mortified", (8, 60), lambda p, F: 0.008 * (0.5 + p.s["neuroticism"]),
           ["does something so embarrassing he replays it for years"], -0.3),
    Moment("robbed", (15, 95), lambda p, F: 0.002 * (1.4 - F["neighbourhood_safety"]),
           ["comes home to find he has been burgled", "has his phone snatched in the street"], -0.6, {"anxiety": 0.03}),
]

SCAMS = [  # (kind, ages, text, how much it costs, relative to age)
    ("parcel", (14, 100), "clicks a fake parcel-delivery text and gives away his card details", 0.01),
    ("job", (16, 35), "is taken in by a fake job offer that asks for an upfront fee", 0.02),
    ("crypto", (20, 75), "puts his savings into an 'investment' a stranger online swore by, and it vanishes", 0.12),
    ("romance", (30, 95), "sends money to someone he fell for online who never existed", 0.1),
    ("impostor", (25, 100), "pays a 'tax fine' to a caller pretending to be the government", 0.03),
    ("tech", (60, 100), "lets a 'tech support' caller into his computer and his bank account", 0.08),
    ("voice", (60, 100), "gets a panicked call in his grandchild's cloned voice and sends the money", 0.06),
]

YEARN = [  # (from, to, condition, what he yearns for)
    (3, 12, lambda p, F: True, "I want to be big, so I can do what I want."),
    (12, 19, lambda p, F: p.s["household_friction"] > 0.3, "I want to be free of this house."),
    (12, 19, lambda p, F: True, "I want someone to really understand me."),
    (19, 30, lambda p, F: not _partner(p), "I want someone to love who loves me back."),
    (19, 35, lambda p, F: p.s["employed"] < 0.5, "I want a job that means something."),
    (19, 35, lambda p, F: True, "I want to find where I belong."),
    (28, 45, lambda p, F: not _kids(p) and _partner(p), "I want a child of my own."),
    (30, 50, lambda p, F: p.s["housing"] < 0.5, "I want a home that is mine."),
    (35, 60, lambda p, F: p.work.hours > 48, "I want time. Just time."),
    (40, 60, lambda p, F: True, "I want it to have meant something."),
    (60, 100, lambda p, F: p.family.grandchildren > 0, "I want to see my grandchildren grow up."),
    (60, 100, lambda p, F: p.s["social_isolation"] > 0.4, "I want someone to talk to."),
    (60, 100, lambda p, F: True, "I want to be remembered kindly."),
]


class Seasons:
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 8123 + 37)
        self.done: set = set()
        self.recent: List[list] = []                   # [age, text, valence]
        self.regrets: Dict[str, dict] = {}             # key -> {kind, text, since, weight}
        self.testosterone = 0.0
        self.fatherhood_drop = 0.0
        self.postnatal_checked: set = set()
        self.empty_nest_at: Optional[int] = None
        self.scams = 0
        self.scam_lost = 0.0
        self.counts: Dict[str, int] = {}
        self.harms = 0
        self.shape = 0.0                               # how this season of life pulls on his mood

    # ------------------------------------------------------------------ for other modules
    def yearning(self, p, F) -> str:
        y = p.years
        for a, b, cond, text in YEARN:
            if a <= y < b and cond(p, F):
                return text
        return ""

    def regret_load(self) -> float:
        return clip(sum(r["weight"] for r in self.regrets.values()) / 3)

    def line(self, p, F) -> str:
        if p.years >= 30 and self.regrets and self.rng.random() < 0.35:
            r = max(self.regrets.values(), key=lambda x: x["weight"])
            return r["text"]
        return self.yearning(p, F)

    def to_json(self, p, F) -> dict:
        return {"recent": self.recent[-10:], "yearning": self.yearning(p, F),
                "regrets": sorted(({"kind": r["kind"], "text": r["text"], "since": r["since"], "weight": round(r["weight"], 2)}
                                   for r in self.regrets.values()), key=lambda r: -r["weight"])[:6],
                "testosterone": round(self.testosterone, 3), "fatherhood_drop": round(self.fatherhood_drop, 3),
                "scams": self.scams, "scam_lost": round(self.scam_lost, 3),
                "pregnancy_losses": getattr(p.family, "pregnancy_losses", 0),
                "empty_nest": None if self.empty_nest_at is None else round(self.empty_nest_at / 12, 1),
                "season": self.season(p.years)}

    @staticmethod
    def season(y: float) -> str:
        return ("infancy" if y < 3 else "childhood" if y < 12 else "adolescence" if y < 19 else
                "the twenties" if y < 30 else "the thirties" if y < 40 else "midlife" if y < 56 else
                "the sixties" if y < 70 else "old age")

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        fill = self._fill(p)
        # the catalogue
        for mo in MOMENTS:
            if not (mo.ages[0] <= y < mo.ages[1]) or (mo.once and mo.key in self.done):
                continue
            chance = mo.rate(p, F)
            if chance <= 0 or r.random() >= chance:
                continue
            text = r.choice(mo.texts)
            need = [k for k in ("friend", "partner", "parent", "child") if "{" + k + "}" in text]
            if any(fill.get(k) is None for k in need):
                continue
            if mo.once:
                self.done.add(mo.key)
            text = text.format(**{k: fill.get(k) or "" for k in ("friend", "partner", "parent", "child")})
            self._live(p, text, mo.valence, mo.key, mo.deltas, mo.chem, [fill[k] for k in need], out)
        out += self._birthday(p, F)
        out += self._parenthood(p, F)
        out += self._scam(p, F)
        out += self._teen_pregnancy(p, F)
        # the shape of a life, applied to his mood (character.py): a midlife dip and a gentler old age
        # (Blanchflower; Carstensen), and regret weighing more in the life review of old age. Recent surveys find
        # the young now the least happy of all (Blanchflower et al. 2024-25), which his twenties already show.
        if y >= 60:
            p.apply({"anxiety": -0.002}, fades=True)
        if m % 12 == 0 and y >= 22:
            self._regrets(p, F)
        dip = math.exp(-((y - 47.5) / 9) ** 2)
        late = clip((y - 60) / 15) * clip((85 - y) / 10)
        decline = clip((0.45 - s["health"]) / 0.3) * (y >= 60)          # wellbeing sinks in the last years of life
        self.shape = 0.06 * dip - 0.03 * late + 0.06 * self.regret_load() * clip((y - 50) / 20) + 0.08 * decline
        return out

    def _fill(self, p) -> Dict[str, Optional[str]]:
        par = _present(p, "mother") or _present(p, "father") or _present(p, "grandparent")
        old = _old_parent(p, 70)
        kid = _kids(p)
        part = _present(p, "partner")
        return {"friend": _friend(p), "partner": part[0].name if part else None,
                "parent": (old or par)[0].name if (old or par) else None, "child": kid[0].name if kid else None}

    def _live(self, p, text, valence, key, deltas, chem, who, out):
        if deltas:
            p.apply({k: v for k, v in deltas.items() if k in p.s}, fades=True)
        for k, v in (chem or {}).items():
            if k in p.chem.level:
                p.chem.level[k] = clip(p.chem.level[k] + v)
        self.counts[key] = self.counts.get(key, 0) + 1
        self.recent.append([round(p.years, 1), text, valence])
        self.recent = self.recent[-30:]
        out.append({"text": text, "valence": valence, "arousal": 0.3 + 0.5 * abs(valence), "who": who,
                    "key": "joy" if valence > 0 else "sorrow", "deltas": dict(deltas or {})})

    def _birthday(self, p, F) -> List[dict]:
        y, out = p.years, []
        if p.age % 12 or p.age < 36:
            return out
        a = int(round(y))
        text = {13: "turns thirteen: a teenager at last", 16: "turns sixteen", 18: "turns eighteen: officially an adult",
                21: "turns twenty-one", 30: "turns thirty and feels suddenly old", 40: "turns forty and takes stock",
                50: "turns fifty; his friends throw him a party", 60: "turns sixty", 70: "turns seventy",
                80: "turns eighty, with his family around him", 90: "turns ninety"}.get(a)
        if text is None and a < 12:
            text = f"has a birthday party with cake and {a} candles"
        if text:
            v = -0.1 if a in (30, 40) else 0.6
            self._live(p, text, v, "birthday", {}, {"dopamine": 0.05} if v > 0 else {}, [], out)
        return out

    def _parenthood(self, p, F) -> List[dict]:
        """Hormones after a birth, postnatal depression, and the empty nest."""
        r, s, y, m, out = self.rng, p.s, p.years, p.age, []
        male = _male(F)
        # testosterone: rises through puberty, falls slowly from 30, and falls a quarter to a third with fatherhood
        base = (0.1 + 0.7 * s["puberty"]) * (1 - max(0.0, y - 30) * 0.008) if male else 0.08 + 0.05 * s["puberty"]
        infants = _kids(p, 0, 36)
        care = clip((48 - p.work.hours) / 30) if s["employed"] > 0.5 else 1.0
        target = (0.26 + 0.1 * care) if (male and infants) else 0.0
        self.fatherhood_drop += 0.1 * (target - self.fatherhood_drop)
        self.testosterone = clip(base * (1 - self.fatherhood_drop))
        s["testosterone"] = round(self.testosterone, 4)
        if male and infants:
            p.chem.level["oxytocin"] = clip(p.chem.level["oxytocin"] + 0.03 * care)
        for k in _kids(p, 0, 12):
            if k.name in self.postnatal_checked:
                continue
            if m - k.born == 0:
                txt = ("holds {n} for the first time and something in him changes for good" if male else
                       "holds {n} for the first time; her body is wrecked and her heart is full").format(n=k.name)
                self._live(p, txt, 1.0, "newborn", {}, {"oxytocin": 0.15}, [k.name], out)
            if m - k.born == 4:
                self.postnatal_checked.add(k.name)
                risk = (0.104 if male else 0.13) * (0.55 + 0.6 * s["allostatic_load"] + 0.3 * p.mind.family_history)
                if r.random() < risk and p.mind.begin("depression", m):
                    txt = ("loves the baby, and still feels nothing but exhaustion and dread: postnatal depression in a"
                           " father, which no one asks him about" if male else
                           "sinks into postnatal depression; she loves the baby and cannot feel it")
                    self._live(p, txt, -0.8, "postnatal", {"anxiety": 0.05}, {}, [k.name], out)
        # the empty nest: the last child leaves home
        kids = _kids(p)
        if kids and self.empty_nest_at is None and all(m - k.born >= 216 for k in kids) \
                and any(m - k.born == 216 for k in kids):
            self.empty_nest_at = m
            lived_for = clip(0.3 + 0.4 * (p.work.hours < 35 or s["employed"] < 0.5) + 0.2 * (not _partner(p)))
            self._live(p, "stands in his youngest's empty room; the house is so quiet. Who is he now, if not a parent?",
                       -0.5, "empty_nest", {"identity_crisis": 0.1 * lived_for, "loneliness": 0.04}, {}, [], out)
        if self.empty_nest_at is not None and m - self.empty_nest_at == 9 and _partner(p):
            self._live(p, "rediscovers {0}: long dinners, no school runs, time again".format(self._fill(p)["partner"]),
                       0.7, "freedom", {"identity_crisis": -0.04}, {"oxytocin": 0.06}, [], out)
        return out

    def _scam(self, p, F) -> List[dict]:
        r, s, y, out = self.rng, p.s, p.years, []
        if y < 14:
            return out
        online = p.online.has_phone or y >= 60
        vuln = ((0.5 + F["ai_scams"]) * (1 - 0.6 * s["financial_paranoia"]) * (1 + 2.5 * s["neurodegeneration"])
                * (1.3 - 0.6 * s["digital_literacy"]) * (1 + s["felt_loneliness"]) * (1.0 if online else 0.4))
        if r.random() >= 0.0007 * vuln:
            return out
        kinds = [k for k in SCAMS if k[1][0] <= y < k[1][1]]
        if s["felt_loneliness"] < 0.3:
            kinds = [k for k in kinds if k[0] != "romance"] or kinds
        kind, _, text, cost = r.choice(kinds)
        old = 1 + max(0.0, y - 60) / 15                       # median losses rise with age (FTC)
        lost = min(s["wealth"], cost * old * (6 if r.random() < 0.05 else 1))   # 1 in 20 is ruinous
        s["wealth"] = clip(s["wealth"] - lost)
        self.scams += 1
        self.scam_lost += lost
        d = {"anxiety": 0.05, "financial_paranoia": 0.12, "community_support": -0.02}
        self._live(p, text + ("; he tells no one" if r.random() < 0.6 else ""), -0.7, "scam", d, {}, [], out)
        if lost > 0.1 and r.random() < 0.25:
            p.mind.begin("depression", p.age)
        return out

    def _teen_pregnancy(self, p, F) -> List[dict]:
        """Teen births per year: about 1.3% in the US, under 1% in Western Europe, about 10% in Sub-Saharan Africa."""
        y, out = p.years, []
        if _male(F) or not 15 <= y < 19 or p.family.expecting is not None or "teen_pregnancy" in self.done:
            return out
        rate = {"Sub-Saharan Africa": 0.1, "Latin America": 0.06, "South Asia": 0.03, "Southeast Asia": 0.04,
                "Middle East and North Africa": 0.04, "North America": 0.013, "Oceania": 0.01, "Eastern Europe": 0.02,
                "Western Europe": 0.006, "Nordic countries": 0.004, "East Asia": 0.003}.get(p.school.region, 0.02)
        if self.rng.random() < rate / 12 * (0.5 + p.s["peer_risk"]) * (1.3 - F["cultural_strictness"] * 0.6):
            self.done.add("teen_pregnancy")
            p.family.expecting = p.age + 8
            self._live(p, "finds out she is pregnant at {0}".format(int(y)), -0.3, "teen_pregnancy",
                       {"anxiety": 0.06, "goal_horizon": -0.03}, {}, [], out)
        return out

    # ------------------------------------------------------------------ regret
    def _regrets(self, p, F) -> None:
        """Once a year he looks back. Inaction regrets grow with time; action regrets fade (Gilovich & Medvec)."""
        s, y = p.s, p.years
        found: Dict[str, tuple] = {}
        sc = p.school
        if sc.wanted and sc.course != sc.wanted and y >= 25:
            found["study"] = ("boldness", f"I wish I had fought to study {sc.wanted}.")
        if s["wealth"] < 0.2 and y >= 40:
            found["money"] = ("foundation", "I wish I had saved when I could.")
        if s["health"] < 0.55 and y >= 40:
            found["health"] = ("foundation", "I wish I had looked after my body.")
        if p.prejudice.closeted and y >= 30:
            found["true_self"] = ("boldness", "I wish I had had the courage to live as myself.")
        if "solo_trip" not in self.done and s["openness"] > 0.55 and y >= 40:
            found["world"] = ("boldness", "I wish I had seen more of the world.")
        for b in p.bonds.bonds.values():
            if b.pattern == "estranged" and y >= 30:
                found["rift_" + b.name] = ("connection", f"I wish I had made things right with {b.name}.")
        if self.counts.get("drift", 0) >= 2:
            found["friends"] = ("connection", "I wish I had stayed in touch with my friends.")
        if p.work.hours > 50 and _kids(p, 0, 144):
            found["kids_small"] = ("connection", "I wish I had been there more when my kids were little.")
        if p.conscious.last_harm and (p.prejudice.acted or p.conscious.guilt > 0.2):
            found["harm"] = ("moral", "I wish I had been kinder to people who did not deserve what I did.")
        for k, (kind, text) in found.items():
            r = self.regrets.setdefault(k, {"kind": kind, "text": text, "since": round(y), "weight": 0.2})
            r["weight"] = clip(r["weight"] + (0.05 if kind != "moral" else 0.02))      # inaction grows
        for k, r in list(self.regrets.items()):
            if k not in found:
                r["weight"] *= 0.7                                                       # mended, or let go
                if r["weight"] < 0.05:
                    del self.regrets[k]
