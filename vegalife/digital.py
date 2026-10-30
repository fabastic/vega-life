"""Phones, computers and the internet, at every age, with the feed itself simulated.

What the research supports, and how it is used:
  ownership    about half of US children have their own smartphone at 11, ~69% at 12, nearly all by 17
               (Common Sense census 2019, 2026); stricter phone rules at home push it later
  time         entertainment screen time about 5 h a day for tweens and 8 h for teens; more than 4 in 10 teens
               at 10 h+ (Common Sense 2026); adults several hours; older adults less
  sleep        the clearest harm: late-night phone use displaces sleep, which then lowers mood and school results
  mood         average links between social media and depression are small (Orben & Przybylski: well under 1% of
               the variance), larger for heavy users and for girls (UK cohort: 5 h+ a day, more depressive
               symptoms), and driven by sleep loss, cyberbullying, appearance comparison and displaced activity
  bullying     46% of US teens have experienced cyberbullying, 54% of older girls (Pew 2022)
  rewards      likes and new posts arrive on a variable schedule, the strongest kind for building a habit
  feeds        engagement-ranked feeds learn what holds him and serve more of it, outrage and comparison included
  older age    using the internet is linked to less loneliness and depression in later life, and gives access to
               services and family; scams target the old (world.py)

The feed: every month he has a typical session. The algorithm ranks candidate posts by his learned interests plus
engagement bait (outrage, comparison, crisis), he dwells on what catches him, likes come in at random, and what he
dwells on is learned and served more next month (a rabbit hole if nothing breaks it). That session sets the month's
habit, comparison, outrage and crisis exposure. The UI shows the session as a phone screen.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from .factors import FactorSet

# topic: (bait: how strongly feeds push it, what it does to him per unit of dwell)
TOPICS: Dict[str, tuple] = {
    "friends": (0.3, {"community_support": 0.002}),
    "memes": (0.5, {"joy": 0.01}),
    "gaming": (0.45, {"joy": 0.008}),
    "sport": (0.35, {"joy": 0.006}),
    "music": (0.35, {"joy": 0.008}),
    "learning": (0.15, {"digital_literacy": 0.004}),
    "news": (0.4, {"nihilism": 0.002}),
    "crisis": (0.65, {"nihilism": 0.006, "anxiety": 0.004}),
    "outrage": (0.75, {"identity_rigidity": 0.006, "household_friction": 0.002}),
    "looks": (0.7, {"anxiety": 0.004}),
    "money": (0.6, {"goal_horizon": -0.002}),
    "influencers": (0.6, {"felt_loneliness": -0.002}),
    "ads": (0.2, {"wealth": -0.001}),
}
POSTS = {
    "friends": ["{f} posted photos from a party he was not at", "{f} got into the team", "{f} shared a song",
                "{f} posted a selfie with {g}", "{f} is on holiday by the sea"],
    "memes": ["a meme about Monday mornings", "a cat falling off a sofa", "a clip of a toddler dancing",
              "a meme about exams", "a dog that hates the vet"],
    "gaming": ["a speedrun world record", "a clip of a ridiculous game glitch", "a new game trailer"],
    "sport": ["the goal everyone is talking about", "a workout routine", "a training montage"],
    "music": ["a cover of a song he loves", "a new album out tonight", "a concert clip"],
    "learning": ["a ten-minute explainer on black holes", "how a bridge stays up", "a history thread",
                 "a coding tutorial"],
    "news": ["an election result", "a new law on rents", "a strike at the hospital"],
    "crisis": ["record heat on three continents", "markets crash overnight", "a war escalates",
               "a flood drowns a town"],
    "outrage": ["a furious argument in the comments about immigration", "a clip cut to make the other side look stupid",
                "a stranger being mocked by thousands", "a thread on why everyone else is ruining the country"],
    "looks": ["a filtered 'what I eat in a day'", "a body transformation in 30 days", "a perfect skincare routine",
              "an influencer on a yacht"],
    "money": ["'I quit my job and made $40k in a month'", "a crypto coin up 900%", "a 22-year-old's luxury flat tour"],
    "influencers": ["a 'day in my life' vlog", "a streamer talking to chat for hours", "an AI companion asking how his day was"],
    "ads": ["an ad for trainers in exactly his size", "an ad for a loan app", "an ad for the game he just watched"],
}


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class Online:
    def __init__(self, F: FactorSet, seed: int):
        self.rng = random.Random(seed * 3571 + 41)
        r = self.rng
        self.phone_at: int = int(12 * clip(r.gauss(11.2 + 2.5 * F["phone_rules"] - 1.0 * F["screen_time"]
                                                  - 0.8 * (F["ses"] - 0.5), 1.6), 6, 17))
        self.has_phone = False
        self.taste: Dict[str, float] = {k: clip(r.gauss(0.35, 0.12)) for k in TOPICS}
        self.habit = 0.0           # 0..1 compulsive pull: checking without deciding to
        self.hours = 0.0           # screen hours a day (entertainment)
        self.pickups = 0
        self.notifications = 0
        self.comparison = 0.0      # 0..1 this month's appearance and status comparison
        self.outrage = 0.0
        self.followers = 0
        self.feed: List[dict] = []
        self.detox_until = 0
        self.cyberbullied = 0

    def to_json(self) -> dict:
        return {"has_phone": self.has_phone, "first_phone_at": round(self.phone_at / 12, 1),
                "hours": round(self.hours, 1), "pickups": self.pickups, "notifications": self.notifications,
                "habit": round(self.habit, 3), "comparison": round(self.comparison, 3), "outrage": round(self.outrage, 3),
                "followers": self.followers, "detox": self.detox_until > 0, "cyberbullied": self.cyberbullied,
                "top_topics": [k for k, _ in sorted(self.taste.items(), key=lambda t: -t[1])[:4]], "feed": self.feed}

    def baseline_hours(self, y: float) -> float:
        """Entertainment screen hours a day by age (Common Sense; adult surveys)."""
        if y < 2:
            return 0.5
        if y < 9:
            return 2.5
        if y < 13:
            return 5.0
        if y < 19:
            return 8.0
        if y < 35:
            return 6.0
        if y < 60:
            return 4.5
        return 3.5

    # ------------------------------------------------------------------ the month
    def step(self, p, F: FactorSet) -> List[dict]:
        r, s, y, m = self.rng, p.s, p.years, p.age
        out: List[dict] = []
        if not self.has_phone and m >= self.phone_at:
            self.has_phone = True
            out.append({"text": "gets his first smartphone", "valence": 0.6, "arousal": 0.7, "who": [], "key": "phone",
                        "deltas": {"dopamine": 0.1}})
        mind = getattr(p, "mind", None)
        adhd = bool(mind and mind.adhd)
        lonely = s["felt_loneliness"]
        if self.detox_until and m >= self.detox_until:
            self.detox_until = 0
            out.append({"text": "puts the apps back on his phone", "valence": 0.0, "arousal": 0.3, "who": [],
                        "key": "phone", "deltas": {}})
        cut = 0.35 if self.detox_until else 1.0
        rules = F["phone_rules"] * (1.0 if y < 18 else 0.0)
        self.hours = max(0.2, self.baseline_hours(y) * (0.6 + 0.8 * F["screen_time"]) * (1 + 0.4 * self.habit)
                         * (1 + 0.25 * adhd + 0.3 * lonely) * (1 - 0.4 * rules) * cut * (1 if self.has_phone or y < 9 else 0.6))
        if not self.has_phone:
            self.feed, self.pickups, self.notifications, self.comparison, self.outrage = [], 0, 0, 0.0, 0.0
            s["digital_literacy"] = clip(s["digital_literacy"] + 0.002 * (y > 5))
            return out
        # --- one typical session: the algorithm ranks, he dwells, it learns -------------------------------------
        friends = [f.name for f in p.circle.present(m)] if p.circle else []
        engage = 0.35 + 0.5 * F["echo_chambers"]                    # how hard the feed optimises for engagement
        cands = []
        for k, (bait, _) in TOPICS.items():
            if k == "friends" and not friends:
                continue
            score = self.taste[k] + engage * bait + r.gauss(0, 0.12)
            if k == "crisis":
                score += 0.3 * F["crisis_news"]
            if k == "influencers":
                score += 0.2 * F["parasocial_companions"]
            cands.append((score, k))
        cands.sort(reverse=True)
        shown = [k for _, k in cands[:6]] * 2
        r.shuffle(shown)
        feed: List[dict] = []
        dwell_by: Dict[str, int] = {}
        reward = []
        used = set()
        for k in shown[:12]:
            fresh = [t for t in POSTS[k] if t not in used] or POSTS[k]
            raw = r.choice(fresh)
            used.add(raw)
            text = raw.format(f=r.choice(friends) if friends else "someone",
                                              g=r.choice(friends) if friends else "friends")
            secs = max(1, int(r.expovariate(1 / (4 + 30 * self.taste[k]))))
            liked = r.random() < 0.15 + 0.4 * self.taste[k]
            reward.append(liked)
            dwell_by[k] = dwell_by.get(k, 0) + secs
            feed.append({"topic": k, "text": text, "seconds": secs, "liked": liked})
        self.feed = feed
        total = sum(dwell_by.values()) or 1
        for k in TOPICS:                                            # what held him is served more
            share = dwell_by.get(k, 0) / total
            self.taste[k] = clip(self.taste[k] + 0.06 * (share - 1 / len(TOPICS)) + 0.005 * (0.35 - self.taste[k]))
        # posting: likes on a variable schedule
        if y >= 11 and r.random() < 0.3 + 0.4 * s["extraversion"]:
            likes = int(r.lognormvariate(math.log(5 + self.followers / 20 + 1), 0.9))
            self.followers += r.randint(0, 3)
            got = likes > 10 + self.followers / 15
            if "dopamine" in s:
                s["dopamine"] = clip(s["dopamine"] + (0.06 if got else -0.03))
            feed.insert(0, {"topic": "you", "text": f"he posted; {likes} likes", "seconds": 0, "liked": got})
        # --- habit, comparison, outrage, sleep ---------------------------------------------------------------------
        variance = sum(reward) / max(1, len(reward))
        self.habit = clip(self.habit + 0.01 * (0.6 + variance) * (1.3 - s["pfc_maturity"]) * (1 + 0.5 * adhd)
                          - 0.008 * rules - (0.05 if self.detox_until else 0.0) - 0.004 * s["conscientiousness"])
        self.pickups = int(max(5, 30 + 90 * self.habit + 10 * adhd) * cut)
        self.notifications = int((40 + 200 * self.taste["friends"] + 60 * (y < 25)) * (1.0 - 0.4 * rules) * cut)
        self.comparison = clip((dwell_by.get("looks", 0) + dwell_by.get("money", 0) + 0.6 * dwell_by.get("friends", 0))
                               / total * (0.5 + s["neuroticism"]) * min(1.0, self.hours / 5))
        self.outrage = clip(dwell_by.get("outrage", 0) / total * min(1.0, self.hours / 4))
        heavy = max(0.0, self.hours - 4) / 6
        d: Dict[str, float] = {}
        for k, secs in dwell_by.items():
            for st, v in TOPICS[k][1].items():
                if st in s:
                    d[st] = d.get(st, 0.0) + v * secs / total * min(1.5, self.hours / 3)
        night = clip(0.15 + 0.6 * self.habit - 0.5 * rules)        # the phone in the bedroom
        s["sleep"] = clip(s["sleep"] - 0.06 * night * min(1.0, self.hours / 5))
        d["anxiety"] = d.get("anxiety", 0) + 0.006 * self.comparison + 0.004 * heavy
        if y < 25:
            d["cardio"] = -0.002 * heavy                            # the hours come from somewhere
        if y >= 60:
            d["social_isolation"] = -0.004 * min(1.0, self.hours / 3)   # video calls, groups, news from family
        s["digital_literacy"] = clip(s["digital_literacy"] + 0.003)
        p.apply({k: v for k, v in d.items() if k in s}, fades=True)
        # --- cyberbullying (teens; girls more) -------------------------------------------------------------------
        if 11 <= y < 19 and r.random() < 0.012 * (1.2 if F["sex"] < 0.5 else 1.0) * (0.5 + self.hours / 8):
            self.cyberbullied += 1
            what = r.choice(["people pile on in the comments under his photo", "someone spreads a rumour about him online",
                             "a group chat turns on him", "an embarrassing clip of him is shared around school"])
            dd = {"anxiety": 0.06, "school_belonging": -0.04, "peer_isolation": 0.03}
            p.apply(dd, fades=True)
            out.append({"text": what, "valence": -0.7, "arousal": 0.7, "who": [], "key": "cyberbullied", "deltas": dd})
        # --- noticing it, and cutting down -------------------------------------------------------------------------
        if not self.detox_until and self.habit > 0.55 and y >= 14 and r.random() < 0.015 * (0.5 + s["conscientiousness"]):
            self.detox_until = m + r.randint(1, 4)
            out.append({"text": "deletes the apps from his phone for a while", "valence": 0.3, "arousal": 0.4, "who": [],
                        "key": "phone", "deltas": {}})
        return out

    def line(self) -> str:
        if not self.has_phone:
            return ""
        if self.habit > 0.6:
            return "I keep picking up my phone without meaning to, and I do not even enjoy it."
        if self.comparison > 0.35:
            return "Everyone online seems to have a better life than me."
        if self.outrage > 0.3:
            return "People online make me so angry."
        return ""
