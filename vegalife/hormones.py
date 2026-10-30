"""His hormones and body across the whole life course: what changes, when, and what it does to him.

  infancy       mini-puberty: a surge of testosterone in boys and estrogen in girls at 1-6 months; the cortisol day-night
                rhythm and his own melatonin arrive at about 3 months, which is when sleep starts to consolidate
  adrenarche    from about 6-8 DHEA rises: body odour, oily skin, some moodiness, the quiet start of puberty
  puberty       the timing is his own (world.py: earlier with endocrine disruptors, later in boys). A growth spurt peaks
                at about 8-10 cm a year; first periods about 1.5-2.5 years after breasts start to develop (average age
                about 12.4 in the US), voices break, the first shave. Early puberty in girls raises the risk of
                depression and anxiety; late puberty in boys brings teasing about height
  teen sleep    melatonin is released about 2 hours later in adolescence while school starts early: chronic social
                jetlag. Reward sensitivity (dopamine) peaks in the mid-teens, more so with friends watching, and
                social-evaluative cortisol reactions rise
  height, bone  he grows to an adult height set by his genes and childhood nutrition; bone mass peaks around 30, then
  and muscle    falls about 0.5% a year, about 2% a year for the first years after menopause; muscle falls about 1% a
                year after 50 unless he keeps using it; he shrinks about 1 cm a decade after 50
  cycles        (if female) a monthly cycle: about 30% have premenstrual symptoms and about 5% PMDD, about 15% severe
                period pain. Pregnancy: morning sickness in about 70%, the 'baby blues' in up to 80% of mothers in
                the first two weeks, breastfeeding raising oxytocin and prolactin
  menopause     perimenopause for about 4-8 years, average menopause at 51; hot flushes in about 75%, lasting a median
                of about 7 years (SWAN); sleep, anxiety and brain fog; bone and heart risk afterwards; HRT eases it
  men           testosterone falls about 1% a year from 30-40 and free testosterone faster; symptomatic low
                testosterone in a few percent of older men (low energy and mood); a father's sympathetic pregnancy
                symptoms (couvade) in a minority
  love          the first 1-2 years of a relationship carry a dopamine high; after, an oxytocin-based attachment
  seasons       seasonal affective disorder in about 5% where winters are dark (more at high latitudes, women about 3x)
  old age       melatonin falls and his body clock moves earlier: early nights, early mornings, broken sleep; DHEA is
                about a fifth of its peak by 70; fewer dopamine receptors (about 10% a decade) mean new things lift
                him less, while calm and contentment often rise

What it changes elsewhere: his sleep (character.py), his mood (character.py), how much a reward lifts him
(chemistry.py), his bones (illness.py: osteoporosis), anxiety and depression risk (mental.py). Its own random
generator.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from .factors import FactorSet

LATITUDE = {"Nordic countries": 0.9, "Eastern Europe": 0.65, "Western Europe": 0.6, "North America": 0.5,
            "East Asia": 0.45, "Oceania": 0.35, "Middle East and North Africa": 0.25, "Latin America": 0.2,
            "South Asia": 0.2, "Southeast Asia": 0.05, "Sub-Saharan Africa": 0.05}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def smooth(t: float) -> float:
    t = clip(t)
    return t * t * (3 - 2 * t)


class Hormones:
    def __init__(self, F: FactorSet, seed: int, region: str = "North America"):
        self.rng = random.Random(seed * 6971 + 19)
        r = self.rng
        self.male = F["sex"] >= 0.5
        self.target_height = r.gauss(176 if self.male else 163, 7 if self.male else 6.5) + 3 * (F["ses"] - 0.5)
        self.height = 50.0
        self.menarche: Optional[float] = None
        self.menopause_age = clip(r.gauss(51 - 0.6 * (0.5 - F["ses"]), 3.5), 40, 58)
        self.flushes = r.random() < 0.75
        self.flush_years = clip(r.gauss(7.4, 3), 1, 15)
        self.pms = 0.0 if self.male else (0.08 if r.random() < 0.05 else 0.03 if r.random() < 0.3 else 0.0)
        self.cramps = (not self.male) and r.random() < 0.15
        self.sad = r.random() < 0.06 * LATITUDE.get(region, 0.4) * (1.6 if not self.male else 0.6)
        self.hrt = False
        self.low_t = False
        self.done: set = set()
        self.recent: List[list] = []
        self.levels: Dict[str, float] = {}
        self.sleep_now = 0.0
        self.mood_drag = 0.0
        self.chronotype = 23.0                      # the hour he naturally falls asleep
        self.onset: Optional[float] = None

    # ------------------------------------------------------------------ for other modules
    def dopamine_gain(self, y: float) -> float:
        """How much a reward lifts him: highest in the mid-teens, falling about 10% a decade after 40."""
        teen = 0.3 * math.exp(-((y - 15.5) / 3.5) ** 2)
        return clip(1.0 + teen - 0.01 * max(0.0, y - 40), 0.45, 1.4)

    def line(self) -> str:
        if self.sleep_now > 0.12 and 13 <= self.age_y < 22:
            return "I can't fall asleep before midnight and school starts so early."
        if "hot flushes" in self.active_now:
            return "I wake up soaked at night and can't think straight in the day."
        if "winter" in self.active_now:
            return "These dark months drag me down every year."
        if "pms" in self.active_now:
            return "Everything feels heavier this week, and I know why."
        if "new love" in self.active_now:
            return "I can't stop thinking about them."
        return ""

    def to_json(self) -> dict:
        return {"levels": {k: round(v, 3) for k, v in self.levels.items()}, "height_cm": round(self.height, 1),
                "menarche": None if self.menarche is None else round(self.menarche, 1),
                "menopause_age": None if self.male else round(self.menopause_age, 1), "hrt": self.hrt,
                "low_t": self.low_t, "sad": self.sad, "chronotype": round(self.chronotype, 1),
                "sleep_cost": round(self.sleep_now, 3), "mood_drag": round(self.mood_drag, 3),
                "now": sorted(self.active_now), "recent": self.recent[-8:],
                "puberty_onset": None if self.onset is None else round(self.onset, 1)}

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        self.age_y = y
        out: List[dict] = []
        now: set = set()
        sleep = drag = 0.0
        male = self.male
        if s["puberty"] > 0 and self.onset is None:
            self.onset = y
        onset = self.onset if self.onset is not None else 11.8 + 0.8 * male - 2.2 * F["endocrine_disruptors"]
        L = self.levels
        # --- sex hormones ---------------------------------------------------------------------------------------
        mini = 0.35 * math.exp(-((y - 0.25) / 0.15) ** 2)        # mini-puberty
        L["DHEA"] = clip(0.05 + 0.6 * smooth((y - 6) / 14) - 0.012 * max(0.0, y - 25))
        if male:
            L["testosterone"] = max(mini, getattr(p.seasons, "testosterone", 0.0))
            L["estrogen"] = 0.05
        else:
            meno = y >= self.menopause_age
            peri = self.menopause_age - 5 <= y < self.menopause_age
            base = 0.1 + 0.9 * s["puberty"]
            if peri:
                base *= 0.6 + 0.4 * r.random()                    # erratic: high some months, low others
            if meno:
                base = 0.12
            L["estrogen"] = max(mini, clip(base))
            L["testosterone"] = 0.08 + 0.05 * s["puberty"]
        L["growth hormone"] = clip(0.5 + 0.4 * math.exp(-((y - onset - 1.5) / 2) ** 2) - 0.008 * max(0.0, y - 25))
        L["melatonin"] = clip(1.0 - 0.012 * max(0.0, y - 20)) if y > 0.25 else 0.2
        L["cortisol reactivity"] = clip(0.45 + 0.25 * math.exp(-((y - 15) / 3) ** 2) + 0.2 * s["allostatic_load"])
        L["dopamine gain"] = self.dopamine_gain(y) / 1.4
        L["insulin sensitivity"] = clip(1 - s["insulin_resistance"])
        L["prolactin"] = 0.15                                    # raised again below while feeding a baby
        # --- infancy: rhythms arrive ------------------------------------------------------------------------------
        if y < 0.25:
            sleep += 0.15                                        # no melatonin of his own yet
        # --- adrenarche -------------------------------------------------------------------------------------------
        if 6 <= y < 9 and "adrenarche" not in self.done and r.random() < 0.02:
            self._say(p, "starts to smell after PE and gets his first spots: adrenarche", -0.1, "adrenarche", out)
        # --- puberty and growth -----------------------------------------------------------------------------------
        pre = 0.86 * self.target_height
        if y < 1:
            h = 50 + 25 * y
        elif y < onset:
            h = 75 + (pre - 75) * (y - 1) / max(0.5, onset - 1)
        else:
            h = pre + (self.target_height - pre) * smooth((y - onset) / (4.5 if male else 3.5))
        bone = s.get("bone_density", 0.3)
        shrink = 0.1 * max(0.0, y - 50) + 3.0 * max(0.0, 0.5 - bone) * (y > 50)
        self.height = h - shrink
        if s["puberty"] > 0 and y < 20:
            if "spurt" not in self.done and y >= onset + (1.5 if male else 1.0):
                self._say(p, "grows nine centimetres in a year; nothing fits", 0.2, "spurt", out)
            if not male and "menarche" not in self.done and y >= onset + 1.6:
                self.menarche = y
                self._say(p, "gets her first period", -0.1, "menarche", out)
            if male and "voice" not in self.done and y >= onset + 1.2:
                self._say(p, "hears his voice crack in front of the whole class", -0.3, "voice", out)
            if male and "shave" not in self.done and y >= onset + 2.5:
                self._say(p, "shaves for the first time and cuts himself", 0.2, "shave", out)
            if "timing" not in self.done and y >= onset:
                self.done.add("timing")
                if not male and onset < 10.3:
                    p.apply({"anxiety": 0.05}, fades=True)
                    self._say(p, "develops years before her friends and hates the attention it brings", -0.5, "early", out)
                elif male and onset > 12.4:
                    self._say(p, "is still the shortest boy in his year while everyone else shoots up", -0.4, "late", out)
            # the teen body clock: melatonin about 2 hours later, school as early as ever
        self.chronotype = 22.0 + 2.0 * math.exp(-((y - 18) / 5) ** 2) - 1.5 * clip((y - 55) / 25)
        if 12 <= y < 23 and (s["schooling"] > 0.5 or s["employed"] > 0.5):
            sleep += 0.12 * math.exp(-((y - 17) / 4) ** 2)
            if self.sleep_now > 0.08:
                now.add("social jetlag")
        if y >= 60:
            sleep += 0.12 * clip((y - 60) / 25)                # broken, earlier sleep
            if y >= 65:
                now.add("early waking")
        # --- bone and muscle --------------------------------------------------------------------------------------
        sex_h = L["estrogen"] if not male else L["testosterone"]
        if y < 30:
            target = 0.35 + 0.35 * s["motor"] + 0.15 * sex_h + 0.05 * F["ses"]
            s["bone_density"] = clip(bone + 0.01 * (target - bone))
        else:
            loss = 0.0004                                        # about 0.5% a year
            if not male and self.menopause_age <= y < self.menopause_age + 7 and not self.hrt:
                loss = 0.0016                                    # about 2% a year after menopause
            elif male and y >= 50:
                loss = 0.0006
            s["bone_density"] = clip(bone - loss * (1.2 - 0.4 * s["motor"]))
        if y >= 50:
            s["motor"] = clip(s["motor"] - 0.0005 * (1.3 - s["cardio"]))   # sarcopenia, slower if he stays active
        # --- the monthly cycle, pregnancy, menopause (if female) ---------------------------------------------------
        if not male:
            cycling = self.menarche is not None and y < self.menopause_age and p.family.expecting is None
            if cycling and self.pms and r.random() < 0.6:
                drag += self.pms
                now.add("pms")
                if r.random() < 0.02:
                    self._say(p, "has a week where everything feels heavier: " + ("PMDD" if self.pms > 0.05 else "PMS"),
                              -0.4, "", out)
            if cycling and self.cramps and r.random() < 0.05:
                self._say(p, "is doubled up with period pain and misses a day", -0.4, "", out)
            exp = p.family.expecting
            if exp is not None:
                trimester = 3 - max(0, (exp - m - 1) // 3)
                if trimester == 1 and r.random() < 0.7 and "sick_" + str(exp) not in self.done:
                    self._say(p, "is sick every morning for weeks: the first trimester", -0.3, "sick_" + str(exp), out)
                if trimester == 3:
                    sleep += 0.12
            for k in [x for x in p.family.people if x.relation == "child" and 0 <= m - x.born < 12]:
                if m - k.born == 0 and r.random() < 0.8:
                    self._say(p, "cries for no reason a week after the birth: the baby blues, as her hormones crash", -0.3, "", out)
                if m - k.born < 6:
                    p.chem.level["oxytocin"] = clip(p.chem.level["oxytocin"] + 0.04)
                    L["prolactin"] = 0.8
            if self.menopause_age - 5 <= y < self.menopause_age + self.flush_years:
                if "peri" not in self.done:
                    self._say(p, "notices her periods going irregular and her sleep breaking up: perimenopause", -0.3, "peri", out)
                if self.flushes and y >= self.menopause_age - 2:
                    now.add("hot flushes")
                    sleep += 0.06 if self.hrt else 0.14
                    drag += 0.01 if self.hrt else 0.03
                    p.apply({"anxiety": 0.004}, fades=True)
                    if not self.hrt and r.random() < 0.015 * F["healthcare_access"]:
                        self.hrt = True
                        self._say(p, "starts HRT and sleeps through the night for the first time in a year", 0.6, "", out)
            if y >= self.menopause_age and "meno" not in self.done:
                self._say(p, "has had no period for a year: menopause", -0.1, "meno", out)
        # --- men: testosterone over the years, couvade ---------------------------------------------------------------
        if male:
            if y >= 45 and not self.low_t and L["testosterone"] < 0.5 and r.random() < 0.0012:
                self.low_t = True
                self._say(p, "is tired, flat and uninterested for months; a blood test finds low testosterone", -0.4, "", out)
            if self.low_t:
                drag += 0.02
            exp = p.family.expecting
            if exp is not None and any(x.relation == "partner" and x.present(m) for x in p.family.people) \
                    and exp - m == 4 and r.random() < 0.25:
                s["adiposity"] = clip(s.get("adiposity", 0.4) + 0.02)
                self._say(p, "puts on weight and feels sick along with his pregnant partner: couvade", 0.0, "", out)
        # --- love -------------------------------------------------------------------------------------------------
        for x in p.family.people:
            if x.relation == "partner" and x.present(m):
                t = m - x.joined
                if t < 18:
                    p.chem.level["dopamine"] = clip(p.chem.level["dopamine"] + 0.05)
                    now.add("new love")
                    sleep += 0.02
                else:
                    p.chem.level["oxytocin"] = clip(p.chem.level["oxytocin"] + 0.015)
        # --- seasons ----------------------------------------------------------------------------------------------
        if self.sad and y >= 12 and p.chem.daylight(m) < 0.25:
            now.add("winter")
            drag += 0.06
            sleep += 0.04
            if r.random() < 0.08:
                self._say(p, "sinks again as the days get short: seasonal depression", -0.4, "", out)
        self.sleep_now, self.mood_drag, self.active_now = clip(sleep), clip(drag, 0, 0.3), now
        return out

    active_now: set = set()
    age_y: float = 0.0

    def _say(self, p, text: str, valence: float, once: str, out: List[dict]) -> None:
        if once:
            self.done.add(once)
        self.recent.append([round(p.years, 1), text])
        self.recent = self.recent[-20:]
        out.append({"text": text, "valence": valence, "arousal": 0.3 + 0.4 * abs(valence), "who": [], "key": "body",
                    "deltas": {}})
