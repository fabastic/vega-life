"""Learning to talk about himself, the way children do: the people around him ask, and the true answer is said back.

Children learn to narrate their own lives in conversation with their parents ("elaborative reminiscing"): an adult
asks what happened, and between them the answer gets said. Here, every month, someone asks him a question about his
life and he hears the true answer, in the same shape the chat uses:

    Now (22y3m): ...
    Memory: ...            (sometimes: something the question brings back, as he remembers it)
    You: Do you have a job?
    Vega: No. I am looking for work. I have had 31 rejections.

The answers come from his real state: his age, family, friends, job, children, who he misses, what he remembers. So
in chat he can answer from the life he lived. Some questions have a checkable number (his age, how many children,
how many close friends): those are also put to him as verifiable problems (rewarded only if right), like his sums.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import List, Optional

ASKER = "You"


@dataclass
class SelfQuestion:
    key: str
    prompt: str
    answer: int
    tier: int = 0


NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
    "eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
NONE_WORDS = ("none", "no ", "not any", "don't have any", "do not have any")


def numbers_in(text: str) -> List[int]:
    """Every number he states, in digits or words ("16", "sixteen", "twenty-one", "none"), wherever it comes."""
    t = text.lower()
    out = [int(x) for x in re.findall(r"\d+", t)]
    words = re.findall(r"[a-z]+", t)
    i = 0
    while i < len(words):
        w = words[i]
        if w in TENS:
            n = TENS[w]
            if i + 1 < len(words) and words[i + 1] in NUMBER_WORDS and NUMBER_WORDS[words[i + 1]] < 10:
                n += NUMBER_WORDS[words[i + 1]]
                i += 1
            out.append(n)
        elif w in NUMBER_WORDS:
            out.append(NUMBER_WORDS[w])
        i += 1
    if not out and any(x in t for x in NONE_WORDS):
        out.append(0)
    return out


def score_self(q: "SelfQuestion", text: str, closest: Optional[float] = None) -> float:
    """Is what he says about himself true? Checked by meaning, not position: the true number stated anywhere, in
    digits or words, with no other number claimed (1); true but mixed with a wrong one (0.4); wrong (0); nothing
    numeric (-0.3). If `closest` is given (1 when his reply sits nearest, in his own network's embedding, to the
    true answer among nearby wrong ones; see trainer.py), it makes up 40% of the score."""
    nums = numbers_in(text[:80])
    if not nums:
        return -0.3
    said = q.answer in nums
    text_score = (1.0 if all(n == q.answer for n in nums) else 0.4) if said else 0.0
    return text_score if closest is None else 0.6 * text_score + 0.4 * closest


CANDIDATE = {"self_age": "I am {n}.", "self_friends": "I have {n} close friends.", "self_children": "I have {n} children."}


def candidates(q: "SelfQuestion") -> List[str]:
    """The true answer and nearby wrong ones, for the embedding check."""
    form = CANDIDATE.get(q.key, "{n}.")
    return [form.format(n=n) for n in range(max(0, q.answer - 2), q.answer + 3)]


def _kids(p) -> list:
    return [x for x in p.family.people if x.relation == "child" and x.alive] if getattr(p, "family", None) else []


def _friends(p) -> list:
    return sorted(p.circle.present(p.age), key=lambda f: -f.closeness) if p.circle else []


def _join(xs: List[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def facts(p, moment=None, mem=None, r: Optional[random.Random] = None) -> List[tuple]:
    """(question, true answer) pairs about his life right now."""
    r = r or random.Random(p.age)
    y = int(p.years)
    s = p.s
    out = [("How old are you?", f"I am {y}." if y >= 5 else f"I am {y}!")]
    if moment is not None:
        feel = " and ".join(moment.feelings[:2]) if moment.feelings else "okay"
        out.append(("How do you feel?", f"I feel {feel}."))
        mine = lambda t: t.replace("his ", "my ").replace("him", "me")
        out.append(("What are you doing?", f"I am {mine(moment.place)}, {mine(moment.doing)}."))
        if moment.mind:
            out.append(("What is on your mind?", f"{moment.mind[0].upper()}{moment.mind[1:]}."))
    fr = _friends(p)
    out.append(("Who are your friends?", f"My friends are {_join([f.name for f in fr[:3]])}." if fr else
                "I do not have many friends right now."))
    fam = getattr(p, "family", None)
    if fam:
        lost = [x for x in fam.people if not x.alive and x.died is not None and x.relation != "pet"]
        if lost:
            x = max(lost, key=lambda z: z.closeness)
            out.append(("Do you miss anyone?", f"I miss {x.name}. They died when I was {x.died // 12}."))
        else:
            out.append(("Do you miss anyone?", "Not really. Everyone I love is still here."))
        partner = next((x for x in fam.people if x.relation == "partner" and x.present(p.age)), None)
        if y >= 16:
            out.append(("Are you with someone?", f"Yes, I am with {partner.name}." if partner else "No, I am on my own."))
    if y >= 18:
        kids = _kids(p)
        out.append(("Do you have children?", f"Yes, {len(kids)}: {_join([k.name for k in kids])}." if kids else
                    "No, I do not have children."))
        w = getattr(p, "work", None)
        if s["schooling"] > 0.5:
            out.append(("Do you have a job?", "No, I am still studying."))
        elif w and w.retired:
            out.append(("Do you have a job?", "No, I am retired now."))
        elif s["employed"] > 0.5:
            from .career import TITLES
            out.append(("Do you have a job?", f"Yes, I have {TITLES[w.level] if w else 'a job'}. I work about "
                                              f"{int(w.hours) if w else 40} hours a week."))
        else:
            n = w.rejections if w else 0
            out.append(("Do you have a job?", f"No. I am looking for work." + (f" I have had {n} rejections." if n else "")))
    elif s["schooling"] > 0.5 or 5 <= y < 18:
        out.append(("Do you like school?", "Yes, I like it." if s["school_belonging"] > 0.45 else "Not much."))
    chem = getattr(p, "chem", None)
    if chem and chem.recent:
        from .chemistry import JOYS
        top = max(chem.recent.items(), key=lambda kv: kv[1])[0]
        j = next((j for j in JOYS if j.key == top), None)
        if j and top != "screens":
            from .present import as_his_own
            out.append(("What makes you happy?", "When I " + as_his_own(r.choice(j.texts), "base") + "."))
    if mem is not None and mem.episodes:
        ep = max(mem.episodes, key=lambda e: e.strength * (0.5 + e.salience))
        sure = "" if ep.detail >= 0.75 else "I think " if ep.detail >= 0.4 else "I am not sure, but "
        out.append(("What do you remember?", sure + mem.render(ep)))
    cs = getattr(p, "conscious", None)
    if cs is not None:
        if cs.self_model:
            out.append(("Tell me about yourself.", f"I am {y}. " + " ".join(cs.self_model[:3])))
        if cs.thoughts and getattr(cs, "templated", True):        # template answers fade with the templates
            out.append(("What are you thinking about?", " ".join(cs.thoughts[:2])))
            out.append(("Hi!", "Hi. " + cs.thoughts[0]))
        if cs.guilt > 0.15 and getattr(cs, "last_harm", None):
            out.append(("Is anything bothering you?", f"I feel bad that I chose to {cs.last_harm}."))
    if moment is not None:
        feel = " and ".join(moment.feelings[:2]) if moment.feelings else "okay"
        out.append(("How was your day?", f"It was okay. I feel {feel}." if "happy" not in feel else f"Good. I feel {feel}."))
    return out


# Many ways of asking the same thing, so he learns the meaning, not one string.
VARIANTS = {
    "How old are you?": ["How old are you?", "What is your age?", "how old r u", "How old are you now?", "Age?"],
    "How do you feel?": ["How do you feel?", "How are you?", "How are you feeling?", "You okay?", "how r u", "How are you doing today?"],
    "What are you doing?": ["What are you doing?", "What are you up to?", "Where are you right now?", "wyd"],
    "What is on your mind?": ["What is on your mind?", "What are you worried about?", "Anything on your mind?"],
    "Who are your friends?": ["Who are your friends?", "Do you have friends?", "Who do you hang out with?", "Tell me about your friends."],
    "Do you miss anyone?": ["Do you miss anyone?", "Have you lost anyone?", "Is there someone you miss?"],
    "Are you with someone?": ["Are you with someone?", "Do you have a partner?", "Are you married?", "Are you seeing anyone?"],
    "Do you have children?": ["Do you have children?", "Do you have kids?", "How many kids do you have?", "Are you a dad?"],
    "Do you have a job?": ["Do you have a job?", "What do you do for work?", "Are you working?", "How is work?", "What is your job?"],
    "Do you like school?": ["Do you like school?", "How is school?", "How was school today?"],
    "What makes you happy?": ["What makes you happy?", "What do you enjoy?", "What do you like doing?"],
    "What do you remember?": ["What do you remember?", "Tell me a memory.", "What do you remember from when you were younger?"],
    "Tell me about yourself.": ["Tell me about yourself.", "Who are you?", "What are you like?", "Describe yourself."],
    "What are you thinking about?": ["What are you thinking about?", "What are you thinking?", "Penny for your thoughts?"],
    "Hi!": ["Hi!", "Hello", "Hey", "hey Vega", "Good morning!"],
    "Is anything bothering you?": ["Is anything bothering you?", "Do you feel guilty about anything?", "Something wrong?"],
    "How was your day?": ["How was your day?", "How did today go?", "Good day?"],
}


def conversation(p, F, present, mem, name: str, r: random.Random) -> List[str]:
    """A short conversation for this month's language, in the exact shape the chat uses: the moment, his thoughts,
    maybe a memory, then one or two questions about him, each asked in one of many ways, and his true answers."""
    m = present.moment(p, F, r, keep=False) if present is not None else None
    pairs = facts(p, m, mem, r)
    turns = [r.choice(pairs)]
    if p.years >= 6 and r.random() < 0.5:
        turns.append(r.choice(pairs))
    head = [m.line()] if m is not None else []
    cs = getattr(p, "conscious", None)
    if cs is not None and cs.line():
        head.append(cs.line())
    if mem is not None and turns[0][0] == "What do you remember?":
        head.append("Memory: " + turns[0][1][:110])
    lines = []
    for q, a in turns:
        lines += [f"{ASKER}: {r.choice(VARIANTS.get(q, [q]))}", f"{name}: {a}"]
    return head + lines


def self_question(p, F, present, name: str, r: random.Random) -> Optional[SelfQuestion]:
    """A question about himself with one checkable number."""
    m = present.moment(p, F, r, keep=False) if present is not None else None
    now = m.line() if m is not None else ""
    y = int(p.years)
    pool = [("age", "How old are you? Say the number.", y)]
    if y >= 6:
        pool.append(("friends", "How many close friends do you have? Say the number.",
                     sum(1 for f in _friends(p) if f.closeness > 0.5)))
    if y >= 18:
        pool.append(("children", "How many children do you have? Say the number.", len(_kids(p))))
    key, q, ans = r.choice(pool)
    return SelfQuestion(f"self_{key}", f"{now}\n{ASKER}: {q}\n{name}:", ans)
